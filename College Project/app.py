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

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)
CORS(app, resources={r"/*": {"origins": "*"}})

# MQTT CONFIG
MQTT_BROKER = "broker.hivemq.com"   # or your broker
MQTT_TOPIC = "esp32MyProject/data"
timestamp = datetime.now()
weight = 0.00
status = "Normal"
time_threshold = 2 #minutes
weight_threshold = 40


# ------------------ FIREBASE SETUP ------------------
cred = credentials.Certificate("firebase_key.json")  # Ensure this JSON is in same folder
firebase_admin.initialize_app(cred)
# bot token
BOT_TOKEN=" HTTP API:8606618607:AAFj3axkB_iIHvV_3RiWj3Q2gfl6enoIe7k"
CHAT_ID="5718007268"

# Firestore client
db = firestore.client()

# When MQTT receives message
def on_message(client, userdata, msg):
    vehicle_number = ""
    data = json.loads(msg.payload.decode())
    global timestamp, weight, status
    print("MQTT Received:", data)
    curr_timestamp = datetime.now()
    data["timestamp"] = curr_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    query = db.collection("Vehicle numbers").where("device_id", "==", data["vehicle_number"]).get()
    for i in query:
        vehicle_number = i.get("vehicle_number")
    data["vehicle_number"] = vehicle_number
    if (curr_timestamp - timestamp).total_seconds() / 60 >= time_threshold or abs(weight - data["weight"]) >= weight_threshold or status != data["status"]:
        db.collection("Vehicle data").add(data)
        if (curr_timestamp - timestamp).total_seconds() / 60 >= time_threshold:
            timestamp = curr_timestamp
    weight = data["weight"]
    status = data["status"]

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
    docs = db.collection('Vehicle numbers').stream()

    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append({
            "vehicle_number": d.get("vehicle_number"),
            "weight": 0,
            "status": "Normal",
            "timestamp": ""
        })

    return jsonify(data)   #  IMPORTANT

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

        return jsonify({"status": "success", "message": "Data saved to Firestore"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_loads', methods=['GET'])
def get_loads():
    docs = db.collection('Vehicle data').stream()

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
    socketio.run(app, host='0.0.0.0', port=5000)
