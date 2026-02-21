from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

balances = {}
lock = threading.Lock()


@app.route("/transaction", methods=["POST"])
def process_transaction():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if user_id is None or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    amount = float(amount)

    with lock:
        if user_id not in balances:
            balances[user_id] = 0.0
        balances[user_id] += amount
        current_balance = balances[user_id]

    print(
        f"[counter-service] user={user_id} amount={amount:+.2f} balance={current_balance:.2f}"
    )
    return jsonify({"user_id": user_id, "balance": current_balance}), 200


@app.route("/balance/<user_id>", methods=["GET"])
def get_user_balance(user_id):
    with lock:
        balance = balances.get(user_id, 0.0)
    return jsonify({"user_id": user_id, "balance": balance}), 200


@app.route("/balances", methods=["GET"])
def get_all_balances():
    with lock:
        all_balances = dict(balances)
    return jsonify(all_balances), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
