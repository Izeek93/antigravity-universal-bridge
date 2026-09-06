"""
run_bridge.py
=============
Единая точка входа для запуска Antigravity Universal Bridge.
Одним вызовом стартует активные адаптеры (Telegram, VK) и шину Universal Receiver.
"""

import os
import sys
import subprocess
import time

# UTF-8 вывод на консоли Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

def main():
    print("=" * 65)
    print("🛰  ANTIGRAVITY UNIVERSAL BRIDGE — LAUNCHER")
    print("=" * 65)

    py = sys.executable
    processes = []

    # 1. Проверяем Telegram Adapter
    tg_token = os.getenv("TG_BOT_TOKEN", "").strip()
    if tg_token and "YOUR_" not in tg_token:
        print("🟢 Запуск Telegram Bridge Daemon...")
        tg_script = os.path.join(BASE_DIR, "adapters", "telegram", "tg_bridge.py")
        p_tg = subprocess.Popen([py, tg_script], cwd=os.path.join(BASE_DIR, "adapters", "telegram"))
        processes.append(("Telegram Bridge", p_tg))
    else:
        print("⚪ Telegram токен не задан в .env (пропуск)")

    # 2. Проверяем VK Adapter
    vk_token = os.getenv("VK_GROUP_TOKEN", "").strip()
    if vk_token and "your_vk_" not in vk_token:
        print("🔵 Запуск VK Bridge Daemon...")
        vk_script = os.path.join(BASE_DIR, "adapters", "vk", "vk_bridge.py")
        p_vk = subprocess.Popen([py, vk_script], cwd=os.path.join(BASE_DIR, "adapters", "vk"))
        processes.append(("VK Bridge", p_vk))
    else:
        print("⚪ VK токен не задан в .env (пропуск)")

    if not processes:
        print("\n⚠️  Внимание: В файле .env не задан ни один активный токен!")
        print("👉 Откройте файл .env и укажите TG_BOT_TOKEN или VK_GROUP_TOKEN.")
        sys.exit(1)

    # 3. Запуск Universal Receiver
    print("⚡ Запуск Universal Receiver (Шина сессии IDE)...")
    receiver_script = os.path.join(BASE_DIR, "core", "universal_receiver.py")
    p_rec = subprocess.Popen([py, receiver_script], cwd=BASE_DIR)
    processes.append(("Universal Receiver", p_rec))

    print("\n✅ Все сервисы моста успешно запущены под аппаратными мьютексами.")
    print("💡 Для остановки нажмите Ctrl+C в этом окне.\n" + "-" * 65)

    try:
        while True:
            time.sleep(1.0)
            for name, proc in processes:
                if proc.poll() is not None:
                    # Если завершился receiver (получил сообщение), перезапускаем его
                    if name == "Universal Receiver":
                        p_rec = subprocess.Popen([py, receiver_script], cwd=BASE_DIR)
                        processes[-1] = ("Universal Receiver", p_rec)
    except KeyboardInterrupt:
        print("\n🛑 Остановка всех служб моста...")
        for name, proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        print("👋 Мост остановлен.")

if __name__ == "__main__":
    main()
