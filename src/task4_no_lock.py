import hazelcast
import multiprocessing
import time

CLUSTER_MEMBERS = ["localhost:5701", "localhost:5702", "localhost:5703"]
MAP_NAME = "lock-demo"
KEY = "counter"
ITERATIONS = 10_000
NUM_CLIENTS = 3


def worker(worker_id: int, result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev",
        cluster_members=CLUSTER_MEMBERS,
        connection_timeout=10.0,
    )
    hz_map = client.get_map(MAP_NAME).blocking()

    start = time.time()
    for _ in range(ITERATIONS):
        value = hz_map.get(KEY) or 0
        hz_map.put(KEY, value + 1)
    elapsed = time.time() - start

    print(f"  Worker {worker_id}: finished {ITERATIONS} iterations in {elapsed:.3f}s")
    result_queue.put(elapsed)
    client.shutdown()


def main():
    print("  TASK 4: Distributed Map WITHOUT Locks")
    print(f"  Clients  : {NUM_CLIENTS}")
    print(f"  Iterations each: {ITERATIONS:,}")
    print(f"  Expected result: {NUM_CLIENTS * ITERATIONS:,}")
    print()

    client = hazelcast.HazelcastClient(
        cluster_name="dev",
        cluster_members=CLUSTER_MEMBERS,
        connection_timeout=10.0,
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    hz_map.put(KEY, 0)
    client.shutdown()

    result_queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=worker, args=(i + 1, result_queue))
        for i in range(NUM_CLIENTS)
    ]

    wall_start = time.time()
    for p in processes:
        p.start()
    for p in processes:
        p.join()
    wall_elapsed = time.time() - wall_start

    client = hazelcast.HazelcastClient(
        cluster_name="dev",
        cluster_members=CLUSTER_MEMBERS,
        connection_timeout=10.0,
    )
    hz_map = client.get_map(MAP_NAME).blocking()
    final_value = hz_map.get(KEY)
    client.shutdown()

    expected = NUM_CLIENTS * ITERATIONS
    print()
    print(f"  Final counter value : {final_value:,}")
    print(f"  Expected value      : {expected:,}")
    lost = expected - final_value
    loss_pct = 100.0 * lost / expected
    print(f"  Lost increments     : {lost:,}  ({loss_pct:.1f}% data loss)")
    print(f"  Wall-clock time     : {wall_elapsed:.3f}s")
    print()
    if final_value < expected:
        print(
            "  RACE CONDITION CONFIRMED: values were overwritten by concurrent writes."
        )
    else:
        print("  (Unexpectedly no data loss - try again or increase iterations)")


if __name__ == "__main__":
    main()
