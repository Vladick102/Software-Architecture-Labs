"""
Counter Service — Lab 5 (Kubernetes)

Reads queue name and Hazelcast config from the ConfigMap (env vars).
Background thread consumes the Hazelcast Distributed Queue and writes
balance updates to MongoDB.
"""

import json
import os
import threading
import time

import hazelcast
import pymongo
from flask import Flask, jsonify

app = Flask(__name__)

HZ_CLUSTER_MEMBERS = os.environ["HAZELCAST_CLUSTER_MEMBERS"].split(",")
HZ_CLUSTER_NAME = os.environ["HAZELCAST_CLUSTER_NAME"]
QUEUE_NAME = os.environ["QUEUE_NAME"]
MONGO_URL = os.environ["MONGO_URL"]


def connect_mongo():
    while True:
        try:
            client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            print(f"[counter-service] MongoDB connected at {MONGO_URL}")
            return client
        except Exception as e:
            print(f"[counter-service] Waiting for MongoDB... {e}")
            time.sleep(3)


mongo_client = connect_mongo()
balances_col = mongo_client["counter_db"]["balances"]


def connect_hazelcast():
    while True:
        try:
            client = hazelcast.HazelcastClient(
                cluster_members=HZ_CLUSTER_MEMBERS,
                cluster_name=HZ_CLUSTER_NAME,
            )
            print(
                f"[counter-service] Hazelcast connected. Members: {HZ_CLUSTER_MEMBERS}"
            )
            return client
        except Exception as e:
            print(f"[counter-service] Waiting for Hazelcast... {e}")
            time.sleep(3)


hz_client = connect_hazelcast()
queue = hz_client.get_queue(QUEUE_NAME).blocking()
print(f"[counter-service] Consuming queue '{QUEUE_NAME}'.")


def consume_messages():
    print("[counter-service] MQ Consumer started.")
    while True:
        try:
            item = queue.take()  # blocks until a message is available
            if item:
                data = json.loads(item)
                user_id = data["user_id"]
                amount = float(data["amount"])

                result = balances_col.find_one_and_update(
                    {"user_id": user_id},
                    {"$inc": {"balance": amount}},
                    upsert=True,
                    return_document=pymongo.ReturnDocument.AFTER,
                )
                print(
                    f"[counter-service] Processed: user={user_id} "
                    f"amount={amount:+.2f} balance={result['balance']:.2f}"
                )
        except Exception as e:
            print(f"[counter-service] Consumer error: {e}")
            time.sleep(1)


threading.Thread(target=consume_messages, daemon=True).start()


@app.route("/balance/<user_id>", methods=["GET"])
def get_user_balance(user_id):
    doc = balances_col.find_one({"user_id": user_id})
    balance = doc["balance"] if doc else 0.0
    return jsonify({"user_id": user_id, "balance": balance}), 200


@app.route("/balances", methods=["GET"])
def get_all_balances():
    docs = list(balances_col.find())
    return jsonify({d["user_id"]: d["balance"] for d in docs}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
