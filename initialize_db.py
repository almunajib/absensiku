import sqlite3
import os
import sys

# Add project root to allow imports from core_files
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)
from core_files import config


def migrate_database(conn):
    """
    Checks for missing columns in the 'machines' table and adds them.
    This ensures backward compatibility with older database schemas.
    """
    cursor = conn.cursor()
    print("Checking database schema...")

    # Get a list of columns in the 'machines' table
    cursor.execute("PRAGMA table_info(machines)")
    columns = [row[1] for row in cursor.fetchall()]

    # Check if 'sync_schedule' column is missing and add it if so
    if "sync_schedule" not in columns:
        print("Column 'sync_schedule' not found. Adding it now...")
        cursor.execute("ALTER TABLE machines ADD COLUMN sync_schedule TEXT")
        print("✓ Column 'sync_schedule' added successfully.")

    if "db_record_count" not in columns:
        print("Column 'db_record_count' not found. Adding it now...")
        cursor.execute("ALTER TABLE machines ADD COLUMN db_record_count INTEGER DEFAULT 0")
        print("✓ Column 'db_record_count' added successfully.")

def initialize_database():
    """
    Creates the 'machines' table if it doesn't exist and adds the default machine.
    """
    try:
        conn = sqlite3.connect(config.SQLITE_FILENAME)
        cursor = conn.cursor()

        # Create machines table
        print("Creating 'machines' table if it doesn't exist...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip_address TEXT NOT NULL UNIQUE,
            port INTEGER NOT NULL,
            location TEXT,
            firmware TEXT,
            sn TEXT,
            user_count INTEGER,
            record_count INTEGER,
            sync_schedule TEXT,
            db_record_count INTEGER
        )
        """)

        # Run migration to add missing columns to the existing table
        migrate_database(conn)

        # Check if the default machine already exists
        print(f"Checking for default machine (IP: {config.DEFAULT_IP})...")
        cursor.execute("SELECT * FROM machines WHERE ip_address = ?", (config.DEFAULT_IP,))
        existing_machine = cursor.fetchone()

        if existing_machine:
            print("Default machine already exists in the database.")
        else:
            # Add the default machine from the old config
            print("Inserting default machine...")
            cursor.execute(
                """
            INSERT INTO machines (name, ip_address, port, location, firmware, sn)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    f"{config.DEVICE_TYPE} Device (Default)",
                    config.DEFAULT_IP,
                    config.DEFAULT_PORT,
                    "Default Location",
                    "Default Version",
                    "Default SN",
                ),
            )
            print("Default machine added successfully.")

        conn.commit()
        print("Database initialization complete.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    # Ensure the db_files directory exists
    config.ensure_paths()
    print(f"Initializing database at: {config.SQLITE_FILENAME}")
    initialize_database()
