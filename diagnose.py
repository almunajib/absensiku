"""
Verifikasi: read_sizes() mengisi conn.records tanpa hang
"""
import sys, os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
from core_files import config
from zk import ZK

ip   = config.DEFAULT_IP
port = config.DEFAULT_PORT

print(f"Connecting to {ip}:{port}...")
zk = ZK(ip, port=port, timeout=10, password='', force_udp=False, ommit_ping=False)
conn = zk.connect()
print("✓ Connected")

conn.read_sizes()
print(f"✓ users   = {conn.users}")
print(f"✓ records = {conn.records}")
print(f"✓ fingers = {conn.fingers}")
print(f"✓ cards   = {conn.cards}")
print(f"✓ rec_cap = {conn.rec_cap} (kapasitas maksimum)")
print(f"✓ rec_av  = {conn.rec_av} (slot tersisa)")

conn.disconnect()
print("Done - tidak hang!")