#Flask
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from flask_cors import CORS

#Firebase
import firebase_admin
from firebase_admin import credentials, firestore

#MQTT to receive date from esp32
import paho.mqtt.client as mqtt

#Other imports
from datetime import datetime
import json
import requests

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)
CORS(app, resources={r"/*": {"origins": "*"}})

# MQTT CONFIG
MQTT_BROKER = "broker.hivemq.com" 
MQTT_TOPIC = "esp32MyProject/data"

# ------------------ TELEGRAM CONFIG ------------------
BOT_TOKEN = "8606618607:AAFj3axkB_iIHvV_3RiWj3Q2gfl6enoIe7k"
CHAT_ID = "-5062317954"

# Global variables
status = "NORMAL"


# ------------------ FIREBASE SETUP ------------------
cred = credentials.Certificate("firebase_key.json")  # Ensure this JSON is in same folder
firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        requests.post(url, data=payload)
        print("Telegram alert sent!")
    except Exception as e:
        print("Telegram Error:", e)

# When MQTT receives message
def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    global status
    print("MQTT Received:", data)
    curr_timestamp = datetime.now()
    data["timestamp"] = curr_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    if data["status"].upper() == "OVERLOAD" and status == "NORMAL":
        db.collection("overloaded_vehicles").add(data)
        send_telegram_alert(
            f"🚨 OVERLOAD ALERT \nVehicle: {data['vehicle_number']}\nWeight: {data['weight']} kg"
        )
        

    status = data["status"].upper()

    # Send to WebSocket clients
    socketio.emit('update', data)

# Setup MQTT
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe(MQTT_TOPIC)

# Run MQTT in background
mqtt_client.loop_start()

# ------------------ ROUTES ------------------

@app.route('/')
def home():
    return render_template("dashboard.html")

@app.route('/updates')
def updates():
    return render_template("realtime.html")

@app.route('/get-vehicles')
def get_vehicles():
    docs = db.collection('vehicle details').stream()

    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append({
            "vehicle_number": d.get("number"),
            "weight": 0,
            "status": "NORMAL",
            "timestamp": ""
        })

    return jsonify(data)

@app.route('/test')
def test():
    return "Test route works!"

# ------------------ NEW ROUTE: Receive data from ESP32 ------------------
@app.route('/add_load', methods=['POST'])
def add_load():
    try:
        data = request.get_json()  # JSON from ESP32
        if not data:
            return jsonify({"status": "error", "message": "No JSON received"}), 400

        # Optional: print for debugging
        print("Received from ESP32:", data)

        # Add current datetime to data
        data['overload_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add to Firestore collection
        db.collection("Vehicle data").add(data)

        # TELEGRAM ALERT
        if data.get("status") == "OVERLOAD":
            message = f"""OVERLOAD ALERT 

                Vehicle: {data.get('vehicle_number')}
                Weight: {data.get('weight')} kg
                Time: {data.get('overload_time')}
            """
            send_telegram_alert(message)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_loads', methods=['GET'])
def get_loads():
    docs = db.collection('overloaded_vehicles').stream()

    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append({
            "vehicle_number": d.get("vehicle_number"),
            "weight": d.get("weight"),
            "status": d.get("status"),
            "timestamp": d.get("timestamp") or d.get("overload_time")
        })

    return jsonify(data)   #  IMPORTANT

# Run the server
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
