"""
Database Column Migration Script
=================================
Ensures sqlite table inspections has license_plate, notes, and threat_level columns.
"""

import sqlite3
import os

DB_PATH = "./data/app.db"


def migrate_database():
    if not os.path.exists(DB_PATH):
        print("Database file does not exist yet. It will be initialized on startup.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(inspections);")
    columns = [row[1] for row in cursor.fetchall()]

    if "license_plate" not in columns:
        print("Adding 'license_plate' column to inspections table...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN license_plate VARCHAR(30);")

    if "notes" not in columns:
        print("Adding 'notes' column to inspections table...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN notes TEXT;")

    if "threat_level" not in columns:
        print("Adding 'threat_level' column to inspections table...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN threat_level VARCHAR(20) DEFAULT 'normal';")

    conn.commit()
    conn.close()
    print("[OK] Database schema migration completed successfully.")


if __name__ == "__main__":
    migrate_database()
