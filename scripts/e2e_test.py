#!/usr/bin/env python3
"""
End-to-end test script for ForgeBaselines.
Tests full flow: upload → run experiment → poll status → fetch results.
Covers both classification and IR pipelines.

Usage:
    python scripts/e2e_test.py                    # run both pipelines
    python scripts/e2e_test.py classification     # classification only
    python scripts/e2e_test.py ir                 # IR only
"""

import sys
import json
import time
import os
import re
import io
import urllib.request
import urllib.error

# ── Config ─────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
POLL_INTERVAL = 3   # seconds between status polls
POLL_TIMEOUT = 300  # seconds before giving up

# ── Minimal test data (inline) ──────────────────────────────────────────────
CLASSIFICATION_CSV = """\
text,label
"the movie was fantastic and thrilling",positive
"absolutely loved every moment of it",positive
"great acting and wonderful story",positive
"one of the best films I have seen",positive
"outstanding performance by the cast",positive
"terrible film, complete waste of time",negative
"boring and predictable plot",negative
"poorly written and badly directed",negative
"I hated every minute of this movie",negative
"awful experience, do not recommend",negative
"it was okay, nothing special",neutral
"average at best, could be better",neutral
"not great but not terrible either",neutral
"somewhere in the middle, meh",neutral
"decent but forgettable",neutral
"""

CORPUS_CSV = """\
doc_id,text
d1,"Python is a high-level programming language known for simplicity"
d2,"Machine learning uses algorithms to learn patterns from data"
d3,"Natural language processing helps computers understand text"
d4,"Deep learning is a subset of machine learning using neural networks"
d5,"Information retrieval finds relevant documents from a collection"
d6,"FastAPI is a modern Python web framework for building APIs"
d7,"Docker containers package applications with their dependencies"
d8,"Pandas is a data analysis library for Python"
d9,"Transformers are neural network architectures used in NLP tasks"
d10,"BM25 is a ranking function used in information retrieval"
"""

QUERIES_CSV = """\
query,doc_id
"what is machine learning",d2
"Python programming language features",d1
"how do neural networks work",d4
"information retrieval ranking",d10
"NLP and text understanding",d3
"""

# ── Env parsing ─────────────────────────────────────────────────────────────
def parse_env(path):
    env = {}
    with open(path) as f:
        content = f.read()
    sa_match = re.search(r"FIREBASE_SERVICE_ACCOUNT_JSON='(\{.*?\})'", content, re.DOTALL)
    if sa_match:
        env["FIREBASE_SERVICE_ACCOUNT_JSON"] = sa_match.group(1)
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("FIREBASE_SERVICE_ACCOUNT_JSON"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env

# ── Firebase auth ────────────────────────────────────────────────────────────
def get_id_token(env):
    try:
        import firebase_admin
        from firebase_admin import auth, credentials
    except ImportError:
        print("Installing firebase-admin...")
        os.system(f"{sys.executable} -m pip install firebase-admin -q")
        import firebase_admin
        from firebase_admin import auth, credentials

    if not firebase_admin._apps:
        sa_dict = json.loads(env["FIREBASE_SERVICE_ACCOUNT_JSON"])
        cred = credentials.Certificate(sa_dict)
        firebase_admin.initialize_app(cred)

    custom_token = auth.create_custom_token("e2e-test-user").decode("utf-8")
    api_key = env.get("NEXT_PUBLIC_FIREBASE_API_KEY", "").strip()
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
    body = json.dumps({"token": custom_token, "returnSecureToken": True}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["idToken"]

# ── HTTP helpers ─────────────────────────────────────────────────────────────
def api_get(path, token):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {path} → HTTP {e.code}: {e.read().decode()}")

def api_post_json(path, payload, token):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"POST {path} → HTTP {e.code}: {e.read().decode()}")

def api_upload_csv(path, csv_content, filename, token):
    """Multipart form upload."""
    boundary = "----ForgeTestBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{csv_content}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"POST {path} (upload) → HTTP {e.code}: {e.read().decode()}")

def poll_status(experiment_id, token, label=""):
    """Poll /experiments/{id}/status until done or error. Returns final status dict."""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        s = api_get(f"/experiments/{experiment_id}/status", token)
        pct = s.get("pct", "?")
        stage = s.get("stage", "?")
        msg = s.get("message", "")
        print(f"  [{label}] {stage} {pct}% — {msg}")
        if s.get("status") in ("completed", "done") or stage == "done":
            return s
        if s.get("status") == "error":
            raise RuntimeError(f"Experiment failed: {s}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Experiment {experiment_id} did not complete within {POLL_TIMEOUT}s")

# ── Tests ────────────────────────────────────────────────────────────────────
def test_classification(token):
    print("\n" + "="*60)
    print("CLASSIFICATION PIPELINE")
    print("="*60)

    print("\n[1] Uploading dataset...")
    resp = api_upload_csv("/datasets/upload", CLASSIFICATION_CSV, "test_classification.csv", token)
    dataset_id = resp["dataset_id"]
    print(f"    dataset_id={dataset_id}  rows={resp['rows']}  cols={resp['cols']}")

    print("\n[2] Starting experiment (logistic_regression, random_forest)...")
    resp = api_post_json("/experiments/run", {
        "dataset_id": dataset_id,
        "target_column": "label",
        "model_names": ["logistic_regression", "random_forest"],
        "text_column": "text",
    }, token)
    exp_id = resp["experiment_id"]
    print(f"    experiment_id={exp_id}")

    print("\n[3] Polling status...")
    poll_status(exp_id, token, "classification")

    print("\n[4] Fetching results...")
    results = api_get(f"/experiments/{exp_id}/results", token)
    print(f"    task_type={results.get('task_type')}")
    for entry in results.get("leaderboard", []):
        print(f"    {entry.get('model_name')}: accuracy={entry.get('accuracy', entry.get('metrics', {}).get('accuracy', '?'))}")

    print("\n[5] Verifying in /experiments/all...")
    all_exp = api_get("/experiments/all", token)
    ids = [e["experiment_id"] for e in all_exp.get("experiments", [])]
    assert exp_id in ids, f"experiment {exp_id} not found in /all"
    print(f"    Found in unified list. Total experiments: {len(ids)}")

    print("\nCLASSIFICATION: PASSED")
    return exp_id

def test_ir(token):
    print("\n" + "="*60)
    print("IR PIPELINE")
    print("="*60)

    print("\n[1] Uploading corpus dataset...")
    corp_resp = api_upload_csv("/datasets/upload", CORPUS_CSV, "test_corpus.csv", token)
    corpus_id = corp_resp["dataset_id"]
    print(f"    corpus_id={corpus_id}")

    print("\n[2] Uploading queries dataset...")
    q_resp = api_upload_csv("/datasets/upload", QUERIES_CSV, "test_queries.csv", token)
    queries_id = q_resp["dataset_id"]
    print(f"    queries_id={queries_id}")

    print("\n[3] Starting IR experiment...")
    resp = api_post_json("/experiments/ir/run", {
        "corpus_dataset_id": corpus_id,
        "queries_dataset_id": queries_id,
        "corpus_doc_id_col": "doc_id",
        "text_column": "text",
        "queries_query_col": "query",
        "queries_doc_id_col": "doc_id",
    }, token)
    exp_id = resp["experiment_id"]
    print(f"    experiment_id={exp_id}")

    print("\n[4] Polling status...")
    poll_status(exp_id, token, "ir")

    print("\n[5] Fetching results...")
    results = api_get(f"/experiments/{exp_id}/results", token)
    print(f"    task_type={results.get('task_type')}")
    print(f"    n_docs={results.get('n_docs')}  n_queries={results.get('n_queries')}")
    for k, v in results.get("metrics", {}).items():
        print(f"    {k}={v:.4f}" if isinstance(v, float) else f"    {k}={v}")

    print("\n[6] Verifying in /experiments/all...")
    all_exp = api_get("/experiments/all", token)
    ids = [e["experiment_id"] for e in all_exp.get("experiments", [])]
    assert exp_id in ids, f"experiment {exp_id} not found in /all"
    print(f"    Found in unified list. Total experiments: {len(ids)}")

    print("\nIR: PASSED")
    return exp_id

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode not in ("classification", "ir", "both"):
        print(f"Unknown mode: {mode}. Use: classification | ir | both")
        sys.exit(1)

    env = parse_env(ENV_FILE)

    print("==> Authenticating with Firebase...")
    token = get_id_token(env)
    print("    Token acquired.")

    passed = []
    failed = []

    if mode in ("classification", "both"):
        try:
            test_classification(token)
            passed.append("classification")
        except Exception as e:
            print(f"\nCLASSIFICATION FAILED: {e}")
            failed.append("classification")

    if mode in ("ir", "both"):
        try:
            test_ir(token)
            passed.append("ir")
        except Exception as e:
            print(f"\nIR FAILED: {e}")
            failed.append("ir")

    print("\n" + "="*60)
    print(f"Results: {len(passed)} passed, {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("All tests passed.")

if __name__ == "__main__":
    main()
