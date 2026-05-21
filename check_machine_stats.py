import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from core_files.x105_machine import X105Client
from core_files import config


def get_machine_stats(ip, port, password):
    client = X105Client(ip=ip, port=port, password=password, timeout=config.DEFAULT_TIMEOUT)

    print("Fetching data dari mesin...")
    firmware, sn, user_count, fingers, cards, record_count, rec_cap, rec_av = client.get_all_info()

    if firmware is None:
        print(f"Error: Gagal konek ke {ip}:{port}.")
        return

    print(f"Successfully connected to {ip}:{port}.")
    print(f"Firmware    : {firmware}")
    print(f"Serial No   : {sn}")
    print(f"Fingers     : {fingers}")
    print(f"Cards       : {cards}")
    print(f"Total Users : {user_count}")
    print(f"Total Records (di mesin): {record_count}")
    print(f"Records Capacity: {rec_cap} (kapasitas maksimum)")
    print(f"Records Available: {rec_av} (tersedia)")


if __name__ == "__main__":
    config.ensure_paths()
    ip, port, password = config.get_device_params()
    print(f"Connecting to machine at {ip}:{port}...")
    get_machine_stats(ip, port, password)