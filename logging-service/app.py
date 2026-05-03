import os
import time

import hazelcast
from flask import Flask, jsonify, request

app = Flask(__name__)

HZ_CLUSTER_MEMBERS = os.environ["HAZELCAST_CLUSTER_MEMBERS"].split(",")
HZ_CLUSTER_NAME = os.environ["HAZELCAST_CLUSTER_NAME"]


def connect_hazelcast():
    while True:
        try:
            client = hazelcast.HazelcastClient(
                cluster_members=HZ_CLUSTER_MEMBERS,
                cluster_name=HZ_CLUSTER_NAME,
            )
            print(
                f"[logging-service] Hazelcast connected. Members: {HZ_CLUSTER_MEMBERS}"
            )
            return client
        except Exception as e:
            print(f"[logging-service] Waiting for Hazelcast... {e}")
            time.sleep(3)


hz_client = connect_hazelcast()
transactions_map = hz_client.get_map("transactions_map").blocking()
print("[logging-service] Distributed Map 'transactions_map' ready.")


@app.route("/transaction", methods=["POST"])
def store_transaction():
    data = request.get_json()
    transaction_id = data.get("transaction_id")
    user_id = data.get("user_id")
    amount = data.get("amount")

    if transaction_id is None or user_id is None or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    transactions_map.put(
        transaction_id,
        {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
        },
    )
    print(
        f"[logging-service] Stored tx={transaction_id} user={user_id} amount={amount}"
    )
    return jsonify({"status": "ok"}), 200


@app.route("/transactions", methods=["GET"])
def get_all_transactions():
    return jsonify(list(transactions_map.values())), 200


@app.route("/transactions/<user_id>", methods=["GET"])
def get_user_transactions(user_id):
    values = list(transactions_map.values())
    return jsonify([t for t in values if t["user_id"] == user_id]), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
