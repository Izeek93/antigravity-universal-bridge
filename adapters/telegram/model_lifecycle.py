import time
import threading
import subprocess
import urllib.request
import json
import os

COMFY_PORT = 8188
IDLE_TIMEOUT_SECONDS = 300  # 5 minutes auto-shutdown timeout

_last_activity_time = 0
_watchdog_thread = None
_stop_watchdog = threading.Event()

def is_comfyui_running() -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{COMFY_PORT}/system_stats")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            return bool(data.get("system", {}).get("comfyui_version"))
    except Exception:
        return False

def touch_activity():
    global _last_activity_time
    _last_activity_time = time.time()
    ensure_watchdog_running()

def free_comfyui_vram():
    """Unload all cached models from VRAM without killing the server."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{COMFY_PORT}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return True
    except Exception:
        return False

def free_system_resources():
    """Universal memory & VRAM cleanup for Windows and AI processes."""
    import gc
    gc.collect()

    # 1. Clean PyTorch CUDA Cache if available
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass

    # 2. Release Windows working set
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
        except Exception:
            pass

    # 3. Unload local ComfyUI/LLM server models if running
    free_comfyui_vram()

    # 4. Optional: terminate processes specified in FREE_PROCESS_PATTERNS env
    patterns = os.getenv("FREE_PROCESS_PATTERNS", "").strip()
    if patterns:
        for pat in patterns.split(","):
            p = pat.strip()
            if p and sys.platform == "win32":
                try:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", f"Get-Process python -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '*{p}*' }} | Stop-Process -Force"],
                        capture_output=True, text=True
                    )
                except Exception:
                    pass
    return True

# Backward-compatibility alias
stop_comfyui_process = free_system_resources

def _watchdog_loop():
    global _last_activity_time
    while not _stop_watchdog.wait(15):
        if is_comfyui_running():
            idle_duration = time.time() - _last_activity_time
            if _last_activity_time > 0 and idle_duration >= IDLE_TIMEOUT_SECONDS:
                print(f"[ModelLifecycle] Local model server idle for {int(idle_duration)}s. Freeing memory...")
                free_system_resources()
                _last_activity_time = 0

def ensure_watchdog_running():
    global _watchdog_thread
    if _watchdog_thread is None or not _watchdog_thread.is_alive():
        _stop_watchdog.clear()
        _watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
        _watchdog_thread.start()

# Start watchdog on import
ensure_watchdog_running()

if __name__ == "__main__":
    print(f"ComfyUI running: {is_comfyui_running()}")
    touch_activity()
