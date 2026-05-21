# config.py
import os
import sys

# Device Type Detection
DEVICE_TYPE = "X105"  # X105 uses TCP, X100 uses SOAP

# X105 Configuration (TCP Protocol)
X105_CONFIG = {
    "ip": "192.168.1.33",
    "port": 4370,
    "password": "",  # Usually empty for X105
    "timeout": 20
}

# Legacy X100 Configuration (SOAP Protocol) - for backward compatibility
X100_CONFIG = {
    "ip": "192.168.1.201",
    "comm_key": "0",
    "port": 80,
    "timeout": 20
}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # core_files folder
# project root assumed one level up
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "db_files")
EXPORT_DIR_CSV = os.path.join(PROJECT_ROOT, "exports", "csv")
EXPORT_DIR_JSON = os.path.join(PROJECT_ROOT, "exports", "json")

# Default db file names (you can override)
SQLITE_FILENAME = os.path.join(DB_DIR, "x105.db")
MDB_BACKUP_FILENAME = os.path.join(DB_DIR, "attBackup.mdb")

# Active configuration based on device type
if DEVICE_TYPE == "X105":
    DEFAULT_IP = X105_CONFIG["ip"]
    DEFAULT_PORT = X105_CONFIG["port"]
    DEFAULT_PASSWORD = X105_CONFIG["password"]
    DEFAULT_TIMEOUT = X105_CONFIG["timeout"]
else:
    DEFAULT_IP = X100_CONFIG["ip"]
    DEFAULT_PORT = X100_CONFIG["port"]
    DEFAULT_KEY = X100_CONFIG["comm_key"]
    DEFAULT_TIMEOUT = X100_CONFIG["timeout"]

# Export Settings
EXPORT_CONFIG = {
    "csv_path": EXPORT_DIR_CSV,
    "json_path": EXPORT_DIR_JSON,
    "auto_timestamp": True
}

# Logging Configuration (left as simple dict)
LOGGING_CONFIG = {
    "level": "INFO",
    "log_file": os.path.join(PROJECT_ROOT, "logs", "device.log"),
    "max_log_size": 10 * 1024 * 1024,
    "backup_count": 5
}

def ensure_paths():
    """Create folders if missing (db_files, exports/csv, exports/json)"""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR_CSV, exist_ok=True)
    os.makedirs(EXPORT_DIR_JSON, exist_ok=True)
    logs_dir = os.path.dirname(LOGGING_CONFIG["log_file"])
    if logs_dir:
        os.makedirs(logs_dir, exist_ok=True)

def get_device_params():
    """Ambil parameter device dari command line atau input"""
    ip = DEFAULT_IP
    if DEVICE_TYPE == "X105":
        port = DEFAULT_PORT
        password = DEFAULT_PASSWORD

        # Parse command line arguments like ip=..., port=..., password=...
        for arg in sys.argv[1:]:
            if arg.startswith("ip="):
                ip = arg.split("=", 1)[1]
            elif arg.startswith("port="):
                try:
                    port = int(arg.split("=", 1)[1])
                except Exception:
                    pass
            elif arg.startswith("password="):
                password = arg.split("=", 1)[1]

        return ip, port, password

    else:
        # X100 compatibility (kept minimal)
        key = DEFAULT_KEY
        port = DEFAULT_PORT
        for arg in sys.argv[1:]:
            if arg.startswith("ip="):
                ip = arg.split("=", 1)[1]
            elif arg.startswith("key="):
                key = arg.split("=", 1)[1]
            elif arg.startswith("port="):
                try:
                    port = int(arg.split("=", 1)[1])
                except Exception:
                    pass
        return ip, key, port

def get_client(ip: str = None, port: int = None, password: str = None, sn: str = None):
    """
    Return X105Client instance using configured/default IP/PORT.
    If ip/port are provided, they are used. Otherwise, it falls back to
    command-line arguments or default config values.
    """
    # ensure folders exist
    ensure_paths()

    if DEVICE_TYPE == "X105":
        from core_files.x105_machine import X105Client

        # If no specific IP is given, get from defaults/args
        if ip is None:
            ip, port, password = get_device_params()

        # If password is not provided for a specific IP, use the default
        if password is None:
            password = DEFAULT_PASSWORD

        return X105Client(ip=ip, port=port, password=password, sn=sn, timeout=DEFAULT_TIMEOUT)
    else:
        from core_files.x100_client import X100Client
        ip, key, port = get_device_params()
        return X100Client(ip=ip, key=key, port=port)

if __name__ == "__main__":
    ensure_paths()
    print("Config OK")
    print("DB path:", SQLITE_FILENAME)
