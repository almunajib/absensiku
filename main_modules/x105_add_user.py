# main_modules/x105_add_user.py
import sys
import os
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files import config


def main():
    # Setup argparse
    parser = argparse.ArgumentParser(
        description="Tambah user baru ke mesin fingerprint"
    )
    parser.add_argument("user_id", type=str, help="ID user yang akan ditambahkan")
    parser.add_argument("name", type=str, help="Nama user")
    parser.add_argument(
        "--privilege",
        type=int,
        choices=[0, 14],
        default=0,
        help="Privilege: 0=User biasa (default), 14=Admin",
    )
    parser.add_argument(
        "--password", type=str, default="", help="Password user (optional)"
    )
    parser.add_argument("--confirm", action="store_true", help="Skip konfirmasi")

    args = parser.parse_args()

    client = config.get_client()

    print(f"\n{'=' * 60}")
    print(f"Menambah user ID: {args.user_id} - {args.name}")
    print(f"{'=' * 60}\n")

    # PENTING: Panggil get_users() dulu untuk "warm up" mesin
    print("Mengambil daftar user saat ini...")
    users_before, msg = client.get_users()
    if users_before:
        print(f"✓ {msg}")
    else:
        print(f"⚠️  Warning: {msg}")

    # Konfirmasi sebelum tambah (kecuali pakai flag --confirm)
    if not args.confirm:
        priv_text = "Admin" if args.privilege == 14 else "User"
        confirm = input(
            f"\nApakah Anda yakin ingin menambah user '{args.name}' (ID: {args.user_id}, Privilege: {priv_text})? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("❌ Operasi dibatalkan")
            return

    # Tambah user
    print(f"\nMenambahkan user...")
    success, msg = client.add_user(
        user_id=args.user_id,
        name=args.name,
        privilege=args.privilege,
        password=args.password,
    )

    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
        return

    # Tampilkan list users setelah tambah
    print(f"\n{'=' * 60}")
    print(f"Daftar user setelah penambahan:")
    print(f"{'=' * 60}\n")

    users, msg = client.get_users()
    if users:
        print(f"Total users: {len(users)}\n")
        print(f"{'ID':<10} {'Name':<30} {'Privilege':<10}")
        print(f"{'-' * 55}")
        for user in users:
            priv_text = "Admin" if user["privilege"] == 14 else "User"
            marker = " ← BARU" if user["user_id"] == args.user_id else ""
            print(f"{user['user_id']:<10} {user['name']:<30} {priv_text:<10}{marker}")
    else:
        print(f"✗ {msg}")


if __name__ == "__main__":
    main()
