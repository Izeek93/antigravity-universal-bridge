import subprocess
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

_cached_model = None

def _get_direct_whisper_model(model_size: str = "large-v3-turbo"):
    global _cached_model
    if _cached_model is not None:
        return _cached_model
        
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if torch.cuda.is_available() else "int8"
    except ImportError:
        device = "cpu"
        compute_type = "int8"
    
    from faster_whisper import WhisperModel
    print(f"[STT] Initializing Faster-Whisper ({model_size}) on {device} ({compute_type})...")
    _cached_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _cached_model

def transcribe_local_whisper(audio_path: str, model_size: str = "large-v3-turbo") -> str:
    """
    Нативное локальное распознавание речи через Faster-Whisper.
    Работает напрямую в Windows / Linux (CUDA GPU при наличии или CPU).
    """
    abs_audio = os.path.abspath(audio_path)
    if not os.path.exists(abs_audio):
        raise FileNotFoundError(f"Audio file not found: {abs_audio}")

    try:
        model = _get_direct_whisper_model(model_size)
        segments, info = model.transcribe(abs_audio, language="ru", beam_size=5)
        full_text = " ".join([s.text.strip() for s in segments]).strip()
        return full_text
    except Exception as e:
        print(f"[STT Error] Faster-Whisper transcription failed: {e}", file=sys.stderr)
        raise RuntimeError(f"STT failed: {e}")

if __name__ == "__main__":
    test_files = [f for f in os.listdir(".") if f.startswith("voice_") and f.endswith(".ogg")]
    if test_files:
        sample = test_files[0]
        print(f"Testing cascade STT on {sample}...")
        res = transcribe_local_whisper(sample)
        print(f"Result: {res}")
