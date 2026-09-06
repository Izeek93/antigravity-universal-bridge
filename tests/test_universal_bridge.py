"""
tests/test_universal_bridge.py
==============================
Автоматизированный комплексный тестовый набор для Antigravity Universal Bridge.
Проверяет:
1. Аппаратный мьютекс Windows (Single-Instance Mutex).
2. Потокобезопасные очереди сообщений (Queue Protocol с OS file-lock).
3. Форматтеры Markdown -> Telegram HTML и VK Text.
4. Системную диагностику (limits_checker, tasks_checker, screenshot).
"""

import unittest
import os
import sys
import time
import json
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.windows_mutex import WindowsNamedMutex
from core.queue_protocol import MessageQueue
from adapters.telegram.tg_formatter import md_to_tg_html
from adapters.vk.vk_formatter import format_for_vk
from tools.limits_checker import format_limits_report
from tools.tasks_checker import get_background_tasks_report
from tools.screenshot import capture_desktop

class TestUniversalBridge(unittest.TestCase):

    def test_01_windows_named_mutex(self):
        """Проверка работы аппаратного мьютекса ядра Windows и защиты от дублей."""
        m_name = f"Test_Agy_Bridge_Mutex_{os.getpid()}"
        m1 = WindowsNamedMutex(m_name)
        self.assertTrue(m1.acquire(), "Первый процесс должен успешно захватить мьютекс")

        # Вторая попытка захвата должна вернуть False
        m2 = WindowsNamedMutex(m_name)
        self.assertFalse(m2.acquire(), "Второй процесс НЕ должен захватить уже занятый мьютекс")

        m1.release()
        self.assertFalse(m1.is_owner, "После release мьютекс должен быть свободен")

        # Теперь m2 может захватить
        self.assertTrue(m2.acquire(), "После освобождения мьютекс должен захватываться повторно")
        m2.release()

    def test_02_queue_protocol(self):
        """Проверка атомарности и порядка FIFO очереди сообщений."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            inbox_path = os.path.join(tmp_dir, "test_inbox.json")
            queue = MessageQueue(inbox_path)

            msg1 = {"user": "alice", "text": "Task 1", "chat_id": 101}
            msg2 = {"user": "bob", "text": "Task 2", "chat_id": 102}

            self.assertTrue(queue.push(msg1))
            self.assertTrue(queue.push(msg2))

            popped = queue.pop_all(source_label="TEST")
            self.assertEqual(len(popped), 2)
            self.assertEqual(popped[0]["text"], "Task 1")
            self.assertEqual(popped[0]["source"], "TEST")
            self.assertEqual(popped[1]["text"], "Task 2")

            # Очередь должна быть пуста после извлечения
            self.assertEqual(len(queue.pop_all()), 0)

    def test_03_telegram_formatter(self):
        """Проверка конвертера Markdown в валидный Telegram HTML."""
        raw_md = "**Жирный** и *курсив* и `код` и [Ссылка](https://example.com)"
        html = md_to_tg_html(raw_md)
        self.assertIn("<b>Жирный</b>", html)
        self.assertIn("<i>курсив</i>", html)
        self.assertIn("<code>код</code>", html)
        self.assertIn('<a href="https://example.com">Ссылка</a>', html)

    def test_04_vk_formatter(self):
        """Проверка адаптации Markdown под специфику ВКонтакте."""
        raw_md = "# Заголовок\n**Важно:** текст"
        vk_text = format_for_vk(raw_md)
        self.assertIsInstance(vk_text, str)
        self.assertIn("Важно:", vk_text)

    def test_05_screenshot_capture(self):
        """Проверка захвата экрана рабочего стола Windows."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_file = os.path.join(tmp_dir, "screen.png")
            out = capture_desktop(shot_file)
            self.assertTrue(os.path.exists(out), "Файл скриншота должен существовать")
            self.assertTrue(os.path.getsize(out) > 500, "Размер скриншота должен быть больше 500 байт")

    def test_06_limits_report(self):
        """Проверка генератора отчета по квотам контекста."""
        report = format_limits_report()
        self.assertIsInstance(report, str)
        self.assertIn("Gemini", report)
        self.assertTrue(len(report) > 30)

    def test_07_tasks_report(self):
        """Проверка мониторинга процессов Windows."""
        report = get_background_tasks_report()
        self.assertIsInstance(report, str)
        self.assertIn("мьютекс", report.lower())

    def test_08_remote_approval_lifecycle(self):
        """Проверка жизненного цикла удаленного согласования действий в IDE."""
        from adapters.telegram.remote_approval_manager import request_remote_approval, resolve_approval, get_pending_approval, APPROVAL_FILE
        req = request_remote_approval("Тестовое действие для код-ревью")
        self.assertIsNotNone(req)
        
        pending = get_pending_approval()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.get("status"), "PENDING")
        
        ok = resolve_approval(True)
        self.assertTrue(ok)
        self.assertIsNone(get_pending_approval())
        
        if os.path.exists(APPROVAL_FILE):
            try:
                os.remove(APPROVAL_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
