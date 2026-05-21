# mainapp.py
import sys, os, sqlite3
from datetime import datetime
from functools import partial
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import logging


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core_files import config
from main_modules import x105_download_data
from webapp import app, reschedule_jobs_for_machine


# === Setup logger khusus mainapp ===
LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

# Create a global scheduler object
scheduler = BackgroundScheduler()


def run_web():
    # Jalankan Flask web server
    logger.info("🚀 Web server started")
    app.run(host="0.0.0.0", port=5002, debug=False)

def download_task_wrapper(machine_name, ip, port, password, sn):
    """Wrapper to call download data for a specific machine."""
    logger.info(f"🕒 Scheduler triggered for '{machine_name}' ({ip}:{port}) at {datetime.now()}")
    try:
        # Call the download function with specific machine details
        x105_download_data.main(ip=ip, port=port, password=password, sn=sn)
    except Exception as e:
        logger.error(f"Error running download_data for '{machine_name}': {e}")


def schedule_jobs():
    """Reads machine schedules from the database and creates jobs."""
    try:
        conn = sqlite3.connect(config.SQLITE_FILENAME)
        cursor = conn.cursor()
        # Get all machines that have a sync_schedule defined
        cursor.execute("SELECT id, name, ip_address, port, sn, sync_schedule FROM machines WHERE sync_schedule IS NOT NULL AND sync_schedule != ''")
        machines = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"DB Error: Could not read machines for scheduling. {e}")
        machines = []

    if not machines:
        logger.warning("No machines with a schedule found in the database. No jobs scheduled.")
        # Fallback to old hardcoded job if you want
        # scheduler.add_job(...)
    else:
        logger.info(f"Found {len(machines)} machine(s) with schedules.")

    for machine in machines:
        # Delegate the actual job creation to the function in webapp
        # This keeps the logic consistent
        reschedule_jobs_for_machine(scheduler, machine)

    scheduler.start()
    logger.info("📋 All jobs registered: %s", scheduler.get_jobs())


def main():
    # Pass the scheduler instance to the Flask app context
    app.scheduler = scheduler

    # Start scheduler
    schedule_jobs()

    # Jalankan Flask langsung (blocking)
    run_web()

if __name__ == "__main__":
    # Ensure DB and paths exist before starting
    config.ensure_paths()
    main()
