"""
tools/tasks_checker.py
======================
Мониторинг активных процессов и фоновых служб Antigravity Universal Bridge в Windows.
"""

import sys
import subprocess
import urllib.request
import json

def get_background_tasks_report() -> str:
    lines = ["⚙️ **Активные фоновые задачи и процессы моста:**\n"]

    detected = set()
    try:
        cmd = 'Get-CimInstance Win32_Process -Filter "Name like \'python%\'" | Select-Object ProcessId, CommandLine, WorkingSetSize | ConvertTo-Json'
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        if res.stdout.strip():
            raw_data = json.loads(res.stdout)
            proc_list = raw_data if isinstance(raw_data, list) else [raw_data]
            for proc in proc_list:
                cmdline = proc.get("CommandLine") or ""
                pid = proc.get("ProcessId", 0)
                ws = proc.get("WorkingSetSize") or 0
                mem_mb = round(int(ws) / (1024 * 1024), 1)
                
                if "tg_bridge.py" in cmdline:
                    lines.append(f"• 🟢 **Telegram Bridge Daemon** (PID `{pid}`, `{mem_mb} МБ`)\n  └ Статус: `Активен (Long-polling)`")
                    detected.add("tg")
                elif "vk_bridge.py" in cmdline:
                    lines.append(f"• 🔵 **VK Bridge Daemon** (PID `{pid}`, `{mem_mb} МБ`)\n  └ Статус: `Активен (LongPoll)`")
                    detected.add("vk")
                elif "universal_receiver.py" in cmdline:
                    lines.append(f"• ⚡ **Universal Receiver** (PID `{pid}`, `{mem_mb} МБ`)\n  └ Статус: `Активен (Шина сообщений)`")
                    detected.add("receiver")
    except Exception:
        pass

    if not detected:
        lines.append("• ℹ️ Демоны моста не обнаружены среди процессов Python.")

    lines.append("\n• 🔒 **Аппаратные мьютексы**: `WindowsNamedMutex (kernel32)`")
    lines.append("• ⚡ **Шина сообщений**: `Бессетевой IPC (OS file locks)`")

    return "\n".join(lines)

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    print(get_background_tasks_report())
