"""
adapters/telegram/remote_approval_manager.py
============================================
Менеджер удалённых согласований действий в Antigravity IDE.
Создает запрос на утверждение плана/команды и транслирует его в подключенные мессенджеры.
"""

import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

APPROVAL_FILE = os.path.join(ROOT_DIR, "pending_approval.json")

def request_remote_approval(action_description: str, timeout_sec: float = 120.0) -> dict:
    """
    Создает отложенный запрос согласования действия в IDE.
    Транслирует интерактивные кнопки в Telegram и VK.
    """
    request_id = f"req_{int(time.time())}"
    data = {
        "request_id": request_id,
        "action": action_description,
        "status": "PENDING",
        "created_at": time.time(),
        "timeout_sec": timeout_sec
    }
    with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 1. Отправка в Telegram с Inline-кнопками
    try:
        from adapters.telegram.send_tg import send_message
        tg_text = f"🔔 **Запрос подтверждения действия в IDE:**\n\n«{action_description}»\n\nНажмите кнопку ниже или ответьте текстом/голосом:"
        tg_inline_kb = {
            "inline_keyboard": [
                [
                    {"text": "✅ Подтвердить", "callback_data": "approve"},
                    {"text": "❌ Отклонить", "callback_data": "reject"}
                ]
            ]
        }
        send_message(tg_text, reply_markup=tg_inline_kb)
    except Exception as e:
        print(f"[Remote Approval TG Error] {e}", file=sys.stderr)

    # 2. Отправка в VK с Inline-кнопками (если настроен)
    try:
        from adapters.vk import vk_api_client as vk
        from adapters.vk import vk_config as vk_cfg
        if vk_cfg.VK_ALLOWED_USER_IDS:
            target_uid = next(iter(vk_cfg.VK_ALLOWED_USER_IDS))
            vk_text = f"🔔 Запрос подтверждения действия в IDE:\n\n«{action_description}»\n\nНажмите кнопку ниже или отправьте ответ:"
            vk_inline_kb = {
                "inline": True,
                "buttons": [
                    [
                        {"action": {"type": "text", "label": "✅ Подтвердить"}, "color": "positive"},
                        {"action": {"type": "text", "label": "❌ Отклонить"}, "color": "negative"}
                    ]
                ]
            }
            vk.send_message(target_uid, vk_text, keyboard=vk_inline_kb)
    except Exception as e:
        print(f"[Remote Approval VK Error] {e}", file=sys.stderr)

    return data

def resolve_approval(decision: bool) -> bool:
    """Фиксирует решение пользователя по текущему запросу."""
    if os.path.exists(APPROVAL_FILE):
        try:
            with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = "APPROVED" if decision else "REJECTED"
            data["resolved_at"] = time.time()
            with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            pass
    return False

def get_pending_approval() -> dict:
    """Возвращает текущий активный запрос согласования, если он ожидает ответа."""
    if os.path.exists(APPROVAL_FILE):
        try:
            with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("status") == "PENDING":
                    return data
        except Exception:
            pass
    return None
