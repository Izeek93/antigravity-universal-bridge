import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

ROOT_ENV = os.path.join(ROOT_DIR, ".env")
LOCAL_ENV = os.path.join(BASE_DIR, ".env")
SECRETS_FILE = os.path.join(ROOT_DIR, "secrets.json")

ACTIVE_CHAT_FILE = os.path.join(BASE_DIR, "active_chat.json")
INBOX_FILE = os.path.join(BASE_DIR, "inbox.json")
VOICE_SETTINGS_FILE = os.path.join(BASE_DIR, "voice_settings.json")

def is_voice_enabled() -> bool:
    """Проверка, включено ли голосовое сопровождение ответов."""
    if os.path.exists(VOICE_SETTINGS_FILE):
        try:
            with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("enabled", True))
        except Exception:
            pass
    return True

def set_voice_enabled(enabled: bool) -> bool:
    """Включение или отключение голосового сопровождения ответов."""
    data = {"enabled": enabled}
    try:
        with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def load_dotenv():
    """Загрузка переменных из .env (сначала корень, затем локально)."""
    for env_path in [ROOT_ENV, LOCAL_ENV]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

def load_secrets_json():
    """Фоллбэк загрузка из secrets.json, если .env не задан."""
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k not in os.environ:
                        os.environ[k] = str(v)
        except Exception:
            pass

load_dotenv()
load_secrets_json()

# Конфигурационные переменные (только Telegram и системные)
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()

# Whitelist разрешённых chat_id (пустой set = без ограничений)
_raw_ids = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS: set[int] = {int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()}

_raw_users = os.environ.get("ALLOWED_USERNAMES", "").strip()
ALLOWED_USERNAMES: set[str] = {x.strip().lstrip("@").lower() for x in _raw_users.split(",") if x.strip()}

def get_active_chat_id():
    if os.path.exists(ACTIVE_CHAT_FILE):
        try:
            with open(ACTIVE_CHAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("chat_id")
        except Exception:
            pass
    return None

def set_active_chat(chat_id, user_info=None):
    data = {"chat_id": chat_id, "user_info": user_info or {}}
    with open(ACTIVE_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
