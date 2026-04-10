import time
import os
import threading
import requests
from flask import Flask, request, jsonify
import hazelcast

app = Flask(__name__)

config_server_url = os.environ.get("CONFIG_SERVER_URL", "http://config-server:8083")
service_name = os.environ.get("SERVICE_NAME", "logging-service")
host_address = os.environ.get("HOST", "http://localhost:8081")

def register_service():
    while True:
        try:
            resp = requests.post(
                f"{config_server_url}/register",
                json={"service_name": service_name, "address": host_address},
                timeout=5
            )
            if resp.status_code == 200:
                print(f"[logging-service] Registered with config server at {host_address}")
                break
        except Exception as e:
            print(f"[logging-service] Waiting for config server... {e}")
        time.sleep(2)

threading.Thread(target=register_service, daemon=True).start()

# Connect to Hazelcast cluster
hz_cluster = os.environ.get("HAZELCAST_CLUSTER", "hazelcast-1:5701,hazelcast-2:5701,hazelcast-3:5701").split(",")
client = hazelcast.HazelcastClient(
    cluster_members=hz_cluster,
    cluster_name="dev"
)
# Get or create the Distributed Map
transactions_map = client.get_map("transactions_map").blocking()

@app.route("/transaction", methods=["POST"])
def store_transaction():
    data = request.get_json()
    transaction_id = data.get("transaction_id")
    user_id = data.get("user_id")
    amount = data.get("amount")

    if transaction_id is None or user_id is None or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    transactions_map.put(transaction_id, {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "amount": amount,
    })

    print(f"[logging-service] Stored transaction: {transaction_id} | user={user_id} amount={amount}")
    return jsonify({"status": "ok"}), 200


@app.route("/transactions", methods=["GET"])
def get_all_transactions():
    values = list(transactions_map.values())
    return jsonify(values), 200


@app.route("/transactions/<user_id>", methods=["GET"])
def get_user_transactions(user_id):
    values = list(transactions_map.values())
    user_transactions = [t for t in values if t["user_id"] == user_id]
    return jsonify(user_transactions), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
