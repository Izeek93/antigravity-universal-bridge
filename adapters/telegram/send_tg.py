import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import argparse
import urllib.request
import urllib.parse
import threading
import time

ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
if ADAPTER_DIR not in sys.path:
    sys.path.insert(0, ADAPTER_DIR)

try:
    from adapters.telegram.tg_config import TG_BOT_TOKEN, get_active_chat_id
    from adapters.telegram.tg_formatter import md_to_tg_html
except ImportError:
    from tg_config import TG_BOT_TOKEN, get_active_chat_id
    from tg_formatter import md_to_tg_html

REMOVE_REPLY_KEYBOARD = {"remove_keyboard": True}

MAIN_REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "📸 Скриншот"}, {"text": "📊 Лимиты"}],
        [{"text": "📋 Задачи"}, {"text": "ℹ️ Помощь"}],
        [{"text": "🚨 SOS / Проверить логи"}]  # Спрятана внизу других кнопок
    ],
    "resize_keyboard": True
}

BOT_COMMANDS = [
    {"command": "new",    "description": "🔄 Начать новую сессию"},
    {"command": "screen", "description": "📸 Скриншот рабочего стола"},
    {"command": "voice",  "description": "🔊 Вкл/выкл голосовые ответы"},
    {"command": "limits", "description": "⏳ Квоты и телеметрия IDE"},
    {"command": "tasks",  "description": "⚙️ Фоновые задачи и процессы"},
    {"command": "team",   "description": "🤖 Статус мультиагентной системы AATC"},
    {"command": "retro",  "description": "📈 Еженедельная ретроспектива уроков"},
    {"command": "status", "description": "📊 Статус подключения IDE"},
    {"command": "help",   "description": "ℹ️ Справка и возможности"},
    {"command": "sos",    "description": "🚨 Проверить логи и связь (SOS)"}
]

def set_bot_commands(chat_id: int | str = None) -> bool:
    target_chat = chat_id or get_active_chat_id()
    tg_api_post("setMyCommands", {"commands": BOT_COMMANDS, "scope": {"type": "default"}})
    tg_api_post("setMyCommands", {"commands": BOT_COMMANDS, "scope": {"type": "all_private_chats"}})
    if target_chat:
        tg_api_post("setMyCommands", {"commands": BOT_COMMANDS, "scope": {"type": "chat", "chat_id": target_chat}})
        tg_api_post("setChatMenuButton", {"chat_id": target_chat, "menu_button": {"type": "commands"}})
    return True


def tg_api_post(method: str, payload: dict = None) -> dict:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Telegram API Error] {method}: {e}", file=sys.stderr)
        return {"ok": False, "error": str(e)}

def send_chat_action(action: str = "typing", chat_id: int | str = None) -> bool:
    target_chat_id = chat_id or get_active_chat_id()
    if not target_chat_id:
        return False
    res = tg_api_post("sendChatAction", {"chat_id": target_chat_id, "action": action})
    return bool(res.get("ok"))

class ActionKeeper:
    """Context manager and thread to continuously keep a Telegram chat action active (e.g. typing, record_voice)."""
    def __init__(self, action: str = "typing", chat_id: int | str = None, interval: float = 4.0):
        self.action = action
        self.chat_id = chat_id or get_active_chat_id()
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if not self.chat_id:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=1.0)

    def _run(self):
        send_chat_action(self.action, self.chat_id)
        while not self.stop_event.wait(self.interval):
            send_chat_action(self.action, self.chat_id)

def send_message(text: str, chat_id: int | str = None, reply_markup: dict = None, with_keyboard: bool = False, raw: bool = False) -> bool:
    target_chat_id = chat_id or get_active_chat_id()
    if not target_chat_id:
        print("Error: No active Telegram chat_id found.", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    
    markup = reply_markup if reply_markup is not None else MAIN_REPLY_KEYBOARD

    # Format markdown into HTML unless raw is requested
    formatted_text = text if raw else md_to_tg_html(text)

    chunk_size = 4000
    success = True
    for i in range(0, len(formatted_text), chunk_size):
        chunk = formatted_text[i:i + chunk_size]
        payload = {
            "chat_id": target_chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if markup and (i + chunk_size >= len(formatted_text)):
            payload["reply_markup"] = markup

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if not result.get("ok"):
                    # Fallback to plain text if HTML parsing has issues
                    print(f"Telegram HTML send error ({result}), falling back to plain text...", file=sys.stderr)
                    payload.pop("parse_mode", None)
                    payload["text"] = text[i:i + chunk_size]
                    data_fallback = json.dumps(payload).encode("utf-8")
                    req_fallback = urllib.request.Request(url, data=data_fallback, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req_fallback, timeout=15) as resp2:
                        res2 = json.loads(resp2.read().decode("utf-8"))
                        if not res2.get("ok"):
                            success = False
        except Exception as e:
            # Fallback to plain text on exception
            try:
                payload.pop("parse_mode", None)
                payload["text"] = text[i:i + chunk_size]
                data_fallback = json.dumps(payload).encode("utf-8")
                req_fallback = urllib.request.Request(url, data=data_fallback, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req_fallback, timeout=15) as resp2:
                    res2 = json.loads(resp2.read().decode("utf-8"))
                    if not res2.get("ok"):
                        success = False
            except Exception as e2:
                print(f"Network error sending message: {e2}", file=sys.stderr)
                success = False

    return success

def send_photo(photo_path: str, caption: str = "", chat_id: int | str = None, reply_markup: dict = None) -> bool:
    target_chat_id = chat_id or get_active_chat_id()
    if not target_chat_id:
        print("Error: No active Telegram chat_id found.", file=sys.stderr)
        return False

    if not os.path.exists(photo_path):
        print(f"Error: Photo file not found at {photo_path}", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    formatted_caption = md_to_tg_html(caption) if caption else ""
    
    filename = os.path.basename(photo_path)
    with open(photo_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{target_chat_id}\r\n'.encode("utf-8"))
    
    if formatted_caption:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{formatted_caption}\r\n'.encode("utf-8"))
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode("utf-8"))
        
    markup = reply_markup if reply_markup is not None else REMOVE_REPLY_KEYBOARD
    if markup:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="reply_markup"\r\n\r\n{json.dumps(markup)}\r\n'.encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return bool(result.get("ok"))
    except Exception as e:
        print(f"Network error sending photo: {e}", file=sys.stderr)
        return False

def send_voice(audio_path: str, caption: str = "", chat_id: int | str = None) -> bool:
    target_chat_id = chat_id or get_active_chat_id()
    if not target_chat_id:
        print("Error: No active Telegram chat_id found.", file=sys.stderr)
        return False

    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at {audio_path}", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendVoice"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    formatted_caption = md_to_tg_html(caption) if caption else ""
    filename = os.path.basename(audio_path)
    with open(audio_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{target_chat_id}\r\n'.encode("utf-8"))
    
    if formatted_caption:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{formatted_caption}\r\n'.encode("utf-8"))
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode("utf-8"))
        
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="voice"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b'Content-Type: audio/ogg\r\n\r\n')
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if not result.get("ok"):
                return send_audio(audio_path, caption=caption, chat_id=chat_id)
            return bool(result.get("ok"))
    except Exception as e:
        print(f"Network error sending voice: {e}", file=sys.stderr)
        return send_audio(audio_path, caption=caption, chat_id=chat_id)

def send_audio(audio_path: str, caption: str = "", chat_id: int | str = None) -> bool:
    target_chat_id = chat_id or get_active_chat_id()
    if not target_chat_id:
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendAudio"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    formatted_caption = md_to_tg_html(caption) if caption else ""
    filename = os.path.basename(audio_path)
    with open(audio_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{target_chat_id}\r\n'.encode("utf-8"))
    
    if formatted_caption:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{formatted_caption}\r\n'.encode("utf-8"))
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode("utf-8"))
        
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b'Content-Type: audio/mpeg\r\n\r\n')
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return bool(result.get("ok"))
    except Exception as e:
        print(f"Network error sending audio: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Send message, photo, audio or chat action to Telegram.")
    parser.add_argument("text", nargs="?", default="", help="Message text to send")
    parser.add_argument("--action", help="Send chat action (typing, record_voice, upload_photo, etc.)")
    parser.add_argument("--photo", help="Path to photo/image file to send")
    parser.add_argument("--voice", help="Path to voice/audio file to send")
    parser.add_argument("--caption", default="", help="Caption for media")
    parser.add_argument("--keyboard", action="store_true", help="Attach default reply keyboard")
    parser.add_argument("--chat_id", help="Override chat ID")

    args = parser.parse_args()

    if args.action:
        ok = send_chat_action(args.action, chat_id=args.chat_id)
        if ok:
            print(f"Action '{args.action}' sent successfully.")
        else:
            sys.exit(1)
    elif args.photo:
        caption = args.caption or args.text
        ok = send_photo(args.photo, caption=caption, chat_id=args.chat_id)
        if ok:
            print("Photo sent successfully.")
        else:
            sys.exit(1)
    elif args.voice:
        caption = args.caption or args.text
        ok = send_voice(args.voice, caption=caption, chat_id=args.chat_id)
        if ok:
            print("Voice sent successfully.")
        else:
            sys.exit(1)
    elif args.text:
        ok = send_message(args.text, chat_id=args.chat_id, with_keyboard=args.keyboard)
        if ok:
            print("Message sent successfully.")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
