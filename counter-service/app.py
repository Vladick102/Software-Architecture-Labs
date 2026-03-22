from flask import Flask, request, jsonify
import pymongo
import os

app = Flask(__name__)

mongo_url = os.environ.get("MONGO_URL", "mongodb://mongo:27017/")
client = pymongo.MongoClient(mongo_url)
db = client["counter_db"]
balances_col = db["balances"]


@app.route("/transaction", methods=["POST"])
def process_transaction():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if user_id is None or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    amount = float(amount)
    
    # Atomic upsert/increment
    result = balances_col.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"balance": amount}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    current_balance = result["balance"]

    print(f"[counter-service] user={user_id} amount={amount:+.2f} balance={current_balance:.2f}")
    return jsonify({"user_id": user_id, "balance": current_balance}), 200


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
