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

def send_downlink(dev_eui, payload):
    try:
        with grpc.insecure_channel(CHIRPSTACK_SERVER) as channel:
            client = api.DeviceServiceStub(channel)
            auth_token = [("authorization", f"Bearer {CHIRPSTACK_API_TOKEN}")]

            req = api.EnqueueDeviceQueueItemRequest()
            req.queue_item.confirmed = False
            req.queue_item.data = base64.b64encode(bytes(payload)).decode('utf-8')
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
        command = message.get("command")

        if not dev_eui or command not in ["on", "off"]:
            return jsonify({"error": "Invalid request payload"}), 400

        payload = [0x01] if command == "on" else [0x00]
        response = send_downlink(dev_eui, payload)

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
