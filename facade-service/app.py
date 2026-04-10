import time
import uuid
import random
from flask import Flask, request, jsonify
import requests as http_requests
import os
import hazelcast
import json

app = Flask(__name__)

CONFIG_SERVER_URL = os.environ.get("CONFIG_SERVER_URL", "http://config-server:8083")

hz_cluster = os.environ.get("HAZELCAST_CLUSTER", "hazelcast-1:5701,hazelcast-2:5701,hazelcast-3:5701").split(",")
hz_client = hazelcast.HazelcastClient(
    cluster_members=hz_cluster,
    cluster_name="dev"
)
queue = hz_client.get_queue("transactions_queue").blocking()

timing_stats = {
    "logging_service_total_ms": 0.0,
    "counter_service_total_ms": 0.0,
    "call_count": 0,
}

def get_service_addresses(service_name):
    try:
        resp = http_requests.get(f"{CONFIG_SERVER_URL}/services/{service_name}", timeout=5)
        resp.raise_for_status()
        return resp.json().get("addresses", [])
    except Exception as e:
        print(f"[facade] Error getting addresses for {service_name}: {e}")
        return []

def call_logging_service(method, path, **kwargs):
    urls = get_service_addresses("logging-service")
    if not urls:
        raise Exception("No logging-service instances found")
    
    random.shuffle(urls)
    last_err = None
    for url in urls:
        try:
            full_url = f"{url}{path}"
            if method == 'GET':
                resp = http_requests.get(full_url, timeout=5, **kwargs)
            else:
                resp = http_requests.post(full_url, timeout=5, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            print(f"[facade] Error calling logging-service at {url}: {e}")
            continue
    raise Exception(f"All logging-service instances failed. Last error: {last_err}")


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
        call_logging_service('POST', '/transaction', json=payload)
    except Exception as e:
        return jsonify({"error": f"logging-service error: {str(e)}"}), 502
    logging_time_ms = (time.time() - t0) * 1000

    # Put directly to Queue instead of HTTP to counter-service
    t0 = time.time()
    try:
        queue.put(json.dumps(payload))
    except Exception as e:
        return jsonify({"error": f"queue error: {str(e)}"}), 502
    counter_time_ms = (time.time() - t0) * 1000

    timing_stats["logging_service_total_ms"] += logging_time_ms
    timing_stats["counter_service_total_ms"] += counter_time_ms
    timing_stats["call_count"] += 1

    print(
        f"[facade] transaction={transaction_id} user={user_id} amount={amount} "
        f"log_ms={logging_time_ms:.1f} counter_queue_ms={counter_time_ms:.1f}"
    )

    # Balance is not returned immediately
    return jsonify({"transaction_id": transaction_id, "balance": None}), 200


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    t0 = time.time()
    try:
        counter_urls = get_service_addresses("counter-service")
        if not counter_urls:
            raise Exception("No counter-service instances found")
        
        counter_url = random.choice(counter_urls)
        balance_resp = http_requests.get(
            f"{counter_url}/balance/{user_id}", timeout=10
        )
        balance_resp.raise_for_status()
        balance_data = balance_resp.json()
    except Exception as e:
        return jsonify({"error": f"counter-service error: {str(e)}"}), 502
    counter_time_ms = (time.time() - t0) * 1000

    t0 = time.time()
    try:
        t_resp = call_logging_service('GET', f'/transactions/{user_id}')
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
        counter_urls = get_service_addresses("counter-service")
        if not counter_urls:
            raise Exception("No counter-service instances found")
        
        counter_url = random.choice(counter_urls)
        resp = http_requests.get(f"{counter_url}/balances", timeout=10)
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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
