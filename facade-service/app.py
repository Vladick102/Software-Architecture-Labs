"""
Facade Service — Lab 5 (Kubernetes)

Service discovery  : Kubernetes DNS + ClusterIP Services (kube-proxy load-balances).
Configuration      : Injected via ConfigMap as environment variables.
No Consul, no custom config-server, no registration code needed.
"""

import json
import os
import time
import uuid

import hazelcast
from flask import Flask, jsonify, request
import requests as http_requests

app = Flask(__name__)

LOGGING_SERVICE_URL = os.environ["LOGGING_SERVICE_URL"]
COUNTER_SERVICE_URL = os.environ["COUNTER_SERVICE_URL"]
HZ_CLUSTER_MEMBERS = os.environ["HAZELCAST_CLUSTER_MEMBERS"].split(",")
HZ_CLUSTER_NAME = os.environ["HAZELCAST_CLUSTER_NAME"]
QUEUE_NAME = os.environ["QUEUE_NAME"]


def connect_hazelcast():
    while True:
        try:
            client = hazelcast.HazelcastClient(
                cluster_members=HZ_CLUSTER_MEMBERS,
                cluster_name=HZ_CLUSTER_NAME,
            )
            print(f"[facade] Hazelcast connected. Members: {HZ_CLUSTER_MEMBERS}")
            return client
        except Exception as e:
            print(f"[facade] Waiting for Hazelcast... {e}")
            time.sleep(3)


hz_client = connect_hazelcast()
transactions_queue = hz_client.get_queue(QUEUE_NAME).blocking()
print(f"[facade] Queue '{QUEUE_NAME}' ready.")

timing_stats = {
    "logging_service_total_ms": 0.0,
    "counter_service_total_ms": 0.0,
    "call_count": 0,
}


@app.route("/transaction", methods=["POST"])
def post_transaction():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if user_id is None or amount is None:
        return jsonify({"error": "Missing user_id or amount"}), 400

    transaction_id = str(uuid.uuid1())
    payload = {"transaction_id": transaction_id, "user_id": user_id, "amount": amount}

    t0 = time.time()
    try:
        resp = http_requests.post(
            f"{LOGGING_SERVICE_URL}/transaction", json=payload, timeout=5
        )
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"logging-service error: {e}"}), 502
    logging_ms = (time.time() - t0) * 1000

    t0 = time.time()
    try:
        transactions_queue.put(json.dumps(payload))
    except Exception as e:
        return jsonify({"error": f"queue error: {e}"}), 502
    queue_ms = (time.time() - t0) * 1000

    timing_stats["logging_service_total_ms"] += logging_ms
    timing_stats["counter_service_total_ms"] += queue_ms
    timing_stats["call_count"] += 1

    print(
        f"[facade] POST tx={transaction_id} user={user_id} amount={amount} "
        f"log_ms={logging_ms:.1f} queue_ms={queue_ms:.1f}"
    )
    return jsonify({"transaction_id": transaction_id, "balance": None}), 200


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    t0 = time.time()
    try:
        r = http_requests.get(f"{COUNTER_SERVICE_URL}/balance/{user_id}", timeout=10)
        r.raise_for_status()
        balance_data = r.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {e}"}), 502
    counter_ms = (time.time() - t0) * 1000

    t0 = time.time()
    try:
        r = http_requests.get(
            f"{LOGGING_SERVICE_URL}/transactions/{user_id}", timeout=5
        )
        r.raise_for_status()
        t_data = r.json()
    except Exception as e:
        return jsonify({"error": f"logging-service error: {e}"}), 502
    logging_ms = (time.time() - t0) * 1000

    print(
        f"[facade] GET /user/{user_id} log_ms={logging_ms:.1f} counter_ms={counter_ms:.1f}"
    )
    return (
        jsonify({"balance": balance_data.get("balance"), "transactions": t_data}),
        200,
    )


@app.route("/accounts", methods=["GET"])
def get_accounts():
    t0 = time.time()
    try:
        r = http_requests.get(f"{COUNTER_SERVICE_URL}/balances", timeout=10)
        r.raise_for_status()
        balances = r.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {e}"}), 502
    counter_ms = (time.time() - t0) * 1000
    print(f"[facade] GET /accounts counter_ms={counter_ms:.1f}")
    return jsonify({"balances": balances}), 200


@app.route("/timing", methods=["GET"])
def get_timing():
    return jsonify(timing_stats), 200


@app.route("/timing/reset", methods=["POST"])
def reset_timing():
    timing_stats["logging_service_total_ms"] = 0.0
    timing_stats["counter_service_total_ms"] = 0.0
    timing_stats["call_count"] = 0
    return jsonify({"status": "reset"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
