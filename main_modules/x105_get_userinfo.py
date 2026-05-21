#!/usr/bin/env python3
import argparse
from zk import ZK


def map_privilege(raw):
    if raw in (0, 0x00):
        return "0"  # User
    elif raw in (1, 0x01):
        return "1"  # Enroller
    elif raw in (2, 0x02, 3):
        return "2"  # Admin
    elif raw in (14, 0x0E, 15):
        return "3"  # SuperAdmin
    else:
        return f"Unknown ({raw})"


def print_user(u):
    print(f"UID: {u.uid}")
    print(f"UserID: {u.user_id}")
    print(f"Name: {u.name}")
    print(f"Password: {getattr(u, 'password', None)}")
    print(f"Privilege: {map_privilege(u.privilege)}")
    print(f"Group ID: {getattr(u, 'group_id', None)}")
    print("-" * 30)


def main():
    parser = argparse.ArgumentParser(description="Get users from ZK device")
    parser.add_argument("--host", default="192.168.1.33", help="IP mesin")
    parser.add_argument("--port", type=int, default=4370, help="Port")
    parser.add_argument(
        "--user_id", help="Jika diisi, hanya tampilkan user dengan user_id ini"
    )
    args = parser.parse_args()

    zk = ZK(args.host, port=args.port, timeout=10)
    conn = None
    try:
        conn = zk.connect()
        users = conn.get_users()
        if args.user_id:
            found = False
            for u in users:
                if str(u.user_id) == str(args.user_id) or str(u.uid) == str(
                    args.user_id
                ):
                    print_user(u)
                    found = True
                    break
            if not found:
                print(f"User dengan id {args.user_id} tidak ditemukan.")
        else:
            for u in users:
                print_user(u)
    finally:
        if conn:
            conn.disconnect()


if __name__ == "__main__":
    main()
