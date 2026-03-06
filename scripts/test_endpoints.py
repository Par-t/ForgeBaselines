#!/usr/bin/env python3
"""
Test script for ForgeBaselines endpoints.
Uses Firebase Admin SDK to mint a custom token for a test UID,
then exchanges it for an ID token via the REST API.

Usage:
    python scripts/test_endpoints.py
    python scripts/test_endpoints.py <experiment_id>
"""

import sys
import json
import urllib.request
import urllib.parse
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")

# --- Parse .env (handles multi-line FIREBASE_SERVICE_ACCOUNT_JSON) ---
def parse_env(path):
    env = {}
    with open(path) as f:
        content = f.read()

    # Extract FIREBASE_SERVICE_ACCOUNT_JSON block (multi-line JSON in single quotes)
    sa_match = re.search(r"FIREBASE_SERVICE_ACCOUNT_JSON='(\{.*?\})'", content, re.DOTALL)
    if sa_match:
        env["FIREBASE_SERVICE_ACCOUNT_JSON"] = sa_match.group(1)

    # Parse simple KEY=VALUE lines
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("FIREBASE_SERVICE_ACCOUNT_JSON"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env

env = parse_env(ENV_FILE)

API_KEY = env.get("NEXT_PUBLIC_FIREBASE_API_KEY", "").strip()
SA_JSON = env.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
BASE_URL = env.get("BASE_URL", "http://localhost:8000")
TEST_UID = "test-script-user"  # synthetic UID for testing

# --- Mint custom token via Admin SDK ---
try:
    import firebase_admin
    from firebase_admin import auth, credentials
except ImportError:
    print("Installing firebase-admin...")
    os.system(f"{sys.executable} -m pip install firebase-admin -q")
    import firebase_admin
    from firebase_admin import auth, credentials

if not firebase_admin._apps:
    sa_dict = json.loads(SA_JSON)
    cred = credentials.Certificate(sa_dict)
    firebase_admin.initialize_app(cred)

print(f"==> Minting custom token for UID: {TEST_UID}")
custom_token = auth.create_custom_token(TEST_UID).decode("utf-8")

# --- Exchange custom token for ID token ---
def post_json(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

exchange_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
resp = post_json(exchange_url, {"token": custom_token, "returnSecureToken": True})
id_token = resp["idToken"]
print("Token acquired.\n")

# --- Hit endpoints ---
def get_endpoint(path):
    url = f"{BASE_URL}{path}"
    print(f"==> GET {url}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {id_token}"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            print(json.dumps(data, indent=2))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
    print()

get_endpoint("/experiments/all")

if len(sys.argv) > 1:
    exp_id = sys.argv[1]
    get_endpoint(f"/experiments/{exp_id}/status")
    get_endpoint(f"/experiments/{exp_id}/results")
