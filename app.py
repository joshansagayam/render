import os
import sys
import platform
import time
import serial
from flask import Flask, request, jsonify
import joblib
import pandas as pd
import requests

# Function to check if running on Jetson device
def is_jetson():
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
            return "nvidia" in model or "jetson" in model
    except FileNotFoundError:
        return False

print("🔍 Platform:", platform.platform())
print("🧠 Architecture:", platform.machine())

if is_jetson():
    print("🟢 Detected Jetson device.")
else:
    print("🔵 Non-Jetson platform.")

# LiFi Transmission Class
class LiFiTransmitter:
    def __init__(self):
        self.port = self._detect_serial_port()
        self.baudrate = 115200  # Match your transmitter's baud rate
        self.serial_conn = None
        
    def _detect_serial_port(self):
        possible_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyS0']
        for port in possible_ports:
            if os.path.exists(port):
                return port
        raise Exception("❌ No serial port detected for LiFi")
    
    def connect(self):
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Initialization delay
            print(f"✅ LiFi connected to {self.port} @ {self.baudrate} baud")
        except Exception as e:
            print(f"❌ LiFi connection failed: {e}")

    def transmit(self, data):
        if not self.serial_conn:
            self.connect()
        
        formatted_data = (
            "LIFI transmission(marudham care ICU unit)\n"
            f"Patient ID: {data['patient_id']}\n"
            f"Name: {data['name']}\n"
            f"Heart Rate: {data['heart_rate']} bpm\n"
            f"SpO2: {data['spo2']}%\n"
            f"Touch Alert: {'ACTIVE' if data['touch'] else 'inactive'}\n"
            f"Condition: {data['prediction']}\n"
            "=========================\n"
        )
        
        try:
            self.serial_conn.write(formatted_data.encode('utf-8'))
            print("📡 LiFi transmission successful")
        except Exception as e:
            print(f"❌ LiFi transmission failed: {e}")

# Initialize Flask and LiFi
app = Flask(__name__)
lifi = LiFiTransmitter()

# Load ML model
try:
    model = joblib.load('model.pkl')
    print("✅ ML model loaded successfully")
except Exception as e:
    sys.exit(f"❌ Failed to load model.pkl: {e}")

# Pushover config
PUSHOVER_USER_KEY = "ubmb1u4fefwc8pftdyt92yaw9w6351"
PUSHOVER_API_TOKEN = "afhf97c69g51af75f37u1thvw3j6xt"

# Data storage setup
DATA_FOLDER = "data"
CSV_FILE = os.path.join(DATA_FOLDER, "patient_data.csv")
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
    with open(CSV_FILE, "w") as f:
        f.write("patient_id,name,heart_rate,spo2,touch,prediction\n")
    print(f"📁 Created data storage at {CSV_FILE}")

def send_alert(name, patient_id):
    message = f"🚨 ALERT: {name} ({patient_id}) - Critical condition or touch detected!"
    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message,
        "title": "Patient Monitor Alert",
        "priority": 1
    }
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
        print("✅ Alert sent:", response.status_code)
    except Exception as e:
        print("❌ Failed to send alert:", e)

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print("\n📥 Incoming Data:", data)

        # Extract data
        patient_id = data.get('patient_id')
        name = data.get('name')
        heart_rate = data.get('heart_rate')
        spo2 = data.get('spo2')
        touch = data.get('touch')

        # Model prediction
        features_df = pd.DataFrame([{
            'heart_rate': heart_rate,
            'spo2': spo2,
            'touch': touch
        }])
        prediction = model.predict(features_df)[0]
        print(f"🧠 Prediction: {name} ({patient_id}) -> {prediction}")

        # Alert logic
        if str(prediction).lower() == 'critical' or touch:
            send_alert(name, patient_id)

        # Store data
        new_entry = pd.DataFrame([{
            'patient_id': patient_id,
            'name': name,
            'heart_rate': heart_rate,
            'spo2': spo2,
            'touch': touch,
            'prediction': prediction
        }])
        new_entry.to_csv(CSV_FILE, mode='a', index=False, header=False)

        # LiFi transmission
        lifi_data = {
            'patient_id': patient_id,
            'name': name,
            'heart_rate': heart_rate,
            'spo2': spo2,
            'touch': touch,
            'prediction': prediction
        }
        lifi.transmit(lifi_data)

        return jsonify({"status": "success", "prediction": prediction}), 200

    except Exception as e:
        print(f"❌ Processing error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    print("\n🚀 Starting Patient Monitoring System")
    try:
        lifi.connect()  # Initialize LiFi connection
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        if lifi.serial_conn:
            lifi.serial_conn.close()
        print("\n🛑 Server shutdown gracefully")
