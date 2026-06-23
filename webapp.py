from flask import Flask, render_template, jsonify, request, make_response, session, redirect, url_for
import sqlite3
from datetime import datetime
from datetime import date
from functools import partial
from apscheduler.jobstores.base import JobLookupError
import logging
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from core_files.x105_machine import X105Client
from core_files.safe_runner import SafeJobRunner, is_machine_reachable
from main_modules import x105_download_data

DB_PATH = "db_files/x105.db"

app = Flask(__name__)
app.secret_key = "absensiku-tgm-mki-2026"  # Ganti dengan string acak yang aman

# Kredensial login (bisa dipindah ke DB atau .env)
USERS = {
    "admin": "megatamaikon1"  # username: password
}

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated



def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv


def download_task_wrapper(machine_name, ip, port, password, sn, machine_id=None):
    """
    Wrapper to call download data for a specific machine.
    Dilindungi SafeJobRunner agar koneksi yang hang tidak butuh restart systemd.
    """
    logger = logging.getLogger("scheduler")
    logger.info(f"🕒 Scheduler triggered for '{machine_name}' ({ip}:{port}) at {datetime.now()}")

    key = f"machine_{machine_id if machine_id is not None else ip}"

    if not is_machine_reachable(ip, port):
        logger.error(f"Mesin '{machine_name}' tidak dapat dijangkau, skip job ini.")
        return

    ok, msg = SafeJobRunner.start(
        key=key,
        target=x105_download_data.main,
        kwargs=dict(ip=ip, port=port, password=password, sn=sn),
        timeout=90,
    )
    if not ok:
        logger.warning(f"Skip job untuk '{machine_name}': {msg}")
        return

    # Tunggu hasil tanpa membiarkan scheduler hang selamanya
    import time as _t
    deadline = _t.time() + 100
    while _t.time() < deadline:
        result = SafeJobRunner.poll(key)
        if result["status"] in ("done", "error"):
            logger.info(f"Hasil job '{machine_name}': {result.get('message', result)}")
            return
        _t.sleep(3)
    logger.warning(f"Job '{machine_name}' belum selesai setelah 100s polling, lanjut tanpa blocking.")


def reschedule_jobs_for_machine(scheduler, machine_data):
    """Removes old jobs and adds new ones for a specific machine."""
    logger = logging.getLogger("scheduler")
    machine_id, name, ip, port, sn, schedule_str = machine_data

    # 1. Remove all existing jobs for this machine
    for i in range(10): # Assuming max 10 schedules per machine
        job_id = f"download_logs_{machine_id}_{i}"
        try:
            scheduler.remove_job(job_id)
            logger.info(f"✓ Removed old job '{job_id}' for '{name}'.")
        except JobLookupError:
            pass # Job didn't exist, which is fine

    # 2. Add new jobs based on the new schedule string
    if not schedule_str:
        logger.info(f"No schedule for '{name}'. All jobs removed.")
        return

    try:
        schedule_times = [s.strip() for s in schedule_str.split(';') if s.strip()]
        if not schedule_times:
            return

        from core_files import config # Local import to get password

        for i, time_str in enumerate(schedule_times):
            hour, minute = time_str.split(':')
            job_id = f"download_logs_{machine_id}_{i}"
            task_func = partial(download_task_wrapper, machine_name=name, ip=ip, port=port,
                     password=config.DEFAULT_PASSWORD, sn=sn, machine_id=machine_id)

            scheduler.add_job(
                task_func,
                "cron",
                hour=hour,
                minute=minute,
                id=job_id,
                replace_existing=True
            )
            logger.info(f"✓ Rescheduled job '{job_id}' for '{name}' at cron [hour={hour}, minute={minute}]")
    except Exception as e:
        logger.error(f"✗ Failed to parse or reschedule for '{name}' ('{schedule_str}'): {e}.")


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET"])
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def do_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if USERS.get(username) == password:
        session["logged_in"] = True
        session["username"] = username
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Username atau password salah"}), 401

@app.route("/api/logout", methods=["POST"])
def do_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/reports")
def reports():
    return render_template("index.html")

@app.route("/user-setup")
def user_setup():
    return render_template("user_setup.html")


@app.route("/api/users", methods=["GET"])
def get_users():
    client = X105Client()
    users, msg = client.get_users()
    if users:
        # Get department names from the database
        for user in users:
            user_info = query_db(
                "SELECT d.deptname, u.mverifypass, u.defaultdeptid FROM userinfo u LEFT JOIN departments d ON u.defaultdeptid = d.deptid WHERE u.badgenumber = ?",
                [user["user_id"]],
                one=True,
            )
            user["group_id"] = user_info["deptname"] if user_info else "Unknown"
            user["mverifypass"] = user_info["mverifypass"] if user_info else ""
            user["defaultdeptid"] = user_info["defaultdeptid"] if user_info else ""
        return jsonify(users)
    return jsonify([])


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    client = X105Client()
    users, msg = client.get_users()
    user = next((u for u in users if u["user_id"] == user_id), None)
    if user:
        user_info = query_db(
            "SELECT d.deptname, u.mverifypass, u.defaultdeptid FROM userinfo u LEFT JOIN departments d ON u.defaultdeptid = d.deptid WHERE u.badgenumber = ?",
            [user["user_id"]],
            one=True,
        )
        user["group_id"] = user_info["deptname"] if user_info else "Unknown"
        user["mverifypass"] = user_info["mverifypass"] if user_info else ""
        user["defaultdeptid"] = user_info["defaultdeptid"] if user_info else ""
        return jsonify(user)
    return jsonify({"message": "User not found"}), 404


@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.get_json()
    client = X105Client()
    success, msg = client.add_user(
        user_id=data["user_id"],
        name=data["name"],
        privilege=int(data.get("privilege", 0)),
        card=int(data.get("card", 0) or 0),
        password=int(data.get("mverifypass", 0) or 0),
        group_id=data.get("defaultdeptid", ""),
    )
    if success:
        # Also update the local userinfo table
        update_userinfo_in_db(
            data["user_id"],
            data.get("mverifypass"),
            data.get("defaultdeptid"),
            data.get("privilege"),
        )
        return jsonify({"message": msg}), 201
    return jsonify({"message": msg}), 400


@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    client = X105Client()
    success, msg = client.update_user(
        user_id=user_id,
        name=data.get("name"),
        privilege=int(data.get("privilege", 0)),
        card=int(data.get("card", 0) or 0),
        password=int(data.get("mverifypass", 0) or 0),
        group_id=data.get("defaultdeptid"),
    )
    if success:
        # Also update the local userinfo table
        update_userinfo_in_db(
            user_id,
            data.get("mverifypass"),
            data.get("defaultdeptid"),
            data.get("privilege"),
        )
        return jsonify({"message": msg})
    return jsonify({"message": msg}), 400


def update_userinfo_in_db(user_id, mverifypass, defaultdeptid, privilege=None):
    """Update userinfo in the local database."""

    if mverifypass is None and defaultdeptid is None and privilege is None:
        return

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    # Create userinfo table if it doesn't exist

    cur.execute("""


    CREATE TABLE IF NOT EXISTS userinfo (


        badgenumber TEXT PRIMARY KEY,


        name TEXT,


        defaultdeptid INTEGER,


        mverifypass TEXT,


        privilege INTEGER


    )


    """)

    # Check if user exists

    cur.execute("SELECT badgenumber FROM userinfo WHERE badgenumber = ?", (user_id,))

    existing_user = cur.fetchone()

    if existing_user:
        if mverifypass is not None:
            cur.execute(
                "UPDATE userinfo SET mverifypass = ? WHERE badgenumber = ?",
                (mverifypass, user_id),
            )

        if defaultdeptid is not None:
            cur.execute(
                "UPDATE userinfo SET defaultdeptid = ? WHERE badgenumber = ?",
                (defaultdeptid, user_id),
            )

        if privilege is not None:
            cur.execute(
                "UPDATE userinfo SET privilege = ? WHERE badgenumber = ?",
                (privilege, user_id),
            )

    else:
        # Insert new user with the provided details

        cur.execute(
            "INSERT INTO userinfo (badgenumber, mverifypass, defaultdeptid, privilege) VALUES (?, ?, ?, ?)",
            (user_id, mverifypass, defaultdeptid, privilege),
        )

    conn.commit()
    conn.close()


@app.route("/api/departments", methods=["GET"])
def get_departments():
    departments = query_db("SELECT deptid, deptname FROM departments")
    return jsonify([dict(row) for row in departments])


@app.route("/api/machines", methods=["GET"])
def get_machines():
    """Get all machines from the database."""

    try:
        machines = query_db("SELECT * FROM machines ORDER BY name")

        return jsonify([dict(row) for row in machines])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/machines", methods=["POST"])
def add_machine():
    """Add a new machine to the database."""
    data = request.get_json()
    name = data.get("name")
    ip_address = data.get("ip_address")
    port = data.get("port")
    location = data.get("location")
    sync_schedule = data.get("sync_schedule")

    if not all([name, ip_address, port]):
        return jsonify(
            {"message": "Missing required fields: name, ip_address, port"}
        ), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO machines (name, ip_address, port, location, sync_schedule) VALUES (?, ?, ?, ?, ?)",
            (name, ip_address, port, location, sync_schedule),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Machine added successfully"}), 201
    except sqlite3.IntegrityError:
        # This happens if the IP address is not unique
        return jsonify(
            {"message": f"Error: Machine with IP address {ip_address} already exists."}
        ), 409
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/machines/<int:machine_id>", methods=["GET"])
def get_machine(machine_id):
    """Get a single machine by its ID."""
    try:
        machine = query_db(
            "SELECT * FROM machines WHERE id = ?", [machine_id], one=True
        )
        if machine:
            # Simply return the data from the database.
            # The frontend will display existing firmware/sn if available.
            # Connecting to the device here is not necessary for editing.
            return jsonify(dict(machine))
        else:
            return jsonify({"message": "Machine not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/machines/<int:machine_id>", methods=["PUT"])
def update_machine(machine_id):
    """Update an existing machine."""
    data = request.get_json()
    name = data.get("name")
    ip_address = data.get("ip_address")
    port = data.get("port")
    location = data.get("location")
    sync_schedule = data.get("sync_schedule")

    if not all([name, ip_address, port]):
        return jsonify(
            {"message": "Missing required fields: name, ip_address, port"}
        ), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE machines SET name = ?, ip_address = ?, port = ?, location = ?, sync_schedule = ? WHERE id = ?",
            (name, ip_address, port, location, sync_schedule, machine_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Machine not found"}), 404

        conn.close()

        # After successfully updating the DB, reschedule the jobs
        try:
            # We need the 'sn' which might not be in the request data, so we fetch the full machine record
            updated_machine_data = query_db("SELECT id, name, ip_address, port, sn, sync_schedule FROM machines WHERE id = ?", [machine_id], one=True)
            if updated_machine_data:
                reschedule_jobs_for_machine(app.scheduler, updated_machine_data)
        except Exception as e:
            logger = logging.getLogger("scheduler")
            logger.error(f"Failed to trigger rescheduling for machine ID {machine_id}: {e}")

        return jsonify({"message": "Machine updated successfully"})
    except sqlite3.IntegrityError:
        return jsonify(
            {
                "message": f"Error: IP address {ip_address} may already be in use by another machine."
            }
        ), 409
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/machines/delete/<int:machine_id>", methods=["DELETE"])
def delete_machine(machine_id):
    """Delete a machine from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Machine not found"}), 404

        conn.close()
        return jsonify({"message": "Machine deleted successfully"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/machines/download-range/<int:machine_id>", methods=["POST"])
def download_records_for_range(machine_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"message": "Start and end dates are required."}), 400

    machine = query_db("SELECT * FROM machines WHERE id = ?", [machine_id], one=True)
    if not machine:
        return jsonify({"message": "Machine not found"}), 404

    key = f"machine_{machine_id}"

    if not is_machine_reachable(machine["ip_address"], machine["port"]):
        return jsonify({"message": f"❌ Mesin {machine['ip_address']} tidak dapat dijangkau."}), 503

    ok, msg = SafeJobRunner.start(
        key=key,
        target=x105_download_data.main,
        kwargs=dict(ip=machine["ip_address"], port=machine["port"], sn=machine["sn"],
                    mode="range", start=start_date, end=end_date),
        timeout=90,
    )
    if not ok:
        return jsonify({"message": f"⚠️ {msg}"}), 429

    return jsonify({
        "message": "Download dimulai di background. Cek status dengan tombol Refresh.",
        "status": "started"
    }), 202


@app.route("/api/machines/download-status/<int:machine_id>", methods=["GET"])
def get_download_status(machine_id):
    """Endpoint untuk cek status download (polling dari frontend)"""
    result = SafeJobRunner.poll(f"machine_{machine_id}")

    # Setelah selesai, update db_record_count di DB
    if result.get("status") == "done":
        machine = query_db("SELECT sn FROM machines WHERE id = ?", [machine_id], one=True)
        if machine and machine["sn"]:
            x105_download_data.update_db_record_count(machine["sn"])

    return jsonify(result)

def generate_daily_attendance_report(start_date, end_date, department):
    """Generate a daily attendance report for a specific date range and department."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = f"""
        SELECT c.userid, c.checktime, u.name, d.deptname
        FROM checkinout c
        LEFT JOIN userinfo u ON c.userid = u.badgenumber
        LEFT JOIN departments d ON u.defaultdeptid = d.deptid
        WHERE date(c.checktime) BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if department:
        print(f"DEBUG: generate_daily_attendance_report - Filtering by department: '{department}'")
        query += " AND d.deptname = ?"
        params.append(department)

    cursor.execute(query, tuple(params))
    logs = cursor.fetchall()
    conn.close()
    
    report_data = []
    for row in logs:
        report_data.append(dict(row))

    return report_data


def generate_monthly_summary_report(start_date, end_date, department):
    """Generate a monthly summary report for a specific date range and department."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = f"""
        SELECT strftime('%Y-%m', c.checktime) AS month,
               c.userid,
               u.name,
               d.deptname,
               COUNT(DISTINCT date(c.checktime)) AS days_present
        FROM checkinout c
        LEFT JOIN userinfo u ON c.userid = u.badgenumber
        LEFT JOIN departments d ON u.defaultdeptid = d.deptid
        WHERE strftime('%Y-%m-%d', c.checktime) BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if department:
        print(f"DEBUG: generate_monthly_summary_report - Filtering by department: '{department}'")
        query += " AND d.deptname = ?"
        params.append(department)

    query += " GROUP BY 1, 2, 3, 4"

    cursor.execute(query, tuple(params))
    logs = cursor.fetchall()
    conn.close()

    report_data = []
    for row in logs:
        report_data.append(dict(row))

    return report_data


def generate_absent_report(start_date, end_date, department):
    """Generate an absent report for a specific date range and department."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = f"""
        SELECT u.badgenumber, u.name, d.deptname
        FROM userinfo u
        LEFT JOIN departments d ON u.defaultdeptid = d.deptid
        WHERE u.badgenumber NOT IN (
            SELECT c.userid
            FROM checkinout c
            WHERE date(c.checktime) BETWEEN ? AND ?
        )
    """
    params = [start_date, end_date]

    if department:
        print(f"DEBUG: generate_absent_report - Filtering by department: '{department}'")
        query += " AND d.deptname = ?"
        params.append(department)

    cursor.execute(query, tuple(params))
    logs = cursor.fetchall()
    conn.close()

    report_data = []
    for row in logs:
        report_data.append(dict(row))

    return report_data


def generate_department_report(start_date, end_date, department):
    """Generate a department report for a specific date range."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = f"""
        SELECT
            d.deptname,
            COUNT(DISTINCT u.badgenumber) AS total_employees,
            COUNT(DISTINCT CASE WHEN c.checktime BETWEEN ? AND ? THEN c.userid ELSE NULL END) AS present_employees,
            (COUNT(DISTINCT u.badgenumber) - COUNT(DISTINCT CASE WHEN c.checktime BETWEEN ? AND ? THEN c.userid ELSE NULL END)) AS absent_employees
        FROM userinfo u
        JOIN departments d ON u.defaultdeptid = d.deptid
        LEFT JOIN checkinout c ON u.badgenumber = c.userid AND date(c.checktime) BETWEEN ? AND ?
    """
    params = [start_date, end_date, start_date, end_date, start_date, end_date]

    if department:
        print(f"DEBUG: generate_department_report - Filtering by department: '{department}'")
        query += " WHERE d.deptname = ?"
        params.append(department)

    cursor.execute(query, tuple(params))
    query += " GROUP BY d.deptname"
    cursor.execute(query, tuple(params))
    logs = cursor.fetchall()
    conn.close()

    report_data = []
    for row in logs:
        report_data.append(dict(row))

    return report_data


@app.route('/api/generate_report')
def generate_report():
    report_type = request.args.get('report_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department = request.args.get('department')
    output_format = request.args.get('format', 'pdf') # default to pdf

    if not all([report_type, start_date, end_date]):
        return jsonify({"error": "Missing required parameters"}), 400

    data = []
    headers = []

    if report_type == 'Daily Attendance':
        data = generate_daily_attendance_report(start_date, end_date, department)
        if data:
            headers = list(data[0].keys())
    elif report_type == 'Monthly Summary':
        data = generate_monthly_summary_report(start_date, end_date, department)
        if data:
            headers = list(data[0].keys())
    elif report_type == 'Absent Report':
        data = generate_absent_report(start_date, end_date, department)
        if data:
            headers = list(data[0].keys())
    elif report_type == 'Department Report':
        data = generate_department_report(start_date, end_date, department)
        if data:
            headers = list(data[0].keys())
    # Add other report types here
    else:
        return jsonify({"error": "Invalid report type"}), 400

    if output_format == 'json':
        return jsonify(data)

    # --- PDF Generation ---
    if not data:
        # Handle case where there is no data to generate a report
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.drawString(100, 750, f"No data found for the selected criteria.")
        p.drawString(100, 730, f"Report Type: {report_type}")
        p.drawString(100, 710, f"Period: {start_date} to {end_date}")
        p.drawString(100, 690, f"Department: {department or 'All'}")
        p.showPage()
        p.save()
        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=report.pdf'
        return response

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Convert list of dicts to list of lists for the table
    table_data = [headers] + [[str(row.get(header, '')) for header in headers] for row in data]

    # Create table
    t = Table(table_data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    t.setStyle(style)
    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=report.pdf'
    return response



@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    client = X105Client()
    success, msg = client.delete_user(user_id)
    if success:
        return jsonify({"message": msg})
    return jsonify({"message": msg}), 400


@app.route("/api/machine/status/<ip>", methods=["GET"])
def get_machine_status(ip):
    """Test the connection to a machine and return its status."""
    # Using a shorter timeout for quick status checks
    client = X105Client(ip=ip, timeout=15)
    is_online, message = client.test_connection()

    if is_online:
        return jsonify({"status": "Online"})
    else:
        return jsonify({"status": "Offline"})


@app.route("/api/dashboard-data")
def api_dashboard_data():
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not start_date or not end_date:
        today = datetime.today().date()
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    print("DEBUG start:", start_date, "end:", end_date)

    logs = query_db(
        """
        SELECT c.userid, c.checktime, c.verifycode, c.workcode, c.sn,
               u.badgenumber, u.name, u.defaultdeptid, d.deptname
        FROM checkinout c
        LEFT JOIN userinfo u ON c.userid = u.badgenumber
        LEFT JOIN departments d ON u.defaultdeptid = d.deptid
        WHERE date(c.checktime) BETWEEN ? AND ?
        ORDER BY c.checktime ASC
    """,
        (start_date, end_date),
    )

    total_users = query_db("SELECT COUNT(*) as cnt FROM userinfo", one=True)["cnt"]

    # group log per user untuk deteksi check-in pertama
    user_first_checkin = {}
    for row in logs:
        uid = row["userid"]
        if uid not in user_first_checkin:
            user_first_checkin[uid] = datetime.fromisoformat(row["checktime"])

    # hitung keterlambatan
    late_threshold = 10  # jam 10:00
    late_users = [
        uid for uid, t in user_first_checkin.items() if t.hour >= late_threshold
    ]

    # stats
    attendance_count = len(user_first_checkin)
    stats = {
        "total_employees": total_users,
        "present_today": attendance_count,
        "absent_today": total_users - attendance_count,
        "late_today": len(late_users),
    }

    # analytics
    avg_attendance = round(attendance_count / max(total_users, 1) * 100, 2)
    peak_time = "-"
    if logs:
        hours = [datetime.fromisoformat(row["checktime"]).hour for row in logs]
        peak_time = max(set(hours), key=hours.count)

    analytics = {
        "avg_attendance_rate": avg_attendance,
        "peak_time": f"{peak_time}:00" if peak_time != "-" else "-",
        "active_days": len(set([row["checktime"][:10] for row in logs])),
        "late_rate": round(len(late_users) / max(attendance_count, 1) * 100, 2),
    }

    # trend per hari
    trend = {}
    for row in logs:
        day = row["checktime"][:10]
        if day not in trend:
            trend[day] = {"present": 0, "absent": 0, "late": 0}
        trend[day]["present"] += 1
    # masukkan late
    for uid, t in user_first_checkin.items():
        day = t.strftime("%Y-%m-%d")
        if t.hour >= late_threshold:
            trend[day]["late"] += 1

    attendance_trend = {
        "labels": list(trend.keys()),
        "present": [v["present"] for v in trend.values()],
        "absent": [v["absent"] for v in trend.values()],
        "late": [v["late"] for v in trend.values()],
    }

    # breakdown per dept
    dept_stats = {}
    for uid in user_first_checkin.keys():
        row = next((r for r in logs if r["userid"] == uid), None)
        dept = row["deptname"] if row else "Unknown"
        dept_stats[dept] = dept_stats.get(dept, 0) + 1

    department_breakdown = {
        "labels": list(dept_stats.keys()),
        "data": list(dept_stats.values()),
    }

    recent_activities = []
    # Return all logs for the period, sorted by time descending
    for row in sorted(logs, key=lambda r: r["checktime"], reverse=True):
        user = row["name"] or f"User {row['userid']}"
        time_str = row["checktime"]
        check_dt = datetime.fromisoformat(time_str)

        is_late = False
        if (
            row["userid"] in late_users
            and check_dt == user_first_checkin[row["userid"]]
        ):
            is_late = True

        recent_activities.append(
            {"user": user, "time": time_str, "status": "Hadir", "is_late": is_late}
        )

    print(
        f"✅ Masuk ke /api/dashboard-data {start_date} s/d {end_date}, total: {len(logs)}"
    )
    return jsonify(
        {
            "stats": stats,
            "attendance_trend": attendance_trend,
            "department_breakdown": department_breakdown,
            "recent_activities": recent_activities,
            "analytics": analytics,
        }
    )



if __name__ == "__main__":
    app.run(debug=True, port=5020)


@app.route("/api/machines/refresh-stats/<int:machine_id>", methods=["POST"])
def refresh_machine_stats(machine_id):
    """Sync machine data to the database."""
    key = f"machine_{machine_id}"

    # Cegah refresh stats bersamaan dengan download yang sedang berjalan
    existing = SafeJobRunner.poll(key)
    if existing.get("status") == "running":
        return jsonify({"status": "Busy", "message": "⚠️ Mesin sedang sibuk download, coba lagi nanti."}), 429

    try:
        machine = query_db("SELECT * FROM machines WHERE id = ?", [machine_id], one=True)
        if not machine:
            return jsonify({"message": "Machine not found"}), 404

        if not is_machine_reachable(machine["ip_address"], machine["port"], timeout=5):
            return jsonify({"status": "Offline", "message": "Mesin tidak dapat dijangkau"})

        client = X105Client(ip=machine["ip_address"], port=machine["port"], timeout=30)
        firmware, sn, user_count, fingers, cards, record_count, rec_cap, rec_av = client.get_all_info()

        if firmware and sn:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE machines SET firmware=?, sn=?, user_count=?, fingers=?, cards=?, record_count=?, rec_cap=?, rec_av=? WHERE id=?",
                    (firmware, sn, user_count, fingers, cards, record_count, rec_cap, rec_av, machine_id),
                )
                conn.commit()
                conn.close()

                updated_machine = query_db("SELECT * FROM machines WHERE id = ?", [machine_id], one=True)
                return jsonify(dict(updated_machine))
            except Exception as e:
                print(f"DATABASE ERROR: {e}")
                return jsonify({"status": "Error", "message": "Database error"}), 500
        else:
            return jsonify({"status": "Offline", "message": "Failed to connect to device"})

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500
