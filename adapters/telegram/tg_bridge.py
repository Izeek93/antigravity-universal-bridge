"""
adapters/telegram/tg_bridge.py
==============================
Основной фоновый сервис-демон Telegram моста для Antigravity IDE.
Транспортный уровень ввода-вывода (I/O Pipe):
- Принимает текст, войсы (STT через Faster-Whisper), фото и документы.
- Отправляет сервисные команды через command_router.py.
- Перекладывает рабочие сообщения в потокобезопасную очередь inbox.json.
- Автоматически очищает временные медиафайлы.
"""

import os
import sys
import subprocess
import time
import json
import urllib.request
import urllib.parse
import socket
import threading

# Гарантированный сокетный таймаут для предотвращения зависания сетевого стека Windows
socket.setdefaulttimeout(35.0)

# Принудительный UTF-8 вывод на консоли Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH_DIR = os.path.dirname(ROOT_DIR)
for p in [ROOT_DIR, SCRATCH_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.windows_mutex import WindowsNamedMutex
import portalocker

try:
    from shared_ai.privacy import mask_id
except ImportError:
    def mask_id(val, visible=2):
        s = str(val).strip() if val is not None else ""
        return f"{s[:visible]}***{s[-visible:]}" if len(s) > visible * 2 else "***"


from config import TG_BOT_TOKEN, set_active_chat, ALLOWED_CHAT_IDS
from send_tg import send_message, send_chat_action, ActionKeeper, set_bot_commands, tg_api_post
from queue_manager import push_message
from model_lifecycle import ensure_watchdog_running
try:
    from tools.local_stt import transcribe_local_whisper
except ImportError:
    transcribe_local_whisper = None
from command_router import dispatch_command

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
LOG_FILE = os.path.join(os.path.dirname(__file__), "tg_bridge.log")
os.makedirs(MEDIA_DIR, exist_ok=True)

def log(msg: str):
    """Потокобезопасное и немедленное логирование в консоль и файл."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

_last_poll_heartbeat = time.time()

def _start_auto_ack_watchdog():
    """Фоновый сторож: если входящее сообщение находится в очереди > 15 секунд без ответа,
    информирует пользователя, устраняя синдром «тишины»."""
    def _ack_loop():
        inbox_file = os.path.join(os.path.dirname(__file__), "inbox.json")
        lock_file = os.path.join(os.path.dirname(__file__), "inbox.lock")
        while True:
            try:
                time.sleep(3)
                if not os.path.exists(inbox_file):
                    continue
                with portalocker.Lock(lock_file, timeout=5, fail_when_locked=False):
                    with open(inbox_file, "r", encoding="utf-8") as f:
                        msgs = json.load(f)
                    if not isinstance(msgs, list) or not msgs:
                        continue
                    changed = False
                    now = time.time()
                    for m in msgs:
                        if not m.get("auto_acked") and (now - m.get("timestamp", now)) > 15:
                            c_id = m.get("chat_id")
                            if c_id:
                                try:
                                    send_message(
                                        "⏳ **Сообщение принято в очередь Antigravity IDE**\n"
                                        "Агент обрабатывает задачу или выполняет системные операции. "
                                        "Ответ поступит сразу по готовности.",
                                        chat_id=c_id
                                    )
                                    log(f"Auto-Ack sent to chat_id {mask_id(c_id)}")
                                except Exception as err:
                                    log(f"Auto-Ack send error: {err}")
                            m["auto_acked"] = True
                            changed = True
                    if changed:
                        with open(inbox_file, "w", encoding="utf-8") as f:
                            json.dump(msgs, f, ensure_ascii=False, indent=2)
            except Exception:
                time.sleep(1)

    t = threading.Thread(target=_ack_loop, daemon=True, name="AutoAckWatchdog")
    t.start()

def _start_liveness_watchdog():
    """Сторож зависания long-polling сокета. При отсутствии опроса > 55 сек завершает процесс для авто-перезапуска."""
    def _liveness_loop():
        global _last_poll_heartbeat
        while True:
            time.sleep(10)
            elapsed = time.time() - _last_poll_heartbeat
            if elapsed > 60:
                log(f"🚨 [Liveness Watchdog] getUpdates hang detected ({elapsed:.1f}s > 60s). Self-healing exit...")
                try:
                    from incident_manager import report_bridge_incident
                    report_bridge_incident("TG_BRIDGE", f"getUpdates socket hung for {elapsed:.1f}s")
                except Exception:
                    pass
                os._exit(101)

    t = threading.Thread(target=_liveness_loop, daemon=True, name="LivenessWatchdog")
    t.start()


_message_counter = 0
_CLEANUP_INTERVAL = 100  # Запускать очистку медиа раз в N сообщений

def cleanup_old_media(max_age_seconds: int = 86400):
    """Автоматическая очистка временных медиафайлов старше 24 часов."""
    try:
        now = time.time()
        for fname in os.listdir(MEDIA_DIR):
            fpath = os.path.join(MEDIA_DIR, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    except Exception:
        pass


def download_telegram_file(file_id: str, dest_path: str, max_retries: int = 3) -> bool:
    info = tg_api_post("getFile", {"file_id": file_id})
    if not info.get("ok"):
        return False
    file_path = info.get("result", {}).get("file_path")
    if not file_path:
        return False
    download_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"
    
    # 1. Попытка через curl.exe
    try:
        cmd = ["curl.exe", "-sSL", "--retry", "3", "--retry-delay", "1", "--connect-timeout", "15", "--max-time", "60", "-o", dest_path, download_url]
        res = subprocess.run(cmd, capture_output=True, timeout=70)
        if res.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            return True
    except Exception:
        pass
        
    # 2. Fallback через urllib streaming
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                return True
        except Exception:
            time.sleep(1.5 * attempt)
    return False

def transcribe_audio_file(audio_path: str) -> str:
    """Транскрибация аудио через локальный Faster-Whisper."""
    try:
        text = transcribe_local_whisper(audio_path, model_size="large-v3-turbo")
        if text and len(text.strip()) > 0:
            print(f"[STT Local Faster-Whisper] {text.strip()}")
            return text.strip()
    except Exception as e:
        print(f"[STT Local Whisper Error] {e}", file=sys.stderr)
    return ""

def handle_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    user = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "User")
    text = (msg.get("text") or msg.get("caption") or "").strip()

    if not chat_id:
        return

    # Whitelist-проверка: игнорируем сообщения от неавторизованных пользователей
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return

    set_active_chat(chat_id, {"username": user})

    # 🚨 Ранний перехват SOS в обход очереди FIFO
    clean_sos = text.lower().strip()
    is_sos_cmd = (
        any(clean_sos == kw or clean_sos.startswith(kw) for kw in ["sos", "сос", "/sos", "/сос", "стоп", "сброс", "отмена", "🚨"])
        or "проверить логи" in clean_sos
    )
    if is_sos_cmd:
        try:
            # Принудительно гасим зависшие генерации
            try:
                import psutil
                for p in psutil.process_iter(["name"]):
                    p_name = (p.info.get("name") or "").lower()
                    if any(target in p_name for target in ["omnivoice", "ffmpeg"]):
                        p.kill()
            except Exception:
                pass

            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import sos_manager
            sos_manager.trigger_sos("TELEGRAM", chat_id=chat_id, user=user)
            send_message("🚨 **Сигнал SOS принят!**\nВсе зависшие генерации сброшены. Агент проверяет связь.", chat_id=chat_id)
        except Exception as e:
            print(f"[SOS Error] {e}", file=sys.stderr)
        return

    global _message_counter
    _message_counter += 1
    if _message_counter % _CLEANUP_INTERVAL == 0:
        cleanup_old_media()

    # 0. Обработка цитат и ответов (reply_to_message)
    reply_prefix = ""
    reply_msg = msg.get("reply_to_message")
    if reply_msg:
        if "voice" in reply_msg or "audio" in reply_msg:
            v_info = reply_msg.get("voice") or reply_msg.get("audio")
            v_fid = v_info.get("file_id")
            dest_voice = os.path.join(MEDIA_DIR, f"reply_voice_{time.time_ns()}.ogg")
            if download_telegram_file(v_fid, dest_voice):
                transcribed = transcribe_audio_file(dest_voice)
                reply_prefix = f"↳ [В ответ на голосовое сообщение: «{transcribed}»]\n" if transcribed else "↳ [В ответ на голосовое сообщение]\n"
        elif "text" in reply_msg:
            quoted = reply_msg["text"].strip()
            quoted_str = (quoted[:150] + "...") if len(quoted) > 150 else quoted
            reply_prefix = f"↳ [В ответ на: «{quoted_str}»]\n"
        elif "photo" in reply_msg:
            cap = reply_msg.get("caption", "").strip()
            reply_prefix = f"↳ [В ответ на фото/скриншот{' («' + cap + '»)' if cap else ''}]\n"
        elif "document" in reply_msg:
            doc_n = reply_msg.get("document", {}).get("file_name", "документ")
            reply_prefix = f"↳ [В ответ на документ «{doc_n}»]\n"

    # 1. Обработка входящих фото и скриншотов
    if "photo" in msg:
        photo_sizes = msg.get("photo", [])
        if photo_sizes:
            file_id = photo_sizes[-1].get("file_id")
            photo_path = os.path.join(MEDIA_DIR, f"incoming_photo_{time.time_ns()}.png")
            with ActionKeeper("upload_photo", chat_id):
                if download_telegram_file(file_id, photo_path):
                    cap = msg.get("caption", "").strip()
                    cap_str = f" с комментарием: «{cap}»" if cap else ""
                    text = f"[📸 Входящий скриншот/фото]: сохранён в `{photo_path}`{cap_str}"
                    send_message(f"📥 Скриншот успешно получен и передан в IDE!{cap_str}", chat_id=chat_id)
                else:
                    send_message("❌ Ошибка при сохранении входящего скриншота.", chat_id=chat_id)
                    return

    # 2. Обработка входящих документов и файлов
    elif "document" in msg:
        doc_info = msg.get("document", {})
        file_id = doc_info.get("file_id")
        orig_name = doc_info.get("file_name", f"doc_{time.time_ns()}.dat")
        dest_path = os.path.join(MEDIA_DIR, f"incoming_{orig_name}")
        with ActionKeeper("upload_document", chat_id):
            if download_telegram_file(file_id, dest_path):
                cap = msg.get("caption", "").strip()
                cap_str = f" (комментарий: «{cap}»)" if cap else ""
                text = f"[📄 Входящий файл]: сохранён в `{dest_path}`{cap_str}"
                send_message(f"📥 Файл `{orig_name}` успешно сохранён и передан в IDE!", chat_id=chat_id)
            else:
                send_message("❌ Ошибка при загрузке документа.", chat_id=chat_id)
                return

    # 3. Обработка голосовых сообщений (STT)
    elif "voice" in msg or "audio" in msg:
        audio_info = msg.get("voice") or msg.get("audio")
        file_id = audio_info.get("file_id")
        with ActionKeeper("record_voice", chat_id):
            voice_file = os.path.join(MEDIA_DIR, f"voice_{time.time_ns()}.ogg")
            if download_telegram_file(file_id, voice_file):
                transcribed = transcribe_audio_file(voice_file)
                if transcribed:
                    text = f"[🎙 Голосовое сообщение]: {transcribed}"
                else:
                    send_message("❌ Не удалось распознать голосовое сообщение.", chat_id=chat_id)
                    return
            else:
                send_message("❌ Ошибка загрузки голосового сообщения.", chat_id=chat_id)
                return

    if reply_prefix:
        text = f"{reply_prefix}\n{text}".strip()

    clean_text = (msg.get("text") or msg.get("caption") or "").strip().lower()

    # 4. Проверка сервисных команд моста через command_router
    if clean_text and dispatch_command(clean_text, chat_id, user):
        return

    # 5. Перекладывание рабочего сообщения в гарантированную FIFO очередь для IDE
    payload = {
        "chat_id": chat_id,
        "user": user,
        "text": text,
        "timestamp": time.time()
    }
    push_message(payload)
    send_chat_action("typing", chat_id=chat_id)

def run_bridge():
    global _last_poll_heartbeat
    log("Starting Telegram <-> Antigravity IDE Bridge Daemon with Hardware Mutex...")

    mutex = WindowsNamedMutex("Antigravity_TG_Bridge_Mutex")
    if not mutex.acquire():
        log("⚠️ Another tg_bridge instance is already running (Mutex held). Exiting cleanly.")
        sys.exit(0)

    try:
        me = tg_api_post("getMe")
        if not me.get("ok"):
            log(f"Failed to connect to Telegram Bot API: {me}")
            sys.exit(1)

        bot_username = me.get("result", {}).get("username", "Bot")
        log(f"✅ Connected to @{bot_username}")

        set_bot_commands()
        ensure_watchdog_running()
        _start_auto_ack_watchdog()
        _start_liveness_watchdog()

        offset = None
        consecutive_errors = 0
        while True:
            _last_poll_heartbeat = time.time()
            try:
                params = {"timeout": 25}
                if offset is not None:
                    params["offset"] = offset

                updates = tg_api_post("getUpdates", params)
                _last_poll_heartbeat = time.time()
                if updates.get("ok"):
                    consecutive_errors = 0
                    for upd in updates.get("result", []):
                        offset = upd.get("update_id") + 1
                        if "message" in upd:
                            handle_message(upd["message"])
                        elif "callback_query" in upd:
                            cb = upd["callback_query"]
                            tg_api_post("answerCallbackQuery", {"callback_query_id": cb.get("id")})
                            handle_message({
                                "chat": cb.get("message", {}).get("chat", {}),
                                "from": cb.get("from", {}),
                                "text": cb.get("data")
                            })
                else:
                    consecutive_errors += 1
                    sleep_sec = min(30, 2 + consecutive_errors * 2)
                    log(f"⚠️ getUpdates failure ({consecutive_errors}): {updates.get('error')}")
                    if consecutive_errors == 5:
                        try:
                            from incident_manager import report_bridge_incident
                            report_bridge_incident("TG_BRIDGE", f"getUpdates persistent failure: {updates.get('error')}")
                        except Exception:
                            pass
                    time.sleep(sleep_sec)
            except Exception as e:
                consecutive_errors += 1
                sleep_sec = min(30, 2 + consecutive_errors * 2)
                log(f"[Bridge Loop Error ({consecutive_errors})] {e}")
                if consecutive_errors == 5:
                    try:
                        from incident_manager import report_bridge_incident
                        report_bridge_incident("TG_BRIDGE", f"Persistent loop errors: {e}")
                    except Exception:
                        pass
                time.sleep(sleep_sec)
    finally:
        mutex.release()

if __name__ == "__main__":
    run_bridge()
