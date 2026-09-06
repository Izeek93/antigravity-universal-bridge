"""
core/universal_receiver.py
==========================
Единый универсальный приёмник входящих сообщений (Telegram + ВКонтакте) для Antigravity IDE.
- Слушает подключенные адаптеры (adapters/telegram, adapters/vk).
- Отслеживает экстренные сигналы SOS (sos.json) и очереди инцидентов.
- При получении сообщения выводит структурированный лог и завершается с кодом 0,
  мгновенно пробуждая агента в активной сессии Antigravity IDE.
"""

import os
import sys
import time
import json
from typing import List, Dict, Any

# UTF-8 вывод на консоли Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.queue_protocol import MessageQueue

TG_QUEUE = MessageQueue(os.path.join(BASE_DIR, "adapters", "telegram", "inbox.json"))
VK_QUEUE = MessageQueue(os.path.join(BASE_DIR, "adapters", "vk", "inbox.json"))

TG_INCIDENTS = os.path.join(BASE_DIR, "adapters", "telegram", "incidents.json")
VK_INCIDENTS = os.path.join(BASE_DIR, "adapters", "vk", "incidents.json")
SOS_FILE = os.path.join(BASE_DIR, "sos.json")

def check_incidents() -> bool:
    """Проверка инцидентов от любого из адаптеров."""
    found = False
    for inc_path, s_name in [(TG_INCIDENTS, "TELEGRAM"), (VK_INCIDENTS, "VK")]:
        if os.path.exists(inc_path):
            try:
                with open(inc_path, "r", encoding="utf-8") as f:
                    incidents = json.load(f)
                if incidents:
                    for inc in incidents:
                        print("\n" + "!"*60)
                        print(f"🚨 AUTONOMOUS INCIDENT ALERT from [{s_name}]:")
                        print(f"   Error: {inc.get('error')}")
                        if inc.get('traceback'):
                            print(f"   Traceback:\n{inc.get('traceback')}")
                        print("!"*60 + "\n", flush=True)
                    with open(inc_path, "w", encoding="utf-8") as f:
                        json.dump([], f)
                    found = True
            except Exception:
                pass
    return found

def check_sos() -> bool:
    """Проверка экстренного сигнала SOS от пользователя."""
    if os.path.exists(SOS_FILE):
        try:
            with open(SOS_FILE, "r", encoding="utf-8") as f:
                sos_data = json.load(f)
            os.remove(SOS_FILE)
            print("\n" + "="*60)
            print("🚨🚨🚨 [EMERGENCY SOS SIGNAL RECEIVED] 🚨🚨🚨")
            print(f"Источник: {sos_data.get('source')} | Время: {sos_data.get('datetime')}")
            print(f"Детали: {sos_data.get('details')}")
            print("ПРИЧИНА: Пользователь нажал кнопку экстренного вызова SOS!")
            print("ИНСТРУКЦИЯ: Проведи немедленный аудит связи и отправь статус.")
            print("="*60 + "\n", flush=True)
            return True
        except Exception:
            pass
    return False

def print_messages(messages: List[Dict[str, Any]]):
    print("\n" + "="*60)
    print(f"📥 INCOMING MESSAGES ({len(messages)} message(s)):")
    for idx, msg in enumerate(messages, start=1):
        source = msg.get("source", "UNKNOWN")
        chat_id = msg.get("chat_id")
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")
        print(f"[{idx}] [{source}] From: {user} (ID: {chat_id})")
        print(f"    Message: {text}\n")
    print("="*60 + "\n", flush=True)

def main():
    if check_sos() or check_incidents():
        sys.exit(0)

    while True:
        try:
            if check_sos() or check_incidents():
                sys.exit(0)

            tg_msgs = TG_QUEUE.pop_all(source_label="TELEGRAM")
            vk_msgs = VK_QUEUE.pop_all(source_label="VK")

            all_msgs = tg_msgs + vk_msgs
            if all_msgs:
                print_messages(all_msgs)
                sys.exit(0)

            time.sleep(0.5)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
