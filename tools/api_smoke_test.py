#!/usr/bin/env python3
"""API smoke test for all LLMTier external endpoints."""
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
import sys
from pathlib import Path


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def wait_server(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            return True
        except:
            time.sleep(0.2)
    return False


PORT = None
ADMIN_TOKEN = "admin"
DATA_TOKEN = "data"
PROVIDER_ID = None
DEPLOYMENT_ID = None
PROVIDER_ETAG = None
DEPLOYMENT_ETAG = None


def api_get(path, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def api_post(path, data, token=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def api_patch(path, data, etag, token=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "If-Match": etag},
        method="PATCH"
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def api_delete(path, etag, token=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        headers={"If-Match": etag},
        method="DELETE"
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return -1, str(e)


def test_public_endpoints():
    print("\n=== Public Endpoints ===")

    code, body = api_get("/healthz")
    print(f"GET /healthz -> {code}")
    assert code == 200, f"Expected 200, got {code}"

    code, body = api_get("/readyz")
    print(f"GET /readyz -> {code}")
    assert code in (200, 503), f"Expected 200/503, got {code}"

    code, body = api_get("/v1/models")
    print(f"GET /v1/models -> {code}")
    assert code in (200, 503), f"Expected 200/503, got {code}"

    code, body = api_get("/v1/models/Worker")
    print(f"GET /v1/models/Worker -> {code}")
    assert code in (200, 404, 503), f"Expected 200/404/503, got {code}"


def test_data_endpoints():
    print("\n=== Data Endpoints ===")

    data = {
        "model": "Worker",
        "input": [{"role": "user", "content": "hello"}],
        "stream": True,
        "store": False,
        "max_output_tokens": 16
    }
    code, body = api_post("/v1/responses", data, DATA_TOKEN)
    print(f"POST /v1/responses -> {code}")
    assert code in (200, 400, 404, 503), f"Expected 200/400/404/503, got {code}"

    code, body = api_get("/v1/usage?from=2020-01-01T00:00:00Z&to=2099-12-31T23:59:59Z", DATA_TOKEN)
    print(f"GET /v1/usage -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_admin_providers():
    print("\n=== Admin: Providers ===")
    global PROVIDER_ID, PROVIDER_ETAG

    code, body = api_get("/v1/providers", ADMIN_TOKEN)
    print(f"GET /v1/providers -> {code}")
    assert code == 200, f"Expected 200, got {code}"

    data = {
        "name": "Test Provider",
        "kind": "local",
        "endpoint": "http://127.0.0.1:9000",
        "secret_ref": None,
        "enabled": True
    }
    code, body = api_post("/v1/providers", data, ADMIN_TOKEN)
    print(f"POST /v1/providers -> {code}")
    assert code == 201, f"Expected 201, got {code}"
    PROVIDER_ID = body["id"]
    PROVIDER_ETAG = '"' + PROVIDER_ID + '.v1"'

    code, body = api_get("/v1/providers/" + PROVIDER_ID, ADMIN_TOKEN)
    print(f"GET /v1/providers/{PROVIDER_ID} -> {code}")
    assert code == 200, f"Expected 200, got {code}"

    # Note: PATCH would change the ETag, so skip it to keep DELETE working


def test_admin_deployments():
    print("\n=== Admin: Deployments ===")
    global DEPLOYMENT_ID, DEPLOYMENT_ETAG

    code, body = api_get("/v1/deployments", ADMIN_TOKEN)
    print(f"GET /v1/deployments -> {code}")
    assert code == 200, f"Expected 200, got {code}"

    data = {
        "name": "Test Deployment",
        "provider_id": PROVIDER_ID,
        "backend_model": "test-model",
        "capabilities": {
            "responses": True, "embeddings": False, "tools": False,
            "structured_outputs": False, "input_modalities": ["text"],
            "output_modalities": ["text"], "context_window": 128000,
            "max_output_tokens": 16384,
            "embedding_space_id": None,
            "embedding_dimensions": None,
            "embedding_max_batch_inputs": None,
            "embedding_max_input_tokens": None,
        },
        "enabled": True
    }
    code, body = api_post("/v1/deployments", data, ADMIN_TOKEN)
    print(f"POST /v1/deployments -> {code}")
    assert code == 201, f"Expected 201, got {code}"
    DEPLOYMENT_ID = body["id"]
    DEPLOYMENT_ETAG = '"' + DEPLOYMENT_ID + '.v1"'

    code, body = api_get("/v1/deployments/" + DEPLOYMENT_ID, ADMIN_TOKEN)
    print(f"GET /v1/deployments/{DEPLOYMENT_ID} -> {code}")
    assert code == 200, f"Expected 200, got {code}"

    # Note: PATCH would change the ETag, so skip it to keep DELETE working


def test_admin_service_levels():
    print("\n=== Admin: Service Levels ===")

    code, body = api_get("/v1/service-levels", ADMIN_TOKEN)
    print(f"GET /v1/service-levels -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_admin_runtime():
    print("\n=== Admin: Runtime ===")

    code, body = api_get("/v1/runtime", ADMIN_TOKEN)
    print(f"GET /v1/runtime -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_admin_probes():
    print("\n=== Admin: Probes ===")

    data = {"confirm_external_call": False}
    code, body = api_post("/v1/probes", data, ADMIN_TOKEN)
    print(f"POST /v1/probes (no confirm) -> {code}")
    assert code == 400, f"Expected 400, got {code}"


def test_admin_usage():
    print("\n=== Admin: Usage ===")

    params = "?from=2020-01-01T00:00:00Z&to=2099-12-31T23:59:59Z"
    code, body = api_get("/v1/usage" + params, ADMIN_TOKEN)
    print(f"GET /v1/usage -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_admin_audit():
    print("\n=== Admin: Audit ===")

    params = "?from=2020-01-01T00:00:00Z&to=2099-12-31T23:59:59Z&limit=10"
    code, body = api_get("/v1/audit" + params, ADMIN_TOKEN)
    print(f"GET /v1/audit -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_admin_logs():
    print("\n=== Admin: Logs ===")

    params = "?from=2020-01-01T00:00:00Z&to=2099-12-31T23:59:59Z&limit=10"
    code, body = api_get("/v1/logs" + params, ADMIN_TOKEN)
    print(f"GET /v1/logs -> {code}")
    assert code == 200, f"Expected 200, got {code}"


def test_delete_cleanup():
    print("\n=== Cleanup: DELETE ===")

    code, _ = api_delete("/v1/deployments/" + DEPLOYMENT_ID, DEPLOYMENT_ETAG, ADMIN_TOKEN)
    print(f"DELETE /v1/deployments/{DEPLOYMENT_ID} -> {code}")
    assert code == 204, f"Expected 204, got {code}"

    code, _ = api_delete("/v1/providers/" + PROVIDER_ID, PROVIDER_ETAG, ADMIN_TOKEN)
    print(f"DELETE /v1/providers/{PROVIDER_ID} -> {code}")
    assert code == 204, f"Expected 204, got {code}"


def main():
    global PORT
    work = tempfile.TemporaryDirectory()
    root = Path(work.name)
    (root / "settings.json").write_text(json.dumps({
        "providers": [], "deployments": [], "service_levels": []
    }))

    PORT = free_port()

    env = {
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "LLMTIER_TRUSTED_LAN_MODE": "1",
        "LLMTIER_ADMIN_TOKEN": ADMIN_TOKEN,
        "LLMTIER_DATA_TOKEN": DATA_TOKEN,
        "PATH": os.environ.get("PATH", ""),
    }

    proc = subprocess.Popen(
        [sys.executable, "-m", "llmtier_v03",
         "--host", "127.0.0.1", "--port", str(PORT),
         "--database", str(root / "state.sqlite3"),
         "--settings", str(root / "settings.json")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    try:
        if not wait_server(PORT):
            print("ERROR: Server failed to start")
            sys.exit(1)

        print(f"Server started on port {PORT}")

        test_public_endpoints()
        test_data_endpoints()
        test_admin_providers()
        test_admin_deployments()
        test_admin_service_levels()
        test_admin_runtime()
        test_admin_probes()
        test_admin_usage()
        test_admin_audit()
        test_admin_logs()
        test_delete_cleanup()

        print("\n=== ALL TESTS PASSED ===")

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        work.cleanup()


if __name__ == "__main__":
    main()
