import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# Registration format: { "service_name": ["http://ip1:port", "http://ip2:port"] }
services = {}

@app.route("/register", methods=["POST"])
def register_service():
    data = request.get_json()
    service_name = data.get("service_name")
    address = data.get("address")
    
    if not service_name or not address:
        return jsonify({"error": "service_name and address required"}), 400
        
    if service_name not in services:
        services[service_name] = set()
        
    services[service_name].add(address)
    print(f"[config-server] Registered {service_name} at {address}")
    return jsonify({"status": "registered"}), 200

@app.route("/services/<service_name>", methods=["GET"])
def get_service(service_name):
    addresses = list(services.get(service_name, []))
    if not addresses:
        return jsonify({"error": f"No instances found for {service_name}"}), 404
        
    return jsonify({"addresses": addresses}), 200

@app.route("/all_services", methods=["GET"])
def all_services():
    res = {k: list(v) for k, v in services.items()}
    return jsonify(res), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8083)
