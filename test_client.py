import requests
import time
import threading
import argparse

FACADE_URL = "http://localhost:8080"


def send_transactions(user_id: str, amount: float, count: int, results: dict, idx: int):
    start = time.time()
    for _ in range(count):
        try:
            resp = requests.post(
                f"{FACADE_URL}/transaction",
                json={"user_id": user_id, "amount": amount},
                timeout=30,
            )
            if resp.status_code != 200:
                results[idx]["errors"] += 1
        except Exception:
            results[idx]["errors"] += 1
    elapsed = time.time() - start
    results[idx]["time"] = elapsed
    results[idx]["count"] = count


def run_scenario(scenario: int, num_clients: int = 10, t_per_client: int = 10000):
    print(f"Scenario {scenario}: {num_clients} clients x {t_per_client} transactions")
    requests.post(f"{FACADE_URL}/timing/reset")

    results = {i: {"time": 0, "count": 0, "errors": 0} for i in range(num_clients)}
    threads = []

    start_time = time.time()

    for i in range(num_clients):
        if scenario == 1:
            user_id = f"user_{i}"
        else:
            user_id = "shared_user"

        t = threading.Thread(
            target=send_transactions,
            args=(user_id, 1.0, t_per_client, results, i),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.time() - start_time
    total_requests = num_clients * t_per_client
    total_errors = sum(r["errors"] for r in results.values())
    rps = total_requests / total_time if total_time > 0 else 0

    print(f"\nResults:")
    print(f"Total time:       {total_time:.2f}s")
    print(f"Total requests:   {total_requests}")
    print(f"Errors:           {total_errors}")
    print(f"Requests/sec:     {rps:.1f}")

    try:
        timing = requests.get(f"{FACADE_URL}/timing").json()
        print(f"\nDownstream timing (accumulated on facade):")
        print(f"logging-service total:  {timing['logging_service_total_ms']:.1f} ms")
        print(f"counter-service total:  {timing['counter_service_total_ms']:.1f} ms")
        print(f"call count:             {timing['call_count']}")
    except Exception as e:
        print(f"Could not fetch timing: {e}")

    try:
        accounts = requests.get(f"{FACADE_URL}/accounts").json()
        print(f"\nFinal balances:")
        for uid, balance in accounts.get("balances", {}).items():
            print(f"  {uid}: {balance}")
    except Exception as e:
        print(f"Could not fetch accounts: {e}")


def main():
    parser = argparse.ArgumentParser(description="Performance test client")
    parser.add_argument(
        "--scenario",
        type=int,
        choices=[1, 2],
        default=None,
        help="Run specific scenario (1 or 2). Omit to run both.",
    )
    parser.add_argument(
        "--clients", type=int, default=10, help="Number of concurrent clients"
    )
    parser.add_argument("--t", type=int, default=10000, help="Transactions per client")
    args = parser.parse_args()

    if args.scenario is None or args.scenario == 1:
        run_scenario(1, args.clients, args.t)
    if args.scenario is None or args.scenario == 2:
        run_scenario(2, args.clients, args.t)


if __name__ == "__main__":
    main()
