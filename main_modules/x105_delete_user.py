# main_modules/x105_hapus_user.py
import sys
import os
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files.x105_machine import X105Client


def get_client():
    return X105Client()


def main():
    # Setup argparse
    parser = argparse.ArgumentParser(description="Hapus user dari mesin fingerprint")
    parser.add_argument("user_id", type=str, help="ID user yang akan dihapus")
    parser.add_argument("--confirm", action="store_true", help="Skip konfirmasi")

    args = parser.parse_args()

    client = get_client()

    print(f"\n{'=' * 60}")
    print(f"Menghapus user ID: {args.user_id}")
    print(f"{'=' * 60}\n")

    # Konfirmasi sebelum hapus (kecuali pakai flag --confirm)
    if not args.confirm:
        confirm = input(
            f"Apakah Anda yakin ingin menghapus user ID {args.user_id}? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("❌ Operasi dibatalkan")
            return

    # Hapus user
    success, msg = client.delete_user(user_id=args.user_id)

    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")

    # Tampilkan list users setelah hapus
    print(f"\n{'=' * 60}")
    print(f"Daftar user setelah penghapusan:")
    print(f"{'=' * 60}\n")

    users, msg = client.get_users()
    if users:
        print(f"Total users: {len(users)}\n")
        print(f"{'ID':<10} {'Name':<30}")
        print(f"{'-' * 40}")
        for user in users:
            print(f"{user['user_id']:<10} {user['name']:<30}")
    else:
        print(f"✗ {msg}")


if __name__ == "__main__":
    main()
