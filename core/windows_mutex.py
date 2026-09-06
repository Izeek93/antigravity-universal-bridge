"""
core/windows_mutex.py
=====================
Аппаратный Single-Instance Mutex ядра Windows (kernel32).
Гарантирует 100% запуск строго одного экземпляра демона на уровне операционной системы.
Автоматически освобождается ядром Windows при падении или штатном завершении процесса.
"""

import sys
import ctypes

ERROR_ALREADY_EXISTS = 183

class WindowsNamedMutex:
    def __init__(self, mutex_name: str):
        self.mutex_name = mutex_name
        self.handle = None
        self.is_owner = False

    def acquire(self) -> bool:
        """Попытка захвата мьютекса. Возвращает True, если экземпляр первый и единственный."""
        if sys.platform != 'win32':
            return True

        kernel32 = ctypes.windll.kernel32
        self.handle = kernel32.CreateMutexW(None, True, self.mutex_name)
        last_err = kernel32.GetLastError()
        
        if last_err == ERROR_ALREADY_EXISTS or not self.handle:
            if self.handle:
                kernel32.CloseHandle(self.handle)
                self.handle = None
            self.is_owner = False
            return False

        self.is_owner = True
        return True

    def release(self):
        """Освобождение дескриптора мьютекса."""
        if sys.platform == 'win32' and self.handle and self.is_owner:
            try:
                ctypes.windll.kernel32.ReleaseMutex(self.handle)
                ctypes.windll.kernel32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None
            self.is_owner = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Процесс с мьютексом '{self.mutex_name}' уже запущен в системе.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
