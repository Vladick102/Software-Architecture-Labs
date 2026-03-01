import hazelcast
import sys
import time


CLUSTER_MEMBERS = ["localhost:5701", "localhost:5702", "localhost:5703"]
MAP_NAME = "capitals"
ENTRY_COUNT = 1000


def get_client():
    return hazelcast.HazelcastClient(
        cluster_name="dev",
        cluster_members=CLUSTER_MEMBERS,
        connection_timeout=10.0,
    )


def write_entries(hz_map, count: int):
    print(f"\n--- Writing {count} entries to map '{MAP_NAME}' ---")
    hz_map.clear()
    start = time.time()
    for i in range(count):
        hz_map.put(str(i), f"value_{i}")
    elapsed = time.time() - start
    print(f"    Written {count} entries in {elapsed:.3f}s")


def read_and_verify(hz_map, count: int):
    print(f"\n--- Reading and verifying {count} entries ---")
    start = time.time()
    missing = []
    for i in range(count):
        val = hz_map.get(str(i))
        if val is None:
            missing.append(i)
        elif val != f"value_{i}":
            print(f"    MISMATCH key={i}: expected value_{i}, got {val}")
    elapsed = time.time() - start

    found = count - len(missing)
    print(f"    Found    : {found}/{count}")
    print(f"    Missing  : {len(missing)}")
    if missing:
        print(f"    Missing keys (first 20): {missing[:20]}")
    print(f"    Read time: {elapsed:.3f}s")
    return len(missing)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    print("  TASK 3: Distributed Map Demo")

    client = get_client()
    hz_map = client.get_map(MAP_NAME).blocking()

    if mode in ("write", "both"):
        write_entries(hz_map, ENTRY_COUNT)

    if mode in ("verify", "both"):
        missing = read_and_verify(hz_map, ENTRY_COUNT)
        if missing == 0:
            print("\n  All entries intact. No data loss.")
        else:
            print(f"\n  DATA LOSS: {missing} entries are missing!")

    client.shutdown()


if __name__ == "__main__":
    main()
