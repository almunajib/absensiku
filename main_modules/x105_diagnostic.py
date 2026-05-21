#!/usr/bin/env python3
"""
Script diagnostic untuk troubleshoot koneksi X105
"""
import sys
import os
import socket
import time
from datetime import datetime

# Setup path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from zk import ZK

# Config
IP = "192.168.1.33"
PORT = 4370
TIMEOUT = 30

def test_1_socket_connectivity():
    """Test 1: Raw socket connectivity"""
    print("\n" + "="*60)
    print("TEST 1: Raw Socket Connectivity")
    print("="*60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        start = time.time()
        result = sock.connect_ex((IP, PORT))
        elapsed = time.time() - start
        sock.close()
        
        if result == 0:
            print(f"✅ Socket connection successful ({elapsed:.2f}s)")
            return True
        else:
            print(f"❌ Socket connection failed with code {result}")
            return False
    except Exception as e:
        print(f"❌ Socket error: {e}")
        return False


def test_2_zk_connection():
    """Test 2: ZK Library Connection"""
    print("\n" + "="*60)
    print("TEST 2: ZK Library Connection")
    print("="*60)
    
    try:
        print(f"Creating ZK instance (timeout={TIMEOUT})...")
        zk = ZK(IP, port=PORT, timeout=TIMEOUT, password='', force_udp=False, ommit_ping=False)
        
        print("Attempting to connect...")
        start = time.time()
        conn = zk.connect()
        elapsed = time.time() - start
        
        print(f"✅ ZK connection successful ({elapsed:.2f}s)")
        
        # Get device info
        try:
            sn = conn.get_serialnumber()
            print(f"   Serial Number: {sn}")
        except Exception as e:
            print(f"   ⚠️  Cannot get SN: {e}")
        
        try:
            firmware = conn.get_firmware_version()
            print(f"   Firmware: {firmware}")
        except Exception as e:
            print(f"   ⚠️  Cannot get firmware: {e}")
        
        try:
            platform = conn.get_platform()
            print(f"   Platform: {platform}")
        except Exception as e:
            print(f"   ⚠️  Cannot get platform: {e}")
        
        # Disconnect
        print("Disconnecting...")
        conn.disconnect()
        print("✅ Disconnected successfully")
        return True
        
    except Exception as e:
        print(f"❌ ZK connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_get_attendance():
    """Test 3: Get Attendance Data"""
    print("\n" + "="*60)
    print("TEST 3: Get Attendance Data")
    print("="*60)
    
    try:
        zk = ZK(IP, port=PORT, timeout=TIMEOUT, password='', force_udp=False, ommit_ping=False)
        
        print("Connecting...")
        conn = zk.connect()
        print("✅ Connected")
        
        print("Fetching attendance logs...")
        start = time.time()
        attendances = conn.get_attendance()
        elapsed = time.time() - start
        
        print(f"✅ Got {len(attendances)} attendance records ({elapsed:.2f}s)")
        
        if attendances:
            print("\nFirst 3 records:")
            for i, att in enumerate(attendances[:3]):
                print(f"  {i+1}. User: {att.user_id}, Time: {att.timestamp}")
        
        conn.disconnect()
        print("✅ Disconnected successfully")
        return True
        
    except BrokenPipeError as e:
        print(f"❌ BROKEN PIPE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_multiple_connections():
    """Test 4: Multiple Sequential Connections"""
    print("\n" + "="*60)
    print("TEST 4: Multiple Sequential Connections (5x)")
    print("="*60)
    
    success_count = 0
    
    for i in range(1, 6):
        print(f"\n--- Attempt {i}/5 ---")
        try:
            zk = ZK(IP, port=PORT, timeout=TIMEOUT, password='', force_udp=False, ommit_ping=False)
            conn = zk.connect()
            
            # Quick operation
            try:
                users = conn.get_users()
                print(f"✅ Attempt {i}: Connected, got {len(users)} users")
                success_count += 1
            except Exception as e:
                print(f"❌ Attempt {i}: Connected but operation failed: {e}")
            
            conn.disconnect()
            
            # Wait between attempts
            if i < 5:
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Attempt {i}: Connection failed: {e}")
    
    print(f"\n📊 Success rate: {success_count}/5")
    return success_count == 5


def test_5_connection_with_delay():
    """Test 5: Connection with Various Delays"""
    print("\n" + "="*60)
    print("TEST 5: Connection After Various Delays")
    print("="*60)
    
    delays = [0, 5, 10, 30]
    
    for delay in delays:
        print(f"\n--- Delay: {delay}s ---")
        
        if delay > 0:
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)
        
        try:
            zk = ZK(IP, port=PORT, timeout=TIMEOUT, password='', force_udp=False, ommit_ping=False)
            conn = zk.connect()
            attendances = conn.get_attendance()
            print(f"✅ Success after {delay}s delay: {len(attendances)} records")
            conn.disconnect()
        except BrokenPipeError as e:
            print(f"❌ BROKEN PIPE after {delay}s delay: {e}")
        except Exception as e:
            print(f"❌ Error after {delay}s delay: {e}")


def main():
    print("="*60)
    print("X105 CONNECTION DIAGNOSTIC TOOL")
    print("="*60)
    print(f"Device: {IP}:{PORT}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Time: {datetime.now()}")
    
    results = []
    
    # Run tests
    results.append(("Socket Connectivity", test_1_socket_connectivity()))
    results.append(("ZK Connection", test_2_zk_connection()))
    results.append(("Get Attendance", test_3_get_attendance()))
    results.append(("Multiple Connections", test_4_multiple_connections()))
    test_5_connection_with_delay()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    if not results[0][1]:
        print("⚠️  Basic socket connection failed - check network/firewall")
    elif not results[1][1]:
        print("⚠️  ZK library cannot connect - check device compatibility")
    elif not results[2][1]:
        print("⚠️  Cannot fetch attendance - this is your main problem!")
        print("   Possible causes:")
        print("   1. Device is under heavy load")
        print("   2. Too many simultaneous connections")
        print("   3. Device firmware issue")
        print("   4. pyzk library incompatibility")
    elif not results[3][1]:
        print("⚠️  Multiple connections fail - device may have connection limit")
        print("   Try increasing delay between scheduler runs")
    else:
        print("✅ All tests passed - issue might be timing/scheduling related")


if __name__ == "__main__":
    main()
