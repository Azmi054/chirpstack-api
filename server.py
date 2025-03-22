from flask import Flask, request, jsonify
import json
import grpc
import base64
import os
from chirpstack_api import api

app = Flask(__name__)

CHIRPSTACK_SERVER = os.getenv("CHIRPSTACK_SERVER")
CHIRPSTACK_API_TOKEN = os.getenv("CHIRPSTACK_API_TOKEN")
F_PORT = 1

def process_payload(payload):
    """Mengonversi payload ke format bytes yang sesuai."""
    if isinstance(payload, str):
        try:
            # Cek apakah string base64
            decoded = base64.b64decode(payload)
            return decoded
        except Exception:
            pass
        
        # Cek jika string angka biner ('01', '00')
        if payload in ["01", "00"]:
            return bytes([int(payload, 16)])
        
        # Cek jika string 'on' atau 'off'
        if payload.lower() == "on":
            return bytes([0x01])
        elif payload.lower() == "off":
            return bytes([0x00])
        
        return None
    
    elif isinstance(payload, int):
        return bytes([payload])
    
    elif isinstance(payload, list):
        return bytes(payload)
    
    elif isinstance(payload, bytes):
        return payload
    
    return None

def send_downlink(dev_eui, payload):
    try:
        processed_payload = process_payload(payload)
        if processed_payload is None:
            return {"status": "error", "message": "Invalid payload format"}

        with grpc.insecure_channel(CHIRPSTACK_SERVER) as channel:
            client = api.DeviceServiceStub(channel)
            auth_token = [("authorization", f"Bearer {CHIRPSTACK_API_TOKEN}")]

            req = api.EnqueueDeviceQueueItemRequest()
            req.queue_item.confirmed = False
            req.queue_item.data = base64.b64encode(processed_payload).decode('utf-8')
            req.queue_item.dev_eui = dev_eui
            req.queue_item.f_port = F_PORT

            resp = client.Enqueue(req, metadata=auth_token)
            return {"status": "success", "downlink_id": resp.id}

    except grpc.RpcError as e:
        return {"status": "error", "code": str(e.code()), "message": e.details()}

@app.route('/downlink', methods=['POST'])
def downlink():
    try:
        message = request.get_json()
        dev_eui = message.get("dev_eui")
        payload = message.get("payload")  # Bisa string, int, list, atau base64

        if not dev_eui or payload is None:
            return jsonify({"error": "Invalid request payload"}), 400

        response = send_downlink(dev_eui, payload)
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint untuk mengecek apakah API berjalan."""
    return jsonify({"status": "running"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
