import sqlite3

# Define path to database file
DB_PATH = "db_files/x105.db"

# Connect to database
conn = sqlite3.connect(DB_PATH)

# Create cursor object
cursor = conn.cursor()

# Run query to add columns
cursor.execute("""
    ALTER TABLE machines ADD COLUMN firmware TEXT;
""")
cursor.execute("""
    ALTER TABLE machines ADD COLUMN sn TEXT;
""")

# Commit changes and close connection
conn.commit()
conn.close()