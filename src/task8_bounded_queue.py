import hazelcast
import multiprocessing
import time

CLUSTER_MEMBERS = ["localhost:5701", "localhost:5702", "localhost:5703"]
QUEUE_NAME = "bounded-queue"
NUM_MESSAGES = 100


def producer(result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_queue = client.get_queue(QUEUE_NAME).blocking()

    start = time.time()
    for i in range(1, NUM_MESSAGES + 1):
        hz_queue.put(i)
    elapsed = time.time() - start
    result_queue.put(("producer", NUM_MESSAGES, elapsed))
    client.shutdown()


def consumer(consumer_id: int, result_queue: multiprocessing.Queue):
    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_queue = client.get_queue(QUEUE_NAME).blocking()

    received = []
    start = time.time()
    while True:
        msg = hz_queue.poll(timeout=3)
        if msg is None:
            break
        received.append(msg)

    elapsed = time.time() - start
    print(
        f"  [Consumer {consumer_id}] Received {len(received)} messages in {elapsed:.3f}s  "
    )
    result_queue.put((f"consumer_{consumer_id}", len(received), elapsed))
    client.shutdown()


def demo_full_queue_no_consumer():
    print("\n--- Demo: full queue with NO consumer ---")
    print("  Queue max-size=10. Trying to offer() 15 items without a consumer.")

    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    hz_queue = client.get_queue(QUEUE_NAME).blocking()
    hz_queue.clear()

    accepted = 0
    rejected = 0
    for i in range(1, 16):
        ok = hz_queue.offer(i, timeout=0)
        if ok:
            accepted += 1
        else:
            rejected += 1

    print(f"  offer() accepted: {accepted}")
    print(f"  offer() rejected: {rejected}")
    hz_queue.clear()
    client.shutdown()


def main():
    print("  TASK 8: Bounded Queue Demo  (capacity = 10)")

    demo_full_queue_no_consumer()

    print()
    print("--- Starting 1 producer + 2 consumers ---")
    print(f"  Queue: '{QUEUE_NAME}' (max-size=10)")
    print(f"  Messages to send: {NUM_MESSAGES}")
    print()

    client = hazelcast.HazelcastClient(
        cluster_name="dev", cluster_members=CLUSTER_MEMBERS, connection_timeout=10.0
    )
    client.get_queue(QUEUE_NAME).blocking().clear()
    client.shutdown()

    rq = multiprocessing.Queue()

    procs = [
        multiprocessing.Process(target=consumer, args=(1, rq)),
        multiprocessing.Process(target=consumer, args=(2, rq)),
        multiprocessing.Process(target=producer, args=(rq,)),
    ]

    wall_start = time.time()
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    wall_elapsed = time.time() - wall_start

    results = {}
    while not rq.empty():
        role, count, elapsed = rq.get()
        results[role] = (count, elapsed)

    print()
    print("  SUMMARY")
    total_received = 0
    for role, (count, elapsed) in sorted(results.items()):
        print(f"  {role:<12}  messages={count:>4}  time={elapsed:.3f}s")
        if role.startswith("consumer"):
            total_received += count

    print(f"\n  Total produced : {NUM_MESSAGES}")
    print(f"  Total consumed : {total_received}")
    print(f"  Wall-clock time: {wall_elapsed:.3f}s")
    print()
    if total_received == NUM_MESSAGES:
        print("  Every message was consumed exactly once.")
    else:
        print(f"  Mismatch: {NUM_MESSAGES - total_received} messages not consumed!")


if __name__ == "__main__":
    main()
