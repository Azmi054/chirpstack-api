from flask import Flask, request, jsonify
import grpc
import base64
import os
from chirpstack_api import api

app = Flask(__name__)

CHIRPSTACK_SERVER = os.getenv("CHIRPSTACK_SERVER")
CHIRPSTACK_API_TOKEN = os.getenv("CHIRPSTACK_API_TOKEN")
F_PORT = 10  # Port sesuai contoh yang kamu berikan

def process_payload(payload):
    """Mengonversi payload ke format bytes sesuai kebutuhan API ChirpStack."""
    if isinstance(payload, str):
        # Jika payload adalah base64, coba decode
        try:
            return base64.b64decode(payload)
        except Exception:
            pass

        # Jika string "on" atau "off", ubah ke format ASCII
        if payload.lower() == "on":
            return "ON 1".encode("ascii")
        elif payload.lower() == "off":
            return "OFF 0".encode("ascii")

        # Jika string biasa, konversi ke ASCII
        return payload.encode("ascii")

    elif isinstance(payload, int):
        return f"{payload}".encode("ascii")

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

        # Pastikan payload dalam format bytes
        if not isinstance(processed_payload, bytes):
            return {"status": "error", "message": f"Expected bytes, but got {type(processed_payload)}"}

        # Buat koneksi ke ChirpStack
        with grpc.insecure_channel(CHIRPSTACK_SERVER) as channel:
            client = api.DeviceServiceStub(channel)
            auth_token = [("authorization", f"Bearer {CHIRPSTACK_API_TOKEN}")]

            # Buat request
            req = api.EnqueueDeviceQueueItemRequest()
            req.queue_item.confirmed = False
            req.queue_item.f_port = F_PORT
            req.queue_item.data = processed_payload
            req.queue_item.dev_eui = dev_eui

            # Kirim downlink
            resp = client.Enqueue(req, metadata=auth_token)
            return {"status": "success", "downlink_id": resp.id}

    except grpc.RpcError as e:
        return {"status": "error", "code": str(e.code()), "message": e.details()}

@app.route('/downlink', methods=['POST'])
def downlink():
    try:
        message = request.get_json()
        dev_eui = message.get("dev_eui")
        payload = message.get("payload")

        if not dev_eui or payload is None:
            return jsonify({"error": "Invalid request payload"}), 400

        response = send_downlink(dev_eui, payload)
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
