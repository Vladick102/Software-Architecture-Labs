# Microservices Basics Lab

This project demonstrates a simple microservices architecture with three services communicating via HTTP.

## Architecture

The system consists of three services:

- Facade Service (Port 8080) - Main entry point that coordinates requests between services
- Logging Service (Port 8081) - Handles logging of operations
- Counter Service (Port 8082) - Manages request counters

All services are containerized using Docker and orchestrated with Docker Compose.

## Running the Application

Start all services:
```bash
docker-compose up --build
```

Test the basic functionality:
```bash
python test_client.py
```

Optional test arguments:
- `--scenario {1|2}` - Run specific scenario (default: run both)
- `--clients N` - Number of concurrent clients (default: 10)
- `--t N` - Transactions per client (default: 10000)

Example:
```bash
python test_client.py --scenario 1 --clients 5 --t 5000
```

Stop all services:
```bash
docker-compose down
```

## Testing

### Basic Functionality
![Basic Functionality](screenshots/basic_functionality.png)

### Scenario 1
![Scenario 1](screenshots/scenario1.png)

### Scenario 2
![Scenario 2](screenshots/scenario2.png)
![Scenario 2 (with docker-compose down)](screenshots/scenario2_end.png)


## Analysis of the Results

### Scenario 1

The system successfully processed all 100 000 requests in 405.47 seconds, achieving a rate of 246.6 requests per second. The final balance for each of the 10 individual accounts was 10 000, exactly as we wanted. The total time on the facade service was 279 589.1 ms for the logging-service and 269 609.7 ms for the counter-service.

### Scenario 2

Processing the 100 000 requests took 420.69 seconds (it is the real outcome of the test, I swear), resulting in a slightly lower throughput of 237.7 requests per second. The final balance for the reached exactly 100 000, as intended. The time is 312 778.3 ms for the logging-service and 301 241.8 ms for the counter-service.

### Conclusion

Both scenarios executed without errors, demonstrating the basic reliability of the architecture. The slight decrease in requests per second (from 246.6 to 237.7) and the corresponding increase in processing times during Scenario 2 suggest minor contention or synchronization overhead when multiple concurrent clients attempt to update the exact same memory record in the counter-service. Additionally, across both scenarios, the logging-service consistently accounted for a slightly larger portion of the execution time compared to the counter-service.
