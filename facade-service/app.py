import time
import uuid
from flask import Flask, request, jsonify
import requests as http_requests

app = Flask(__name__)

import os

LOGGING_SERVICE_URL = os.environ.get(
    "LOGGING_SERVICE_URL", "http://logging-service:8081"
)
COUNTER_SERVICE_URL = os.environ.get(
    "COUNTER_SERVICE_URL", "http://counter-service:8082"
)

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

    payload = {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "amount": amount,
    }

    t0 = time.time()
    try:
        log_resp = http_requests.post(
            f"{LOGGING_SERVICE_URL}/transaction", json=payload, timeout=10
        )
        log_resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"logging-service error: {str(e)}"}), 502
    logging_time_ms = (time.time() - t0) * 1000

    t0 = time.time()
    try:
        counter_resp = http_requests.post(
            f"{COUNTER_SERVICE_URL}/transaction", json=payload, timeout=10
        )
        counter_resp.raise_for_status()
        counter_data = counter_resp.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {str(e)}"}), 502
    counter_time_ms = (time.time() - t0) * 1000

    timing_stats["logging_service_total_ms"] += logging_time_ms
    timing_stats["counter_service_total_ms"] += counter_time_ms
    timing_stats["call_count"] += 1

    balance = counter_data.get("balance")

    print(
        f"[facade] transaction={transaction_id} user={user_id} amount={amount} "
        f"balance={balance} log_ms={logging_time_ms:.1f} counter_ms={counter_time_ms:.1f}"
    )

    return jsonify({"transaction_id": transaction_id, "balance": balance}), 200


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    t0 = time.time()
    try:
        balance_resp = http_requests.get(
            f"{COUNTER_SERVICE_URL}/balance/{user_id}", timeout=10
        )
        balance_resp.raise_for_status()
        balance_data = balance_resp.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {str(e)}"}), 502
    counter_time_ms = (time.time() - t0) * 1000

    t0 = time.time()
    try:
        t_resp = http_requests.get(
            f"{LOGGING_SERVICE_URL}/transactions/{user_id}", timeout=10
        )
        t_resp.raise_for_status()
        t_data = t_resp.json()
    except Exception as e:
        return jsonify({"error": f"logging-service error: {str(e)}"}), 502
    logging_time_ms = (time.time() - t0) * 1000

    print(
        f"[facade] GET /user/{user_id} log_ms={logging_time_ms:.1f} counter_ms={counter_time_ms:.1f}"
    )

    return (
        jsonify(
            {
                "balance": balance_data.get("balance"),
                "transactions": t_data,
            }
        ),
        200,
    )


@app.route("/accounts", methods=["GET"])
def get_accounts():
    t0 = time.time()
    try:
        resp = http_requests.get(f"{COUNTER_SERVICE_URL}/balances", timeout=10)
        resp.raise_for_status()
        balances = resp.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {str(e)}"}), 502
    counter_time_ms = (time.time() - t0) * 1000

    print(f"[facade] GET /accounts counter_ms={counter_time_ms:.1f}")
    return jsonify({"balances": balances}), 200


@app.route("/timing", methods=["GET"])
def get_timing():
    return jsonify(timing_stats), 200


@app.route("/timing/reset", methods=["POST"])
def reset_timing():
    timing_stats["logging_service_total_ms"] = 0.0
    timing_stats["counter_service_total_ms"] = 0.0
    timing_stats["call_count"] = 0
    return jsonify({"status": "timing stats reset"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
