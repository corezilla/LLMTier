from __future__ import annotations

import json
import mimetypes
import re
import traceback
import uuid
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .admin import AdminService
from .account_usage import AccountUsageService
from .audit import AuditLog
from .auth import authenticate, unauthenticated_principal
from .embeddings import EmbeddingsService
from .errors import ApiError
from .health import health_view, readiness_view
from .logs import OperationalLog
from .models import ModelCatalog
from .registry import Registry
from .responses import ResponsesService
from .routing import Router
from .sse import response_stream
from .store import Store
from .usage import UsageRecorder


class Application:
    def __init__(self, database: str, settings: str | None):
        self.store = Store(database); self.store.migrate()
        self.registry = Registry(self.store); self.bootstrap_error: ApiError | None = None
        try:
            self.registry.bootstrap_settings(settings); self.registry.ensure_fixed_tiers()
        except ApiError as exc:
            self.bootstrap_error = exc
        self.router = Router(self.registry); self.usage = UsageRecorder(self.store)
        self.account_usage = AccountUsageService(self.store)
        self.audit = AuditLog(self.store); self.logs = OperationalLog(self.store)
        self.models = ModelCatalog(self.registry)
        self.responses = ResponsesService(self.registry, self.router, self.usage)
        self.embeddings = EmbeddingsService(self.registry, self.router, self.usage)
        self.admin = AdminService(self.registry, self.audit, self.logs, self.usage)


def handler_factory(app: Application):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LLMTier/0.3"

        def log_message(self, format, *args):
            app.logs.record("info", "http", "request", format % args, getattr(self, "request_id", None))

        def _json(self, status: int, data, headers: dict[str, str] | None = None):
            raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Request-ID", self.request_id)
            for key, value in (headers or {}).items(): self.send_header(key, value)
            self.end_headers(); self.wfile.write(raw)

        def _body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000: raise ApiError(413, "request_too_large", "Request body is too large")
            try: return json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as exc: raise ApiError(400, "invalid_json", "Request body is not valid JSON") from exc

        def _static(self, path: str):
            root = Path(__file__).with_name("webui")
            name = "index.html" if path in {"/", "/ui", "/ui/"} else path.removeprefix("/ui/")
            target = (root / name).resolve()
            if root.resolve() not in target.parents and target != root.resolve(): raise ApiError(404, "not_found", "Not found")
            if not target.is_file(): raise ApiError(404, "not_found", "Not found")
            raw = target.read_bytes(); self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store"); self.send_header("Last-Modified", formatdate(target.stat().st_mtime, usegmt=True))
            self.end_headers(); self.wfile.write(raw)

        def _auth(self, role="data"):
            principal = unauthenticated_principal(self.client_address[0], self.headers, role)
            if principal is not None:
                return principal
            return authenticate(self.headers, role)

        def _dispatch(self):
            parsed = urlparse(self.path); path, query = parsed.path, parse_qs(parsed.query)
            method = self.command
            if path == "/healthz" and method == "GET": return self._json(200, health_view(__version__))
            if path == "/readyz" and method == "GET":
                if app.bootstrap_error: return self._json(503, {"status": "not_ready", "models": []})
                data, status = readiness_view(app.registry); return self._json(status, data)
            if path in {"/", "/ui", "/ui/"} or path.startswith("/ui/"): return self._static(path)
            if app.bootstrap_error: raise app.bootstrap_error
            if path == "/v1/models" and method == "GET": self._auth(); return self._json(200, app.models.list())
            match = re.fullmatch(r"/v1/models/([^/]+)", path)
            if match and method == "GET": self._auth(); return self._json(200, app.models.get(match.group(1)))
            if path == "/v1/responses" and method == "POST":
                principal = self._auth(); response = app.responses.create(principal.principal_id, self.request_id, self._body())
                self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.send_header("X-Request-ID", self.request_id); self.end_headers()
                for chunk in response_stream(response): self.wfile.write(chunk); self.wfile.flush()
                return
            if path == "/v1/embeddings" and method == "POST":
                principal = self._auth(); return self._json(200, app.embeddings.create(principal.principal_id, self.request_id, self._body()))
            if path == "/tier/v1/usage" and method == "GET":
                principal = self._auth(); return self._json(200, app.usage.page(principal.principal_id, query.get("cursor", [None])[0], int(query.get("limit", [100])[0]), since=query.get("from", [None])[0], until=query.get("to", [None])[0], model=query.get("model", [None])[0], request_id=query.get("request_id", [None])[0]))
            principal = self._auth("admin")
            if path == "/tier/admin/v1/providers":
                if method == "GET": return self._json(200, app.admin.page(app.registry.list_providers(), principal.principal_id, "providers", query.get("cursor", [None])[0], int(query.get("limit", [100])[0])))
                if method == "POST":
                    view, etag = app.admin.mutate(principal.principal_id, "provider.create", "provider", self.request_id, lambda: app.registry.create_provider(self._body()))
                    return self._json(201, view, {"ETag": etag})
            if path == "/tier/admin/v1/deployments":
                if method == "GET": return self._json(200, app.admin.page(app.registry.list_deployments(), principal.principal_id, "deployments", query.get("cursor", [None])[0], int(query.get("limit", [100])[0])))
                if method == "POST":
                    view, etag = app.admin.mutate(principal.principal_id, "deployment.create", "deployment", self.request_id, lambda: app.registry.create_deployment(self._body()))
                    return self._json(201, view, {"ETag": etag})
            if path == "/tier/admin/v1/service-levels":
                if method == "GET": return self._json(200, app.admin.page(app.registry.list_service_levels(), principal.principal_id, "service-levels", query.get("cursor", [None])[0], int(query.get("limit", [100])[0])))
                if method == "POST":
                    view, etag = app.admin.mutate(principal.principal_id, "service_level.create", "service_level", self.request_id, lambda: app.registry.create_service_level(self._body()))
                    return self._json(201, view, {"ETag": etag})
            if path == "/tier/admin/v1/runtime" and method == "GET":
                return self._json(200, app.router.snapshot())
            match = re.fullmatch(r"/tier/admin/v1/stats", path)
            if match and method == "GET":
                since, until = query.get("from", [None])[0], query.get("to", [None])[0]
                if not since or not until: raise ApiError(400, "invalid_request", "from and to are required")
                group_by = (query.get("group_by", ["tier"])[0] or "tier").lower()
                return self._json(200, app.admin.stats(since, until, group_by))
            match = re.fullmatch(r"/tier/admin/v1/providers/([^/]+)/usage", path)
            if match:
                provider_id = match.group(1)
                if method == "GET": return self._json(200, app.account_usage.latest(provider_id))
                if method == "POST":
                    body = self._body()
                    if set(body) != {"confirm_external_call"}: raise ApiError(400, "invalid_request", "Usage refresh accepts only confirm_external_call")
                    result = app.admin.mutate(principal.principal_id, "provider.usage.refresh", provider_id, self.request_id, lambda: app.account_usage.refresh(provider_id, body.get("confirm_external_call") is True))
                    return self._json(200, result)
            match = re.fullmatch(r"/tier/admin/v1/providers/([^/]+)/models", path)
            if match:
                provider_id = match.group(1)
                if method == "GET":
                    models = app.admin.list_provider_models(provider_id)
                    return self._json(200, {"data": models})
            for kind, plural, getter, updater, deleter in (
                ("provider", "providers", app.registry.get_provider, app.registry.update_provider, app.registry.delete_provider),
                ("deployment", "deployments", app.registry.get_deployment, app.registry.update_deployment, app.registry.delete_deployment),
                ("service_level", "service-levels", app.registry.get_service_level, app.registry.update_service_level, app.registry.delete_service_level),
            ):
                match = re.fullmatch(fr"/tier/admin/v1/{plural}/([^/]+)", path)
                if match:
                    rid = match.group(1)
                    if method == "GET": view, etag = getter(rid); return self._json(200, view, {"ETag": etag})
                    if method == "PATCH":
                        view, etag = app.admin.mutate(principal.principal_id, f"{kind}.update", rid, self.request_id, lambda: updater(rid, self._body(), self.headers.get("If-Match")))
                        return self._json(200, view, {"ETag": etag})
                    if method == "DELETE":
                        app.admin.mutate(principal.principal_id, f"{kind}.delete", rid, self.request_id, lambda: deleter(rid, self.headers.get("If-Match")))
                        self.send_response(204); self.end_headers(); return
            if path == "/tier/admin/v1/probes" and method == "POST": return self._json(200, app.admin.probe(principal.principal_id, self._body(), self.request_id))
            if path == "/tier/admin/v1/usage" and method == "GET": return self._json(200, app.usage.page(principal.principal_id, query.get("cursor", [None])[0], int(query.get("limit", [100])[0]), admin=True, since=query.get("from", [None])[0], until=query.get("to", [None])[0]))
            if path == "/tier/admin/v1/audit" and method == "GET": return self._json(200, app.audit.page(int(query.get("limit", [50])[0])))
            if path == "/tier/admin/v1/logs" and method == "GET":
                since, until = query.get("from", [None])[0], query.get("to", [None])[0]
                if not since or not until: raise ApiError(400, "invalid_request", "from and to are required")
                return self._json(200, app.logs.page(int(query.get("limit", [100])[0]), query.get("level", [None])[0], query.get("module", [None])[0], query.get("request_id", [None])[0], since, until))
            raise ApiError(404, "not_found", "Endpoint not found")

        def _run(self):
            self.request_id = f"req_{uuid.uuid4().hex}"
            try:
                try: self._dispatch()
                except ApiError as exc: self._json(exc.status, exc.envelope(), exc.headers)
                except (BrokenPipeError, ConnectionResetError): pass
                except Exception:
                    app.logs.record("error", "http", "unhandled_error", traceback.format_exc(limit=1), self.request_id)
                    self._json(500, ApiError(500, "internal_error", "Internal server error").envelope())
            finally:
                # ThreadingHTTPServer spawns a fresh thread per request.
                # BaseHTTPRequestHandler.finish() closes rfile/wfile, but
                # does not touch the per-thread SQLite connection cached in
                # Store._local. Without this close, each request leaks the
                # db + wal + shm fds (~3) until Python's deferred
                # thread-local cleanup eventually runs, which exhausts the
                # default 256-fd macOS ulimit within minutes of modest traffic.
                try: app.store.close()
                except Exception: pass

        do_GET = _run; do_POST = _run; do_PATCH = _run; do_DELETE = _run
    return Handler


def serve(host: str, port: int, database: str, settings: str | None = None):
    app = Application(database, settings)
    server = ThreadingHTTPServer((host, port), handler_factory(app))
    print(f"LLMTier 0.3 listening on http://{host}:{port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); app.store.close()
