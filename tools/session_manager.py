"""
tools/session_manager.py
========================
Модуль программного управления сессиями Antigravity IDE.
Позволяет удаленно из мессенджеров (Telegram, VK) открывать новый чистый чат/сессию в IDE
через официальный CLI-интерфейс Antigravity (`antigravity-ide chat`).
"""

import os
import sys
import subprocess
import shutil

IDE_CMD_PATH = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\Antigravity IDE\bin\antigravity-ide.cmd"
)
if not os.path.exists(IDE_CMD_PATH):
    IDE_CMD_PATH = shutil.which("antigravity-ide") or IDE_CMD_PATH

def start_new_ide_session(prompt: str = "Старт новой сессии через мост.") -> bool:
    """
    Открывает новую сессию чата в активном окне Antigravity IDE.
    Выполняется асинхронно без блокировки моста.
    """
    cmd_exe = IDE_CMD_PATH
    if not os.path.exists(cmd_exe):
        cmd_exe = "antigravity-ide.cmd"

    try:
        args = [cmd_exe, "chat", "-r", prompt]
        subprocess.Popen(
            args,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return True
    except Exception as e:
        print(f"[SessionManager Error] Не удалось открыть сессию: {e}", file=sys.stderr)
        return False
