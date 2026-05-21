# main_modules/x105_restart.py
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_files.x105_machine import X105Client


def get_client():
    return X105Client()


client = get_client()


def main():
    success, msg = client.restart_device()
    print("🔄 Restart X105 device success")


if __name__ == "__main__":
    main()
