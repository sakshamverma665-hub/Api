from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
import secrets
import json
import os

app = Flask(__name__)

ORIGINAL_API = "https://sakshamxosintapi.onrender.com/get"

KEY_DURATION_DAYS = 30
KEYS_FILE = "keys.json"

# Admin password (to view all keys)
ADMIN_PASSWORD = "KT2411"

# Load existing keys
if os.path.exists(KEYS_FILE):
    with open(KEYS_FILE, "r") as f:
        API_KEYS = json.load(f)
        for key, info in API_KEYS.items():
            if info["activated_at"]:
                info["activated_at"] = datetime.fromisoformat(info["activated_at"])
            info["created_at"] = datetime.fromisoformat(info["created_at"])
else:
    API_KEYS = {}

# Save keys to file
def save_keys():
    temp_keys = {}
    for k, v in API_KEYS.items():
        temp_keys[k] = {
            "created_at": v["created_at"].isoformat(),
            "activated_at": v["activated_at"].isoformat() if v["activated_at"] else None,
            "duration_days": v["duration_days"]
        }
    with open(KEYS_FILE, "w") as f:
        json.dump(temp_keys, f)

# Generate secure random key
def generate_key():
    return secrets.token_urlsafe(16)

# Endpoint to generate new key
@app.route("/genkey2411", methods=["GET"])
def gen_key():
    new_key = generate_key()
    API_KEYS[new_key] = {
        "created_at": datetime.utcnow(),
        "activated_at": None,
        "duration_days": KEY_DURATION_DAYS
    }
    save_keys()
    return jsonify({
        "new_key": new_key,
        "duration_days": KEY_DURATION_DAYS
    })

# Endpoint to get data using key
@app.route("/get", methods=["GET"])
def get_data():
    api_key = request.args.get("key")
    num = request.args.get("num")

    if not api_key or api_key not in API_KEYS:
        return jsonify({"error": "Invalid or missing API key"}), 401

    key_info = API_KEYS[api_key]

    # Activate key on first use
    if key_info["activated_at"] is None:
        key_info["activated_at"] = datetime.utcnow()

    # Check expiry
    expiry = key_info["activated_at"] + timedelta(days=key_info["duration_days"])
    if datetime.utcnow() > expiry:
        return jsonify({"error": "API key expired"}), 401

    if not num:
        return jsonify({"error": "Missing 'num' parameter"}), 400

    try:
        response = requests.get(ORIGINAL_API, params={"num": num})
        response.raise_for_status()
        data = response.json()  # Return original JSON as-is
        save_keys()
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch data from original API", "details": str(e)}), 500

# Admin endpoint to view all keys
@app.route("/keys", methods=["GET"])
def view_keys():
    admin_pass = request.args.get("admin")
    if admin_pass != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    keys_info = {}
    for k, v in API_KEYS.items():
        activated = v["activated_at"].isoformat() if v["activated_at"] else None
        expiry = (v["activated_at"] + timedelta(days=v["duration_days"])).isoformat() if v["activated_at"] else None
        keys_info[k] = {
            "created_at": v["created_at"].isoformat(),
            "activated_at": activated,
            "expires_at": expiry,
            "duration_days": v["duration_days"]
        }

    return jsonify(keys_info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)