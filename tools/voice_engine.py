import subprocess
import os
import sys
import re

# Dictionary for natural Russian phonetic pronunciation of tech terms/brands
PHONETIC_REPLACEMENTS = {
    r"\bFlux\s*2\s*Klein\b": "Флакс два Кляйн",
    r"\bFlux\s*2\b": "Флакс два",
    r"\bFlux\b": "Флакс",
    r"\bKlein\b": "Кляйн",
    r"\bOpenAI\b": "Опен Эй Ай",
    r"\bRTX\s*3060\b": "эр тэ икс тридцать шестьдесят",
    r"\bRTX\b": "эр тэ икс",
    r"\bGPU\b": "гэ пэ у",
    r"\bCPU\b": "цэ пэ у",
    r"\bCUDA\b": "Куда",
    r"\bTTS\b": "тэ тэ эс",
    r"\bSTT\b": "эс тэ тэ",
    r"\bRAG\b": "Раг",
    r"\bLoRA\b": "Лора",
    r"\bControlNet\b": "Контрол Нэт",
    r"\bWhisper\b": "Виспер",
    r"\bOmniVoice\b": "Омнивойс",
    r"\bAI\b": "эй ай",
    r"\bv(\d+)\b": r"версии \1",
}

def clean_and_normalize_for_speech(text: str) -> str:
    # 1. Remove markdown bold/italic/code/link syntax
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    
    # 2. Apply phonetic replacements
    for pattern, replacement in PHONETIC_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
    # 3. Clean multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def synthesize_voice(text: str, output_path: str = "voice_reply.ogg") -> str:
    """
    Нативный модульный синтез речи.
    1. Проверяет кастомную команду генерации через переменную окружения CUSTOM_TTS_COMMAND.
    2. По умолчанию использует нативный edge-tts (Windows / Linux / macOS).
    """
    clean_text = clean_and_normalize_for_speech(text)
    
    abs_out = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_out), exist_ok=True)
    
    # 1. Опциональная нативная системная команда (если настроена)
    custom_cmd = os.getenv("CUSTOM_TTS_COMMAND", "").strip()
    if custom_cmd:
        try:
            formatted_cmd = custom_cmd.replace("{text}", f'"{clean_text}"').replace("{out}", f'"{abs_out}"')
            subprocess.run(formatted_cmd, shell=True, timeout=60)
            if os.path.exists(abs_out) and os.path.getsize(abs_out) > 0:
                return abs_out
        except Exception as e:
            print(f"[voice_engine warning] Custom TTS failed: {e}", file=sys.stderr)

    # 2. Нативный Edge-TTS
    try:
        edge_cmd = ["edge-tts", "--voice", "ru-RU-SvetlanaNeural", "--text", clean_text, "--write-media", abs_out]
        subprocess.run(edge_cmd, capture_output=True, timeout=30)
        if os.path.exists(abs_out) and os.path.getsize(abs_out) > 0:
            return abs_out
    except Exception:
        pass
        
    return abs_out if os.path.exists(abs_out) and os.path.getsize(abs_out) > 0 else None

if __name__ == "__main__":
    test_text = "Проверка каскадного синтеза речи: универсальный нейро-голос и нормализация."
    out = synthesize_voice(test_text, "media/test_voice.ogg")
    print(f"Voice test generated at: {out}")
