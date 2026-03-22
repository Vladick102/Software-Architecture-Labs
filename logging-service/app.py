from flask import Flask, request, jsonify
import hazelcast
import os

app = Flask(__name__)

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
    # Fetch all and filter (for simplicity)
    values = list(transactions_map.values())
    user_transactions = [t for t in values if t["user_id"] == user_id]
    return jsonify(user_transactions), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
