"""
adapters/telegram/session_manager.py
====================================
Прокси-модуль обратной совместимости.
Перенаправляет вызовы в единый tools/session_manager.py.
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.session_manager import start_new_ide_session, IDE_CMD_PATH

