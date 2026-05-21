# main_modules/x105_update_user_flexible.py
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files.x105_machine import X105Client


def get_client():
    return X105Client()


def main():
    parser = argparse.ArgumentParser(
        description="Update user berdasarkan UID atau User ID"
    )

    # Group untuk memilih UID atau User ID (mutually exclusive)
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--uid", type=int, help="UID yang akan diupdate")
    id_group.add_argument(
        "--user-id", type=str, dest="user_id", help="User ID yang akan diupdate"
    )

    # Parameter update
    parser.add_argument("--name", type=str, help="Nama baru user")
    parser.add_argument(
        "--privilege",
        type=int,
        choices=[0, 14],
        help="Privilege: 0=User biasa, 14=Admin",
    )
    parser.add_argument("--password", type=str, help="Password baru user")
    parser.add_argument(
        "--group", "--group-id", type=str, dest="group_id", help="Group ID baru"
    )
    parser.add_argument("--card", type=int, help="Card number baru")
    parser.add_argument("--confirm", action="store_true", help="Skip konfirmasi")

    args = parser.parse_args()

    client = get_client()

    # Validasi: minimal satu parameter update harus diisi
    if not any(
        [
            args.name,
            args.privilege is not None,
            args.password is not None,
            args.group_id,
            args.card is not None,
        ]
    ):
        print("❌ Error: Minimal satu parameter update harus diisi")
        print("   Gunakan --name, --privilege, --password, --group, atau --card")
        return

    print(f"\n{'=' * 60}")
    if args.uid:
        print(f"Update user berdasarkan UID: {args.uid}")
    else:
        print(f"Update user berdasarkan User ID: {args.user_id}")
    print(f"{'=' * 60}\n")

    # Ambil daftar user
    print("Mengambil daftar user saat ini...")
    users, msg = client.get_users()
    if not users:
        print(f"❌ {msg}")
        return

    print(f"✓ {msg}\n")

    # Cari user berdasarkan UID atau User ID
    target_user = None

    if args.uid:
        # Cari berdasarkan UID
        for user in users:
            if user["uid"] == args.uid:
                target_user = user
                break

        if not target_user:
            print(f"❌ User dengan UID {args.uid} tidak ditemukan")
            return
    else:
        # Cari berdasarkan User ID
        for user in users:
            if user["user_id"] == args.user_id:
                target_user = user
                break

        if not target_user:
            print(f"❌ User dengan User ID '{args.user_id}' tidak ditemukan")
            return

    # Tampilkan info user yang akan diupdate
    print("User yang ditemukan:")
    print(f"  UID       : {target_user['uid']}")
    print(f"  User ID   : {target_user['user_id']}")
    print(f"  Name      : {target_user['name']}")
    print(f"  Privilege : {'Admin' if target_user['privilege'] == 14 else 'User'}")
    print(f"  Group ID  : {target_user['group_id']}")
    print(f"  Password  : {target_user['password']}")
    print(f"  Card      : {target_user['card']}")

    # Konfirmasi sebelum update (kecuali pakai flag --confirm)
    if not args.confirm:
        print("\nData yang akan diupdate:")
        if args.name:
            print(f"  Nama      : {args.name}")
        if args.privilege is not None:
            priv_text = "Admin" if args.privilege == 14 else "User"
            print(f"  Privilege : {priv_text}")
        if args.password is not None:
            print(f"  Password  : (akan diubah)")
        if args.group_id:
            print(f"  Group ID  : {args.group_id}")
        if args.card is not None:
            print(f"  Card      : {args.card}")

        confirm = input(f"\nApakah Anda yakin ingin update user ini? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Operasi dibatalkan")
            return

    # Update user
    success, msg = client.update_user(
        user_id=target_user["user_id"],
        name=args.name,
        privilege=args.privilege,
        password=args.password,
        group_id=args.group_id,
        card=args.card,
    )

    if success:
        print(f"\n✓ {msg}")
    else:
        print(f"\n❌ {msg}")
        return

    # Tampilkan list users setelah update
    print(f"\n{'=' * 60}")
    print(f"Daftar user setelah update:")
    print(f"{'=' * 60}\n")

    users, msg = client.get_users()
    if users:
        print(f"Total users: {len(users)}\n")
        print(f"{'UID':<6} {'User ID':<15} {'Name':<30} {'Privilege':<10}")
        print(f"{'-' * 65}")
        for user in users:
            priv_text = "Admin" if user["privilege"] == 14 else "User"
            marker = " ← UPDATED" if user["user_id"] == target_user["user_id"] else ""
            print(
                f"{user['uid']:<6} {user['user_id']:<15} {user['name']:<30} {priv_text:<10}{marker}"
            )
    else:
        print(f"❌ {msg}")


if __name__ == "__main__":
    main()
