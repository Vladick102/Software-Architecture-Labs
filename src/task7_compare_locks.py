import hazelcast
import multiprocessing
import time

CLUSTER_MEMBERS = ["localhost:5701", "localhost:5702", "localhost:5703"]
MAP_NAME = "lock-demo"
KEY = "counter"
ITERATIONS = 10_000
NUM_CLIENTS = 3


def worker_no_lock(worker_id: int, result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    start = time.time()
    for _ in range(ITERATIONS):
        value = hz_map.get(KEY) or 0
        hz_map.put(KEY, value + 1)
    elapsed = time.time() - start
    result_queue.put(elapsed)
    client.shutdown()


def worker_pessimistic(worker_id: int, result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    start = time.time()
    for _ in range(ITERATIONS):
        hz_map.lock(KEY)
        try:
            value = hz_map.get(KEY) or 0
            hz_map.put(KEY, value + 1)
        finally:
            hz_map.unlock(KEY)
    elapsed = time.time() - start
    result_queue.put(elapsed)
    client.shutdown()


def worker_optimistic(worker_id: int, result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    start = time.time()
    for _ in range(ITERATIONS):
        while True:
            old_val = hz_map.get(KEY) or 0
            if hz_map.replace_if_same(KEY, old_val, old_val + 1):
                break
    elapsed = time.time() - start
    result_queue.put(elapsed)
    client.shutdown()


def run_strategy(label: str, worker_fn) -> tuple[int, float]:
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    hz_map.put(KEY, 0)
    client.shutdown()

    rq = multiprocessing.Queue()
    procs = [
        multiprocessing.Process(target=worker_fn, args=(i + 1, rq))
        for i in range(NUM_CLIENTS)
    ]

    wall_start = time.time()
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    wall_elapsed = time.time() - wall_start

    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    final = hz_map.get(KEY)
    client.shutdown()

    print(f"  [{label}] final={final:,}  time={wall_elapsed:.3f}s")
    return final, wall_elapsed


def main():
    expected = NUM_CLIENTS * ITERATIONS

    print("  TASK 7: Lock Strategy Comparison")
    print(f"  Clients  : {NUM_CLIENTS}")
    print(f"  Iterations each: {ITERATIONS:,}")
    print(f"  Expected result: {expected:,}")
    print()

    print("Running NO LOCK ...")
    val_none, t_none = run_strategy("NO LOCK     ", worker_no_lock)

    print("\nRunning PESSIMISTIC LOCK ...")
    val_pess, t_pess = run_strategy("PESSIMISTIC ", worker_pessimistic)

    print("\nRunning OPTIMISTIC LOCK ...")
    val_opt, t_opt = run_strategy("OPTIMISTIC  ", worker_optimistic)

    print()
    print("  SUMMARY")
    header = (
        f"  {'Strategy':<20}  {'Result':>8}  {'Expected':>8}  {'Lost':>8}  {'Time':>8}"
    )
    print(header)

    for label, val, t in [
        ("No Lock", val_none, t_none),
        ("Pessimistic", val_pess, t_pess),
        ("Optimistic", val_opt, t_opt),
    ]:
        lost = expected - val
        print(f"  {label:<20}  {val:>8,}  {expected:>8,}  {lost:>8,}  {t:>7.3f}s")


if __name__ == "__main__":
    main()
