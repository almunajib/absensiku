# main_modules/x105_clear_data.py
import sys
import os
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files.x105_machine import X105Client


def get_client():
    return X105Client()


def main():
    parser = argparse.ArgumentParser(
        description="Hapus semua attendance logs di mesin fingerprint"
    )
    parser.add_argument("--confirm", action="store_true", help="Skip konfirmasi")
    args = parser.parse_args()

    client = get_client()

    print(f"\n{'=' * 60}")
    print("CLEAR ATTENDANCE LOGS")
    print(f"{'=' * 60}\n")

    # Konfirmasi sebelum hapus (kecuali pakai --confirm)
    if not args.confirm:
        confirm = input(
            "Apakah Anda yakin ingin menghapus SEMUA attendance logs? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("❌ Operasi dibatalkan")
            return

    print("Menghapus logs...")
    success, msg = client.clear_attendance()

    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
        return

    # Setelah hapus, coba ambil logs lagi
    logs, msg = client.get_attendance_logs()
    if logs:
        print(f"⚠️ Masih ada {len(logs)} log tersisa")
    else:
        print("✓ Attendance logs sekarang kosong")


if __name__ == "__main__":
    main()
