import serial
import time

# Use the USB-TTL port (adjust if necessary)
ser = serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=1)

# Sample patient data
patient_data = {
    "patient_id": "TEST_1",
    "name": "John Doe",
    "heart_rate": 92,
    "spo2": 97,
    "touch": False
}

# Convert to CSV-style string
data_str = f"{patient_data['patient_id']},{patient_data['name']},{patient_data['heart_rate']},{patient_data['spo2']},{int(patient_data['touch'])}"

try:
    while True:
        ser.write((data_str + '\n').encode())
        print("?? Sent via USB-TTL:", data_str)
        time.sleep(1)

except KeyboardInterrupt:
    print("? Transmission stopped.")
    ser.close()

