import os
import sys
import json
import time
import traceback

INCIDENTS_FILE = os.path.join(os.path.dirname(__file__), "incidents.json")

def report_bridge_incident(service_name: str, error_msg: str, tb: str = None, target_file: str = None) -> bool:
    """
    Автоматически фиксирует инцидент моста в файловой очереди incidents.json
    для автономного устранения сбоя агентом IDE.
    """
    if tb is None:
        tb = traceback.format_exc()
        
    incident_payload = {
        "type": "CRITICAL_INCIDENT",
        "service": service_name,
        "error": str(error_msg),
        "traceback": str(tb),
        "timestamp": time.time()
    }
    
    print(f"\n🚨 [INCIDENT DETECTED in {service_name}]: {error_msg}\n{tb}\n", flush=True)
    
    inc_file = target_file or INCIDENTS_FILE
    lock_file = inc_file + ".lock"
    try:
        import portalocker
        with portalocker.Lock(lock_file, timeout=5, fail_when_locked=False):
            incidents = []
            if os.path.exists(inc_file):
                try:
                    with open(inc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            incidents = data
                except Exception:
                    incidents = []
            incidents.append(incident_payload)
            with open(inc_file, "w", encoding="utf-8") as f:
                json.dump(incidents, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
