import paho.mqtt.client as mqtt
import asyncio
import websockets

# Set of connected clients
connected_clients = set()

# Function to handle each client connection
async def handle_client(websocket):
    # Add the new client to the set of connected clients
    connected_clients.add(websocket)
    try:
        # Listen for messages from the client
        async for message in websocket:
            # Broadcast the message to all other connected clients
            for client in connected_clients.copy():
                if client != websocket:
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Remove the client from the set of connected clients
        connected_clients.remove(websocket)

# Main function to start the WebSocket server
async def main():
    server = await websockets.serve(handle_client, 'localhost', 12345)
    await server.wait_closed()

# Define callbacks
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code: {reason_code}")
    # Subscribing in on_connect() ensures subscriptions are renewed on reconnect
    client.subscribe("sensors/temperature")

def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic} | Payload: {msg.payload.decode()}")

# Initialize client (VERSION2 is recommended for new projects)
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

# Connect to a public broker (e.g., Eclipse or EMQX)
mqttc.connect("mqtt.eclipseprojects.io", 1883, 60)

# Blocking loop that handles network traffic and auto-reconnects
mqttc.loop_forever()

# Run the server
if __name__ == "__main__":
    asyncio.run(main())