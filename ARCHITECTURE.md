# 📐 Архитектура Antigravity Universal Bridge

## 1. Архитектурный паттерн: Ports & Adapters (Гексагональная архитектура)

Проект спроектирован по принципу **модульного монолита** с разделением ответственности:

```
[ Telegram API ]  ──> [ adapters/telegram ] ──┐
                                               ├──> [ core/queue_protocol ] ──> [ core/universal_receiver ] ──> [ Antigravity IDE ]
[ VK LongPoll  ]  ──> [ adapters/vk       ] ──┘                                                                        │
                                                                                                                       │
[ Пользователь ]  <── [ send_tg / send_vk ] <──────────────────────────────────────────────────────────────────────────┘
```

### Ключевые компоненты:
1. **Core (Ядро системы):**
   - Не знает о деталях конкретных мессенджеров (Telegram/VK/Discord).
   - Оперирует универсальной структурой сообщений: `source`, `chat_id`, `user`, `text`, `timestamp`, `attachments`.
   - Отвечает за бессетевое IPC (Inter-Process Communication) через файл `inbox.json` с гарантированными системными блокировками (`portalocker`).

2. **Adapters (Адаптеры платформ):**
   - Изолированные модули ввода/вывода под конкретные API.
   - Отвечают за сетевой протокол (Long-polling у Telegram, LongPoll у VK), парсинг входящих сообщений (текст, голосовые через STT, фото) и отправку ответов с форматированием.
   - Превращают специфичные события платформ в единый формат сообщения очереди `MessageQueue.push()`.

3. **Tools (Системные утилиты):**
   - Общие инструменты телеметрии, захвата экрана и распознавания речи, доступные любому адаптеру без дублирования кода.

---

## 2. Как добавить новую платформу (например, Discord или MAX) без переделки ядра

Благодаря модульности, добавление нового адаптера занимает **3 простых шага**:

### Шаг 1. Создать каталог адаптера
Создайте папку `adapters/discord/`:
```text
adapters/discord/
├── __init__.py
├── config.py             # Считывание DISCORD_BOT_TOKEN из корневого .env
├── discord_bridge.py     # Слушатель событий Discord
└── send_discord.py       # Отправка сообщений в канал
```

### Шаг 2. Подключить очередь сообщений ядра
В `discord_bridge.py` добавьте отправку в очередь:
```python
from core.queue_protocol import MessageQueue

QUEUE = MessageQueue("adapters/discord/inbox.json")

def on_discord_message(msg):
    QUEUE.push({
        "source": "DISCORD",
        "chat_id": msg.channel.id,
        "user": str(msg.author),
        "text": msg.content
    })
```

### Шаг 3. Добавить опрос очереди в `core/universal_receiver.py`
В `core/universal_receiver.py` добавьте одну строку:
```python
DISCORD_QUEUE = MessageQueue(os.path.join(BASE_DIR, "adapters", "discord", "inbox.json"))
...
discord_msgs = DISCORD_QUEUE.pop_all(source_label="DISCORD")
```

**Ни ядро, ни существующие адаптеры не требуют никаких модификаций.**

---

## 3. Механизмы надежности и отказоустойчивости

1. **Аппаратные мьютексы Windows (Hardware Named Mutex):**
   Каждый демон запускается под именованным мьютексом ядра Windows (`ctypes.windll.kernel32.CreateMutexW`). Это исключает дублирование процессов, даже если пользователь нажал запуск дважды.

2. **Бессетевой IPC:**
   Обмен между мостом и IDE происходит через атомарные файловые очереди. Это устраняет необходимость открывать порты TCP/HTTP (исключает конфликты `EADDRINUSE` и блокировки сетевым экраном Windows Defender).

3. **Auto-Ack Watchdog:**
   Если сообщение принято, но IDE занята сложной задачей >15 секунд, мост автоматически информирует пользователя: *«⏳ Сообщение принято в работу Antigravity IDE...»*, предотвращая повторные запросы.

4. **Liveness Watchdog:**
   Сетевые сокеты защищены жестким сокетным таймаутом (35 секунд). При обрыве соединения процесс не зависает в цикле ожидания, а мягко переподключается с экспоненциальным backoff.
