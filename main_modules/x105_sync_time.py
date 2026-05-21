# main_modules/x105_sync_time.py
import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files.x105_machine import X105Client


def get_client():
    return X105Client()


def main():
    parser = argparse.ArgumentParser(description="Sinkronkan waktu mesin fingerprint")
    parser.add_argument(
        "--time",
        type=str,
        help="Waktu manual format 'YYYY-MM-DD HH:MM:SS' (default=sekarang)",
    )
    parser.add_argument("--confirm", action="store_true", help="Skip konfirmasi")
    args = parser.parse_args()

    client = get_client()

    if args.time:
        try:
            new_time = datetime.strptime(args.time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("❌ Format waktu salah. Gunakan format: YYYY-MM-DD HH:MM:SS")
            return
    else:
        new_time = datetime.now()

    print(f"\n{'=' * 60}")
    print("SYNC TIME MESIN")
    print(f"{'=' * 60}\n")
    print(f"Waktu tujuan: {new_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Konfirmasi
    if not args.confirm:
        confirm = input("Apakah Anda yakin ingin sync time mesin? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Operasi dibatalkan")
            return

    success, msg = client.sync_time(new_time=new_time)
    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")


if __name__ == "__main__":
    main()
