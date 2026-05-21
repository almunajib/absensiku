"""
x105_get_biometric.py
Modul untuk mengambil data template biometrik (fingerprint) dari mesin X105
dan menyimpannya ke database untuk backup/transfer ke mesin lain

Data diambil dari tabel TEMPLATE di mesin dengan field:
- USERID: User ID
- FINGERID: Index jari (0-9)
- TEMPLATE4: Data biometrik utama (BLOB)
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dari core_files
from core_files.x105_machine import X105Client

SQLITE_FILENAME = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "db_files", "x105.db"
)

MACHINE_LIST = [{"ip": "192.168.1.33", "port": 4370, "name": "Main Device"}]


def get_client():
    return X105Client()


def init_biometric_db():
    conn = sqlite3.connect(SQLITE_FILENAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TEMPLATE (
            TEMPLATEID INTEGER PRIMARY KEY AUTOINCREMENT,
            USERID TEXT NOT NULL,
            FINGERID INTEGER NOT NULL,
            TEMPLATE BLOB,
            TEMPLATE1 BLOB,
            TEMPLATE2 BLOB,
            TEMPLATE3 BLOB,
            TEMPLATE4 BLOB,
            USETYPE INTEGER DEFAULT 0,
            Flag INTEGER DEFAULT 1,
            DivisionFP INTEGER DEFAULT 10,
            machine_ip TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(machine_ip, USERID, FINGERID)
        )
    """)

    conn.commit()
    conn.close()
    print("✓ Tabel TEMPLATE siap")


def get_biometric_from_machine(
    machine_ip=None, machine_port=None, machine_password=None
):
    """
    Mengambil semua template biometrik dari tabel TEMPLATE di mesin
    Data template bisa ada di field: TEMPLATE, TEMPLATE1, TEMPLATE2, TEMPLATE3, TEMPLATE4

    Args:
        machine_ip: IP address mesin
        machine_port: Port mesin (default 4370)
        machine_password: Password mesin (default "")

    Returns:
        list: List of dict containing USERID, FINGERID, dan template data
    """
    templates = []

    try:
        # Jika parameter tidak lengkap, gunakan get_client dari config
        if machine_ip is None:
            client = get_client()  # Pakai default dari config
            machine_ip = client.ip
            machine_port = client.port
        else:
            # Buat client dengan parameter custom
            from core_files.x105_machine import X105Client

            client = X105Client(
                ip=machine_ip,
                port=machine_port or 4370,
                password=machine_password or "",
            )

        print(f"\n{'=' * 60}")
        print(f"Mengambil template dari: {machine_ip}:{machine_port}")
        print(f"{'=' * 60}")

        # Connect menggunakan client
        ok, msg = client.connect()
        if not ok:
            print(f"✗ Koneksi gagal: {msg}")
            return templates

        print(f"✓ Koneksi berhasil")

        # Disable device untuk mempercepat proses
        client.conn.disable_device()
        print("✓ Device di-disable")

        # Ambil semua user terlebih dahulu
        users = client.conn.get_users()
        total_users = len(users)
        print(f"✓ Total users di mesin: {total_users}")

        if total_users == 0:
            print("⚠ Tidak ada user di mesin")
            client.conn.enable_device()
            client.disconnect()
            return templates

        # Ambil template untuk setiap user
        print(f"\n{'=' * 60}")
        print("Mengambil template dari tabel TEMPLATE...")
        print(f"{'=' * 60}\n")

        template_count = 0

        for idx, user in enumerate(users, 1):
            user_id = user.user_id
            user_name = user.name
            print(f"[{idx}/{total_users}] User: {user_id} ({user_name})")

            # Cek setiap FINGERID (0-9)
            for finger_id in range(10):
                try:
                    # Pastikan user_id adalah integer
                    uid = int(user_id) if not isinstance(user_id, int) else user_id

                    # Ambil template untuk FINGERID tertentu
                    template_obj = client.conn.get_user_template(uid, finger_id)

                    # Debug: tampilkan info template_obj
                    if template_obj:
                        print(
                            f"  [DEBUG] FINGERID {finger_id}: template_obj = {type(template_obj)}"
                        )
                        if hasattr(template_obj, "template"):
                            template_data = template_obj.template
                            print(
                                f"  [DEBUG] template data: type={type(template_data)}, len={len(template_data) if template_data else 0}"
                            )

                            if template_data:
                                # Tampilkan 20 bytes pertama untuk debugging
                                preview = (
                                    template_data[:20]
                                    if len(template_data) >= 20
                                    else template_data
                                )
                                print(f"  [DEBUG] preview: {preview}")

                            # Skip jika template kosong atau "NONE"
                            if template_data and len(template_data) > 10:
                                if template_data == b"NONE":
                                    print(f"  [DEBUG] Skipped: template = 'NONE'")
                                else:
                                    templates.append(
                                        {
                                            "USERID": str(user_id),
                                            "FINGERID": finger_id,
                                            "machine_ip": machine_ip,
                                            "TEMPLATE4": template_data,
                                            "USETYPE": 0,
                                            "Flag": template_obj.valid
                                            if hasattr(template_obj, "valid")
                                            else 1,
                                            "DivisionFP": 10,
                                        }
                                    )
                                    template_count += 1
                                    print(
                                        f"  ✓ FINGERID {finger_id}: {len(template_data)} bytes - SAVED!"
                                    )
                            else:
                                print(f"  [DEBUG] Skipped: template too small or empty")
                        else:
                            print(f"  [DEBUG] No 'template' attribute in template_obj")

                except Exception as e:
                    # Debug: tampilkan error detail
                    print(f"  [DEBUG] FINGERID {finger_id} error: {e}")
                    continue

            if (idx % 10 == 0 or idx == total_users) and template_count > 0:
                print(f"  Progress: {template_count} templates ditemukan\n")

        # Enable device kembali
        client.conn.enable_device()
        print(f"\n{'=' * 60}")
        print(f"✓ Selesai! Total template: {template_count}")
        print(f"{'=' * 60}\n")

        client.disconnect()

    except Exception as e:
        print(f"✗ Error saat mengambil template dari {machine_ip}: {str(e)}")
        import traceback

        traceback.print_exc()

    return templates


def save_templates_to_db(templates):
    """
    Simpan template ke tabel TEMPLATE di database x105.db

    Args:
        templates: List of template dict dengan field USERID, FINGERID, TEMPLATE4, dll

    Returns:
        int: Jumlah template yang berhasil disimpan
    """
    if not templates:
        print("⚠ Tidak ada template untuk disimpan")
    conn = sqlite3.connect(SQLITE_FILENAME)
    cursor = conn.cursor()

    saved_count = 0
    updated_count = 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for template in templates:
        try:
            # Cek apakah template sudah ada
            cursor.execute(
                """
                SELECT TEMPLATEID FROM TEMPLATE
                WHERE machine_ip=? AND USERID=? AND FINGERID=?
            """,
                (template["machine_ip"], template["USERID"], template["FINGERID"]),
            )

            existing = cursor.fetchone()

            # Ambil data template (prioritas TEMPLATE4)
            template_data = template.get("TEMPLATE4") or template.get("template_data")

            if existing:
                # Update existing template
                cursor.execute(
                    """
                    UPDATE TEMPLATE
                    SET TEMPLATE4=?, USETYPE=?, Flag=?, DivisionFP=?, updated_at=?
                    WHERE machine_ip=? AND USERID=? AND FINGERID=?
                """,
                    (
                        template_data,
                        template.get("USETYPE", 0),
                        template.get("Flag", 1),
                        template.get("DivisionFP", 10),
                        now,
                        template["machine_ip"],
                        template["USERID"],
                        template["FINGERID"],
                    ),
                )
                updated_count += 1
            else:
                # Insert new template
                cursor.execute(
                    """
                    INSERT INTO TEMPLATE
                    (USERID, FINGERID, TEMPLATE4, USETYPE, Flag, DivisionFP,
                     machine_ip, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        template["USERID"],
                        template["FINGERID"],
                        template_data,
                        template.get("USETYPE", 0),
                        template.get("Flag", 1),
                        template.get("DivisionFP", 10),
                        template["machine_ip"],
                        now,
                        now,
                    ),
                )
                saved_count += 1

        except Exception as e:
            print(f"✗ Error saving template for user {template['USERID']}: {str(e)}")

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"✓ Saved to x105.db:")
    print(f"  - New templates: {saved_count}")
    print(f"  - Updated templates: {updated_count}")
    print(f"{'=' * 60}\n")

    return saved_count + updated_count


def upload_templates_to_machine(
    target_ip, target_port=4370, target_password="", source_ip=None
):
    """
    Upload template dari database x105.db ke mesin lain

    Args:
        target_ip: IP mesin tujuan
        target_port: Port mesin tujuan
        target_password: Password mesin tujuan
        source_ip: IP sumber (None = ambil semua template)

    Returns:
        int: Jumlah template yang berhasil di-upload
    """
    conn_db = sqlite3.connect(SQLITE_FILENAME)
    cursor = conn_db.cursor()

    # Ambil template dari database (prioritas TEMPLATE4)
    if source_ip:
        cursor.execute(
            """
            SELECT USERID, FINGERID, COALESCE(TEMPLATE4, TEMPLATE, TEMPLATE1) as template_data
            FROM TEMPLATE
            WHERE machine_ip=? AND COALESCE(TEMPLATE4, TEMPLATE, TEMPLATE1) IS NOT NULL
        """,
            (source_ip,),
        )
    else:
        cursor.execute("""
            SELECT USERID, FINGERID, COALESCE(TEMPLATE4, TEMPLATE, TEMPLATE1) as template_data
            FROM TEMPLATE
            WHERE COALESCE(TEMPLATE4, TEMPLATE, TEMPLATE1) IS NOT NULL
        """)

    templates = cursor.fetchall()
    conn_db.close()

    if not templates:
        print("⚠ Tidak ada template di database x105.db")
        return 0

    try:
        # Gunakan X105Client
        client = X105Client(ip=target_ip, port=target_port, password=target_password)

        print(f"\n{'=' * 60}")
        print(f"Upload template ke: {target_ip}:{target_port}")
        print(f"Total template: {len(templates)}")
        print(f"{'=' * 60}\n")

        ok, msg = client.connect()
        if not ok:
            print(f"✗ Koneksi gagal: {msg}")
            return 0

        client.conn.disable_device()

        success_count = 0

        for idx, (user_id, finger_id, template_data) in enumerate(templates, 1):
            try:
                # Skip jika data kosong atau "NONE"
                if (
                    not template_data
                    or len(template_data) <= 10
                    or template_data == b"NONE"
                ):
                    continue

                # Upload template ke mesin
                client.conn.set_user_template(
                    uid=int(user_id), temp_id=finger_id, template=template_data, valid=1
                )
                success_count += 1

                if idx % 10 == 0 or idx == len(templates):
                    print(
                        f"[{idx}/{len(templates)}] Progress: {success_count} berhasil"
                    )

            except Exception as e:
                print(f"✗ User {user_id}, Finger {finger_id}: {str(e)}")

        client.conn.enable_device()
        client.disconnect()

        print(f"\n{'=' * 60}")
        print(f"✓ Upload selesai: {success_count}/{len(templates)}")
        print(f"{'=' * 60}\n")

        return success_count

    except Exception as e:
        print(f"✗ Error upload ke {target_ip}: {str(e)}")
        import traceback

        traceback.print_exc()
        return 0


def backup_all_machines():
    """Backup template dari semua mesin di MACHINE_LIST"""
    print("\n" + "=" * 60)
    print("BACKUP BIOMETRIC TEMPLATES - ALL MACHINES")
    print("=" * 60 + "\n")

    # Inisialisasi database
    init_biometric_db()

    total_templates = 0

    for machine in MACHINE_LIST:
        ip = machine["ip"]
        port = machine.get("port", 4370)
        password = machine.get("password", "")
        name = machine.get("name", ip)

        print(f"\n📍 Processing: {name} ({ip}:{port})")

        # Ambil template dari mesin
        templates = get_biometric_from_machine(ip, port, password)

        # Simpan ke database
        if templates:
            count = save_templates_to_db(templates)
            total_templates += count

    print(f"\n{'=' * 60}")
    print(f"BACKUP SELESAI!")
    print(f"Total template tersimpan: {total_templates}")
    print(f"{'=' * 60}\n")


def view_templates_summary():
    """Tampilkan ringkasan template di database x105.db"""
    conn = sqlite3.connect(SQLITE_FILENAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT machine_ip, USERID, COUNT(*) as finger_count
        FROM TEMPLATE
        GROUP BY machine_ip, USERID
        ORDER BY machine_ip, USERID
    """)

    results = cursor.fetchall()
    conn.close()

    if not results:
        print("⚠ Tidak ada template di database x105.db")
        return

    print(f"\n{'=' * 60}")
    print("RINGKASAN TEMPLATE DI DATABASE x105.db")
    print(f"{'=' * 60}\n")

    current_ip = None
    total_templates = 0

    for ip, user_id, finger_count in results:
        if ip != current_ip:
            if current_ip is not None:
                print()
            print(f"📍 Machine: {ip}")
            current_ip = ip

        print(f"  User {user_id}: {finger_count} fingers")
        total_templates += finger_count

    print(f"\n{'=' * 60}")
    print(f"Total: {total_templates} templates")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="X105 Biometric Template Manager")
    parser.add_argument(
        "action",
        choices=["backup", "upload", "view"],
        help="Action: backup=backup dari mesin, upload=upload ke mesin, view=lihat database",
    )
    parser.add_argument("--target-ip", help="Target machine IP for upload")
    parser.add_argument(
        "--target-port", type=int, default=4370, help="Target machine port"
    )
    parser.add_argument("--target-password", default="", help="Target machine password")
    parser.add_argument("--source-ip", help="Source machine IP for upload (filter)")

    args = parser.parse_args()

    if args.action == "backup":
        backup_all_machines()

    elif args.action == "upload":
        if not args.target_ip:
            print("✗ Error: --target-ip required for upload")
            print("\nContoh:")
            print("  python x105_get_biometric.py upload --target-ip 192.168.1.201")
            print(
                "  python x105_get_biometric.py upload --target-ip 192.168.1.201 --target-port 4370"
            )
            sys.exit(1)
        upload_templates_to_machine(
            args.target_ip,
            args.target_port,
            args.target_password,
            source_ip=args.source_ip,
        )

    elif args.action == "view":
        view_templates_summary()
