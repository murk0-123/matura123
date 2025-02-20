import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("sensor_data.db")
cursor = conn.cursor()

# Step 1: Create a new table with the correct timestamp type
cursor.execute("""
CREATE TABLE readings_new2 (
    id INTEGER PRIMARY KEY,
    value INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pump_state TEXT,
    auto_mode TEXT
);
""")

# Step 2: Copy data from the old table to the new one
cursor.execute("""
INSERT INTO readings_new2 (id, value, timestamp, pump_state, auto_mode)
SELECT id, value, timestamp, pump_state, auto_mode FROM readings;
""")

# Step 3: Drop the old table
cursor.execute("DROP TABLE readings;")

# Step 4: Rename the new table to match the old table name
cursor.execute("ALTER TABLE readings_new2 RENAME TO readings;")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Table structure updated successfully!")
