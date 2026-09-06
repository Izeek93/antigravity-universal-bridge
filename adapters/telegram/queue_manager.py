"""
adapters/telegram/queue_manager.py
==================================
Адаптер очереди сообщений Telegram на базе core.queue_protocol.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.queue_protocol import MessageQueue

INBOX_FILE = os.path.join(BASE_DIR, "inbox.json")
QUEUE = MessageQueue(INBOX_FILE)

def push_message(payload: dict) -> bool:
    if "source" not in payload:
        payload["source"] = "TELEGRAM"
    return QUEUE.push(payload)

def pop_messages() -> list:
    return QUEUE.pop_all(source_label="TELEGRAM")
