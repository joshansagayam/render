import os
import time
import random
from flask import Flask, jsonify, request
import serial

app = Flask(__name__)


class LiFiTransmitter:
    def __init__(self):
        self.port = self._detect_serial_port()
        self.baudrate = 115200
        self.serial_conn = None
        self.lifi_available = False

    def _detect_serial_port(self):
        possible_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyS0']
        for port in possible_ports:
            if os.path.exists(port):
                return port
        return None  # No serial port found

    def connect(self):
        if not self.port:
            print("?? No serial port found. LiFi will be disabled.")
            return

        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Allow connection to stabilize
            self.lifi_available = True
            print(f"? LiFi connected to {self.port} @ {self.baudrate} baud")
        except Exception as e:
            print(f"? LiFi connection failed: {e}")

    def transmit(self, data):
        if not self.lifi_available:
            print("?? Skipping LiFi transmission (device not available).")
            return

        formatted_data = (
            "LIFI transmission (Marudham Care ICU Unit)\n"
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
            print("?? LiFi transmission successful")
        except Exception as e:
            print(f"? LiFi transmission failed: {e}")


# Initialize and connect to LiFi
lifi = LiFiTransmitter()
lifi.connect()


def predict_condition(heart_rate, spo2):
    if heart_rate < 60 or spo2 < 90:
        return "CRITICAL"
    elif heart_rate > 100 or spo2 < 95:
        return "WARNING"
    else:
        return "STABLE"


@app.route('/send-data', methods=['POST'])
def send_data():
    try:
        data = request.json
        heart_rate = int(data.get('heart_rate', random.randint(60, 100)))
        spo2 = int(data.get('spo2', random.randint(90, 100)))
        patient_id = data.get('patient_id', '001')
        name = data.get('name', 'John Doe')
        touch = bool(data.get('touch', False))

        prediction = predict_condition(heart_rate, spo2)

        patient_data = {
            "patient_id": patient_id,
            "name": name,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "touch": touch,
            "prediction": prediction
        }

        # Send data via LiFi
        lifi.transmit(patient_data)

        return jsonify({
            "status": "success",
            "message": "Data processed and sent successfully",
            "prediction": prediction
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


@app.route('/')
def home():
    return "????? Welcome to Marudham Care LiFi ICU Monitoring System!"


if __name__ == '__main__':
    app.run(debug=True)

