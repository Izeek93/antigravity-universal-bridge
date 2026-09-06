"""
core/queue_protocol.py
======================
Единый потокобезопасный протокол очередей сообщений и межпроцессного взаимодействия (IPC).
Использует атомарную блокировку portalocker (OS file locks) для исключения состояния гонки (race condition).
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
import portalocker

class MessageQueue:
    def __init__(self, inbox_path: str, lock_path: Optional[str] = None):
        self.inbox_path = os.path.abspath(inbox_path)
        self.lock_path = os.path.abspath(lock_path or (self.inbox_path + ".lock"))
        os.makedirs(os.path.dirname(self.inbox_path), exist_ok=True)

    def push(self, message: Dict[str, Any]) -> bool:
        """Потокобезопасное добавление сообщения в конец очереди."""
        if "timestamp" not in message:
            message["timestamp"] = time.time()

        try:
            with portalocker.Lock(self.lock_path, timeout=5, fail_when_locked=False):
                data = []
                if os.path.exists(self.inbox_path):
                    try:
                        with open(self.inbox_path, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                            data = raw if isinstance(raw, list) else [raw]
                    except (json.JSONDecodeError, ValueError, OSError):
                        data = []
                data.append(message)
                with open(self.inbox_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def pop_all(self, source_label: str = "") -> List[Dict[str, Any]]:
        """Атомарное извлечение и очистка всех сообщений из очереди."""
        if not os.path.exists(self.inbox_path):
            return []

        messages = []
        try:
            with portalocker.Lock(self.lock_path, timeout=5, fail_when_locked=False):
                if os.path.exists(self.inbox_path):
                    try:
                        with open(self.inbox_path, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                            messages = raw if isinstance(raw, list) else [raw]
                    except (json.JSONDecodeError, ValueError, OSError):
                        messages = []
                    with open(self.inbox_path, "w", encoding="utf-8") as f:
                        json.dump([], f)
        except Exception:
            return []

        if source_label:
            for m in messages:
                if "source" not in m:
                    m["source"] = source_label

        return messages
