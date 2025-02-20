from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import serial
import sqlite3
import time
import threading
from datetime import datetime, timedelta

app = Flask(__name__, template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*")

auto_mode = True  # Default to auto mode
pump_state = "OFF"  # Default pump state

# Timezone offset (e.g., UTC+1 for Slovenia)
TIMEZONE_OFFSET = timedelta(hours=1)  # Adjust this if your timezone is different

# Try USB first, then Bluetooth
def get_serial_connection():
    ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "COM6", "COM7"]  # Adjust based on OS
    for port in ports:
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            print(f"✅ Connected to {port}")
            return ser
        except serial.SerialException:
            print(f"❌ Failed to connect to {port}")
    print("❌ No available USB or Bluetooth connections found!")
    return None

bt = get_serial_connection()

# Function to get the current timestamp with the timezone offset
def get_local_timestamp():
    utc_now = datetime.utcnow()  # Get the current time in UTC
    local_now = utc_now + TIMEZONE_OFFSET  # Apply the timezone offset
    return local_now  # Return as datetime object

# Database initialization with timezone-aware timestamps
def init_db():
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY, 
            value INTEGER, 
            timestamp TEXT,
            pump_state TEXT
        )
        """
    )
    conn.commit()
    conn.close()

# Initialize the database
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/latest")
def latest_data():
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value, timestamp, pump_state FROM readings ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({"value": row[0], "timestamp": row[1], "pump_state": row[2]})
    else:
        return jsonify({"error": "No sensor data found"}), 404

@app.route("/latest_10")
def latest_10_readings():
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value, timestamp, pump_state FROM readings ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    # Format the readings as a list of dictionaries
    readings = [{"value": row[0], "timestamp": row[1], "pump_state": row[2]} for row in rows]
    
    if readings:
        return jsonify(readings)
    else:
        return jsonify({"error": "No sensor data found"}), 404

@app.route("/search", methods=["GET"])
def search_readings():
    search_timestamp = request.args.get("timestamp")
    print(f"Searching for timestamp: {search_timestamp}")  # Debugging line
    
    # Ensure the timestamp is in the correct format (DD/MM/YYYY HH:MM)
    try:
        search_datetime = datetime.strptime(search_timestamp, "%d/%m/%Y %H:%M")
        search_timestamp_str = search_datetime.strftime("%d/%m/%Y %H:%M")  # Store the timestamp format
        
        conn = sqlite3.connect("sensor_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value, timestamp, pump_state FROM readings WHERE timestamp = ? ORDER BY id DESC", (search_timestamp_str,))
        rows = cursor.fetchall()
        conn.close()

        # If results are found
        if rows:
            readings = [{"value": row[0], "timestamp": row[1], "pump_state": row[2]} for row in rows]
            return jsonify(readings)
        else:
            return jsonify({"error": "No readings found for this timestamp"}), 404
        
    except ValueError:
        return jsonify({"error": "Invalid timestamp format. Please use DD/MM/YYYY HH:MM"}), 400

@app.route("/control", methods=["POST"])
def control():
    global auto_mode, pump_state
    data = request.json
    if "auto" in data:
        auto_mode = data["auto"]
        return jsonify({"message": "Auto mode updated", "auto": auto_mode})
    elif "state" in data:
        state = data["state"]
        if state == "ON":
            pump_state = "ON"
            bt.write(b'1')
        elif state == "OFF":
            pump_state = "OFF"
            bt.write(b'0')
        return jsonify({"message": f"Pump state set to {pump_state}"}) 


# Store sensor data in the database with the correct timezone-aware timestamp
def store_reading(value, pump_state):
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    timestamp = get_local_timestamp()  # Get the timestamp in the local timezone
    timestamp_str = timestamp.strftime("%d/%m/%Y %H:%M")  # Store full date and time
    cursor.execute("INSERT INTO readings (value, timestamp, pump_state) VALUES (?, ?, ?)", (value, timestamp_str, pump_state))
    conn.commit()
    conn.close()

def read_sensor_data():
    global bt, auto_mode, pump_state
    while True:
        if bt:
            try:
                line = bt.readline().decode("utf-8").strip()
                if line.startswith("SENSOR:"):
                    value = int(line.split(":")[1].strip())
                    if auto_mode:
                        if value > 500:
                            pump_state = "ON"
                            bt.write(b'1')
                        elif value < 300:
                            pump_state = "OFF"
                            bt.write(b'0')
                    store_reading(value, pump_state)  # Store the data with the correct timezone
                    print(f"📊 Stored in database: {value}, Pump: {pump_state}")
                    socketio.emit("sensor_update", {"value": value, "pump_state": pump_state})
            except Exception as e:
                print(f"❌ Error reading serial data: {e}")
                bt = get_serial_connection()
                time.sleep(5)

# Start the sensor data reading thread
sensor_thread = threading.Thread(target=read_sensor_data, daemon=True)
sensor_thread.start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)