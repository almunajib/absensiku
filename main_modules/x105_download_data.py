# main_modules/x105_download_data.py
import os
import sys
import csv
import json
import sqlite3
from datetime import datetime, date
import logging
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core_files import config

SQLITE_FILENAME = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "db_files", "x105.db"
)


EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "export_files")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "download_data.log")

# === Setup logger ===
logger = logging.getLogger("download_data")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)


def save_to_sqlite(logs):
    """Insert logs ke SQLite dengan cek duplikat."""
    if not logs:
        return 0

    conn = sqlite3.connect(SQLITE_FILENAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkinout (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT,
            checktime DATETIME,
            verifycode INTEGER,
            workcode INTEGER,
            sn TEXT,
            UNIQUE(userid, checktime, sn)
        )
    """)

    inserted = 0
    for log in logs:
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO checkinout (userid, checktime, verifycode, workcode, sn)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    log["userid"],
                    log["checktime"],
                    log["verifycode"],
                    log["workcode"],
                    log["sn"],
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            logger.warning(f"Gagal insert log {log}: {e}")

    conn.commit()
    conn.close()
    return inserted


def update_db_record_count(machine_sn):
    """Updates the total record count in the machines table for a given machine SN."""
    if not machine_sn:
        return

    try:
        conn = sqlite3.connect(SQLITE_FILENAME)
        cur = conn.cursor()

        # Count records for this SN
        cur.execute("SELECT COUNT(*) FROM checkinout WHERE sn = ?", (machine_sn,))
        count = cur.fetchone()[0]

        # Update the machines table
        cur.execute("UPDATE machines SET db_record_count = ? WHERE sn = ?", (count, machine_sn))
        conn.commit()
        logger.info(f"Updated DB record count for machine SN '{machine_sn}' to {count}.")

    except Exception as e:
        logger.error(f"Failed to update DB record count for SN '{machine_sn}': {e}")
    finally:
        if conn:
            conn.close()

def export_to_csv_json(logs, filename_suffix="today"):
    """Export ke CSV dan JSON di folder export_files/."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    filename_base = f"x105_attendance_{filename_suffix}"

    csv_path = os.path.join(EXPORT_DIR, filename_base + ".csv")
    json_path = os.path.join(EXPORT_DIR, filename_base + ".json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
    logger.info(f"Data exported to {csv_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    logger.info(f"Data exported to {json_path}")


def filter_today(logs):
    today_str = date.today().strftime("%Y-%m-%d")
    return [log for log in logs if log["checktime"].startswith(today_str)]


def filter_range_date(logs, start_date, end_date):
    start_dt = datetime.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
    return [
        log
        for log in logs
        if start_dt
        <= datetime.strptime(log["checktime"], "%Y-%m-%d %H:%M:%S")
        <= end_dt
    ]


def main(ip=None, port=None, password=None, sn=None, mode="today", start=None, end=None):
    """
    Main function to download data. Can be called with specific machine params.
    If no params, falls back to command-line args or config defaults.
    """
    parser = argparse.ArgumentParser(
        description="Download and filter attendance logs from X105 machine"
    )
    parser.add_argument(
        "cmd_mode",
        choices=["today", "range", "all"],
        nargs="?",
        default="today",
        help="Download mode: today / range / all (default: today)",
    )
    parser.add_argument("--cmd_start", help="Start date (YYYY-MM-DD) for range mode")
    parser.add_argument("--cmd_end", help="End date (YYYY-MM-DD) for range mode")
    args = parser.parse_args()

    # Determine mode and date range
    used_mode = mode if mode else args.cmd_mode
    used_start = start if start else args.cmd_start
    used_end = end if end else args.cmd_end

    # If called from scheduler, ip/port will be provided.
    # If called from command line, get client from config.
    if ip and port:
        client = config.get_client(ip=ip, port=port, password=password, sn=sn)
    else:
        client = config.get_client()
    
    logs, msg = client.get_attendance_logs()
    if not logs:
        logger.error(f"No logs: {msg}")
        return 0

    if used_mode == "today":
        selected_logs = filter_today(logs)
        suffix = date.today().strftime("%Y-%m-%d")
    elif used_mode == "range":
        if not used_start or not used_end:
            # This error is for command-line usage
            parser.error("--cmd_start and --cmd_end are required for range mode")
        selected_logs = filter_range_date(logs, used_start, used_end)
        suffix = f"{used_start}_to_{used_end}"
    else:
        selected_logs = logs
        suffix = "all"

    logger.info(f"📥 Retrieved {len(selected_logs)} logs ({used_mode} mode)")
    if not selected_logs:
        logger.info("No logs found in the specified range.")
        return 0

    inserted = save_to_sqlite(selected_logs)
    logger.info(f"✅ {inserted} new records inserted into {SQLITE_FILENAME}")
    export_to_csv_json(selected_logs, filename_suffix=suffix)

    # After saving, update the record count in the database
    if inserted > 0:
       update_db_record_count(sn if sn else client.sn)
    
    return inserted


if __name__ == "__main__":
    # Ensure paths are created for standalone execution
    config.ensure_paths()
    main()
