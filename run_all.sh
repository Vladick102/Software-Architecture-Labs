#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="python3"

echo "Installing Python dependencies..."
"$PYTHON" -m pip install -r requirements.txt -q

docker compose up -d
echo "Waiting 25s for cluster to form..."
sleep 25

echo ""
echo "Task 3: Distributed Map (1000 entries)"
"$PYTHON" src/task3_distributed_map.py

echo ""
echo "Task 4: No-Lock Increment (3 clients × 10K iterations)"
"$PYTHON" src/task4_no_lock.py

echo ""
echo "Task 5: Pessimistic Lock Increment"
"$PYTHON" src/task5_pessimistic_lock.py

echo ""
echo "Task 6: Optimistic Lock Increment"
"$PYTHON" src/task6_optimistic_lock.py

echo ""
echo "Task 7: Lock Strategy Comparison"
"$PYTHON" src/task7_compare_locks.py

echo ""
echo "Task 8: Bounded Queue (1 producer, 2 consumers)"
"$PYTHON" src/task8_bounded_queue.py

echo ""
echo "All tasks completed."
