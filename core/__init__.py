"""
Antigravity Universal Bridge Core
"""
from .windows_mutex import WindowsNamedMutex
from .queue_protocol import MessageQueue

__all__ = ["WindowsNamedMutex", "MessageQueue"]
