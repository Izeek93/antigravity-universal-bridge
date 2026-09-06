# 🛰 Antigravity Universal Bridge

[![Release](https://img.shields.io/github/v/release/Izeek93/antigravity-universal-bridge?color=blue&style=flat-square)](https://github.com/Izeek93/antigravity-universal-bridge/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?style=flat-square&logo=githubsponsors)](https://github.com/sponsors/Izeek93)
[![Boosty](https://img.shields.io/badge/Boosty-Donate-f15f2c.svg?style=flat-square&logo=boosty)](https://boosty.to/izeek)
[![YooMoney](https://img.shields.io/badge/YooMoney-Donate-8b3ffd.svg?style=flat-square)](https://yoomoney.ru/to/410011192281528)

> **Высоконадежный двусторонний I/O мост-зеркало между Telegram / ВКонтакте и активной сессией Google Antigravity IDE.**

Мост превращает мессенджеры в полноценный удаленный терминал для управления кодом, задачами и диалогом с агентом Antigravity прямо с телефона или любого устройства: голос, текст, скриншоты экрана, интерактивные согласования и автономная консолидация памяти.

---

## 🚀 Что нужно от пользователя (Быстрый старт за 3 минуты)

Для работы **НЕ требуются** внешние платные ключи OpenAI, Gemini API или Polza AI — мост использует мощности активной сессии вашей IDE.

Всё, что вам нужно — это токены мессенджеров, которыми вы планируете пользоваться.

### Шаг 1. Получение токенов (1-2 минуты)

* **Для Telegram (если нужен TG):**
  1. Напишите боту [@BotFather](https://t.me/BotFather) в Telegram команду `/newbot`.
  2. Задайте имя и юзернейм (например, `MyAgyDevBot`).
  3. Скопируйте выданный токен (вида `123456789:ABCdefGHI...`).
  4. *(Опционально)* Узнайте свой числовой ID через бота [@userinfobot](https://t.me/userinfobot), чтобы бот отвечал только вам.

* **Для ВКонтакте (если нужен VK):**
  1. Зайдите в настройки вашего сообщества ВКонтакте ➔ *«Работа с API»*.
  2. Нажмите *«Создать ключ»*, отметьте галочки **«Сообщения сообщества»** и **«Фотографии»** ➔ скопируйте ключ.
  3. В разделе *«Сообщения»* сообщества включите *«Сообщения сообщества: Включены»*.
  4. Запомните числовой ID группы (из адресной строки сообщества).

---

### Шаг 2. Настройка файла `.env`

Сделайте копию шаблона настроек:
```bash
cp .env.example .env
```
Откройте файл `.env` в блокноте или редакторе и вставьте полученные ключи:

```env
# Токен Telegram (если используете Telegram):
TG_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
ALLOWED_CHAT_IDS="ваш_числовой_id"

# Токены VK (если используете ВКонтакте):
VK_GROUP_TOKEN="vk1.a.ваш_токен_группы"
VK_GROUP_ID="123456789"
```
*(Если пользуетесь только Telegram — блок VK можно оставить пустым, и наоборот).*

---

### Шаг 3. Установка зависимостей

В терминале выполните:
```bash
pip install -r requirements.txt
```

---

### Шаг 4. Запуск моста

Запустите единый лаунчер:
```bash
python run_bridge.py
```
> **Всё готово!** Напишите любое сообщение или отправьте голосовое в своего Telegram-бота или в сообщения группы ВК — Antigravity IDE мгновенно примет задачу и ответит вам.

---

## 🎮 Доступные команды в мессенджерах

Все сервисные команды оформлены в виде нативных слэш-команд (доступны в меню `[ Menu ☰ ]` Telegram и в кнопках VK):

| Команда | Описание |
| :--- | :--- |
| **`/status`** | 🟢 Диагностика моста, статус очереди и состояние самовосстановления. |
| **`/limits`** | 📊 Отчет о расходе токенов контекста сессии, квотах Gemini и RAM. |
| **`/tasks`** | ⚙️ Список активных фоновых процессов, демонов и утилит в Windows. |
| **`/screen`** | 📸 Нативный скриншот экрана рабочего стола без сторонних программ. |
| **`/voice`** | 🔊 Переключение голосового режима (`/voice on` / `/voice off`). |
| **`/new`** | 🔄 Открытие чистой сессии Antigravity IDE с нулевым контекстом. |
| **`/help`** | ℹ️ Справочная панель со всеми возможностями моста. |

---

## 🧠 Ключевые возможности

### 1. Зеркало активной сессии IDE
Никаких посредников и симуляторов. Ваши реплики из Telegram/VK через потокобезопасную очередь (`portalocker`) попадают прямо в контекст работающего агента Antigravity, а ответы агента мгновенно транслируются обратно.

### 2. Защита от дублей (Hardware Mutex)
Оба демона защищены на уровне ядра Windows через `WindowsNamedMutex (kernel32)`:
- `Antigravity_TG_Bridge_Mutex`
- `Antigravity_VK_Bridge_Mutex`
Случайный запуск двух одинаковых процессов невозможен физически. При падении или перезапуске ОС дескриптор освобождается автоматически.

### 3. Удаленные согласования (Human-in-the-Loop)
Когда агент запрашивает подтверждение рискованного действия или плана выполнения задач, в мессенджер приходят интерактивные инлайн-кнопки:
`[✅ Утвердить]` / `[❌ Отклонить]`. Подтверждение применяется за 0.1 секунды.

---

## 📁 Структура проекта

```text
antigravity-universal-bridge/
├── .gitignore                  # Полная защита секретов, токенов, баз и бинарников
├── .env.example                # Шаблон переменных окружения
├── requirements.txt            # Легковесные зависимости (без лишних LLM-библиотек)
├── run_bridge.py               # Единый лаунчер запуска всех служб
├── README.md                   # Руководство пользователя
├── ARCHITECTURE.md             # Архитектурная спецификация (Ports & Adapters)
│
├── core/                       # 🧠 Ядро моста (не зависит от соцсетей)
│   ├── windows_mutex.py        # Аппаратный мьютекс ядра Windows
│   ├── queue_protocol.py       # Потокобезопасные очереди с OS file lock
│   └── universal_receiver.py   # Центральная шина событий сессии IDE
│
├── adapters/                   # 🔌 Адаптеры мессенджеров
│   ├── telegram/               # Telegram: Long-polling, клавиатуры, парсинг HTML
│   │   ├── tg_bridge.py
│   │   ├── tg_config.py
│   │   ├── send_tg.py
│   │   └── command_router.py
│   └── vk/                     # VK: LongPoll, клавиатуры, форматирование
│       ├── vk_bridge.py
│       ├── vk_config.py
│       ├── send_vk.py
│       └── command_router.py
│
└── tools/                      # 🛠 Системные утилиты и диагностика
    ├── limits_checker.py       # Мониторинг квот контекста и памяти
    ├── tasks_checker.py        # Монитор активных фоновых процессов
    ├── screenshot.py           # Нативный захват экрана Windows (GDI/PIL)
    ├── local_stt.py            # Офлайн-распознавание голосовых (Faster-Whisper)
    ├── voice_engine.py         # Фонетическая нормализация речи
    └── session_manager.py      # Управление сессиями чата Antigravity IDE CLI
```

---

## 🔒 Безопасность (Zero-Trust)
- Все токены и приватные ключи хранятся строго в `.env` и никогда не попадают в Git.
- Никакие персональные данные (Chat ID, логи диалогов, скриншоты) не сохраняются в коде.
- Все системные файлы рантайма изолированы мастер-фильтром `.gitignore`.

---

## 💖 Спонсорство и поддержка проекта

Если **Antigravity Universal Bridge** помогает вам в работе и разработке, вы можете поддержать автора и дальнейшее развитие проекта удобным для вас способом:

* 💖 **[GitHub Sponsors (Международная поддержка)](https://github.com/sponsors/Izeek93)**
* 🚀 **[Boosty (Эксклюзивные обновления, подписки и донаты)](https://boosty.to/izeek)**
* 💳 **[ЮMoney (Прямой перевод по СБП и картам)](https://yoomoney.ru/to/410011192281528)**

<p align="left">
  <a href="https://github.com/sponsors/Izeek93"><img src="https://img.shields.io/badge/Sponsor-%E2%99%A5%20Izeek93-ea4aaa?style=for-the-badge&logo=githubsponsors" alt="GitHub Sponsors" /></a>
  <a href="https://boosty.to/izeek"><img src="https://img.shields.io/badge/Boosty-Поддержать-f15f2c?style=for-the-badge&logo=boosty" alt="Boosty" /></a>
  <a href="https://yoomoney.ru/to/410011192281528"><img src="https://img.shields.io/badge/ЮMoney-Перевод%20СБП-8b3ffd?style=for-the-badge" alt="YooMoney" /></a>
</p>

Ваша поддержка помогает создавать новые адаптеры (Discord, Webhooks), развивать локальный AI-стек и поддерживать экосистему в актуальном состоянии!

---

## 📄 Лицензия

Проект распространяется под свободной лицензией [MIT License](LICENSE).

