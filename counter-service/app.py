import time
import os
import threading
import requests
from flask import Flask, jsonify
import pymongo
import hazelcast
import json

app = Flask(__name__)

config_server_url = os.environ.get("CONFIG_SERVER_URL", "http://config-server:8083")
service_name = os.environ.get("SERVICE_NAME", "counter-service")
host_address = os.environ.get("HOST", "http://counter-service:8082")

def register_service():
    while True:
        try:
            resp = requests.post(
                f"{config_server_url}/register",
                json={"service_name": service_name, "address": host_address},
                timeout=5
            )
            if resp.status_code == 200:
                print(f"[counter-service] Registered with config server at {host_address}")
                break
        except Exception as e:
            print(f"[counter-service] Waiting for config server... {e}")
        time.sleep(2)

threading.Thread(target=register_service, daemon=True).start()

mongo_url = os.environ.get("MONGO_URL", "mongodb://mongo:27017/")
client = pymongo.MongoClient(mongo_url)
db = client["counter_db"]
balances_col = db["balances"]

# Connect to Hazelcast cluster
hz_cluster = os.environ.get("HAZELCAST_CLUSTER", "hazelcast-1:5701,hazelcast-2:5701,hazelcast-3:5701").split(",")
hz_client = hazelcast.HazelcastClient(
    cluster_members=hz_cluster,
    cluster_name="dev"
)
queue = hz_client.get_queue("transactions_queue").blocking()

def consume_messages():
    print("[counter-service] MQ Consumer started.")
    while True:
        try:
            # take() blocks until an item is available
            item = queue.take()
            if item:
                data = json.loads(item)
                user_id = data.get("user_id")
                amount = float(data.get("amount", 0))

                # Atomic upsert/increment
                result = balances_col.find_one_and_update(
                    {"user_id": user_id},
                    {"$inc": {"balance": amount}},
                    upsert=True,
                    return_document=pymongo.ReturnDocument.AFTER
                )
                current_balance = result["balance"]
                print(f"[counter-service] Processed MQ msg: user={user_id} amount={amount:+.2f} balance={current_balance:.2f}")
        except Exception as e:
            print(f"[counter-service] MQ Consumer error: {e}")
            time.sleep(1)

threading.Thread(target=consume_messages, daemon=True).start()

@app.route("/balance/<user_id>", methods=["GET"])
def get_user_balance(user_id):
    doc = balances_col.find_one({"user_id": user_id})
    balance = doc["balance"] if doc else 0.0
    return jsonify({"user_id": user_id, "balance": balance}), 200


@app.route("/balances", methods=["GET"])
def get_all_balances():
    docs = balances_col.find()
    all_balances = {d["user_id"]: d["balance"] for d in docs}
    return jsonify(all_balances), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
