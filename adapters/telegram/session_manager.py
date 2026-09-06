"""
adapters/telegram/session_manager.py
====================================
Прокси-модуль обратной совместимости.
Перенаправляет вызовы в единый tools/session_manager.py.
"""
import sys
import os

TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from session_manager import *
