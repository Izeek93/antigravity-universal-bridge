"""
Telegram Configuration Proxy
"""
import sys, os
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
if ADAPTER_DIR not in sys.path:
    sys.path.insert(0, ADAPTER_DIR)

try:
    from .tg_config import *
except ImportError:
    from tg_config import *
