import requests


def run_tests():
    print("Sending 10 transactions...")
    for i in range(1, 11):
        try:
            resp = requests.post(
                "http://localhost:8080/transaction",
                json={"user_id": "vlad", "amount": 10},
                timeout=5,
            )
            print(f"Req {i}: {resp.status_code} {resp.text.strip()}")
        except Exception as e:
            print(f"Req {i} failed: {e}")

    print("\nGetting balances...")
    try:
        resp = requests.get("http://localhost:8080/accounts", timeout=5)
        print(resp.status_code, resp.text.strip())
    except Exception as e:
        print("Failed to get accounts:", e)


if __name__ == "__main__":
    run_tests()
