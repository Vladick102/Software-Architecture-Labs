from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

transactions = {}
lock = threading.Lock()


@app.route("/transaction", methods=["POST"])
def store_transaction():
    data = request.get_json()
    transaction_id = data.get("transaction_id")
    user_id = data.get("user_id")
    amount = data.get("amount")

    if transaction_id is None or user_id is None or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    with lock:
        transactions[transaction_id] = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
        }

    print(
        f"[logging-service] Stored transaction: {transaction_id} | user={user_id} amount={amount}"
    )
    return jsonify({"status": "ok"}), 200


@app.route("/transactions", methods=["GET"])
def get_all_transactions():
    with lock:
        return jsonify(list(transactions.values())), 200


@app.route("/transactions/<user_id>", methods=["GET"])
def get_user_transactions(user_id):
    with lock:
        user_transactions = [
            t for t in transactions.values() if t["user_id"] == user_id
        ]
    return jsonify(user_transactions), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
