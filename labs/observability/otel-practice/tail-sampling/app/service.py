"""Small checkout service with manual SDK spans; every test request is logged, sampled or not."""
import contextvars
import hashlib
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind, Status, StatusCode

request_key = contextvars.ContextVar("request_key", default="manual")

class StableIdGenerator(IdGenerator):
    def generate_trace_id(self):
        return int.from_bytes(hashlib.sha256(request_key.get().encode()).digest()[:16], "big")

    def generate_span_id(self):
        return secrets.randbits(64) or 1

providers, tracers = {}, {}
for mode in ["head", "tail", "head-tail", "late-short", "late-long"]:
    port = 4318 if mode == "head" else 4338 if mode == "late-long" else 4328
    sampler = ParentBased(TraceIdRatioBased(0.25)) if mode in ("head", "head-tail") else ALWAYS_ON
    provider = TracerProvider(sampler=sampler, id_generator=StableIdGenerator(),
                              resource=Resource.create({"service.name": "checkout-" + mode}))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(
        endpoint=f"http://collector:{port}/v1/traces", timeout=10)))
    providers[mode], tracers[mode] = provider, provider.get_tracer("sampling-lab", "1.0")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self.send({"status": "ready", "sdk": "1.38.0"})
        q = parse_qs(parsed.query)
        mode, kind = q.get("mode", ["tail"])[0], q.get("kind", ["normal"])[0]
        case, run = q.get("case", ["manual"])[0], q.get("run", ["manual"])[0]
        if parsed.path != "/checkout" or mode not in tracers or kind not in ["normal", "error", "slow", "late"]:
            return self.send({"error": "invalid request"}, 400)
        token = request_key.set(f"{run}/{mode}/{case}")
        tracer = tracers[mode]
        started = time.monotonic()
        attrs = {"lab.run": run, "lab.mode": mode, "lab.kind": kind, "lab.case": case}
        # The late child deliberately finishes after the request span and is exported five seconds later.
        if kind == "late":
            root = tracer.start_span("checkout", kind=SpanKind.SERVER, attributes=attrs)
            ctx = trace.set_span_in_context(root)
            child = tracer.start_span("inventory.async", context=ctx, attributes=attrs)
            time.sleep(0.015)
            child.set_status(Status(StatusCode.ERROR, "synthetic late error"))
            child_end = time.time_ns()
            root.end()
            time.sleep(5)
            child.end(end_time=child_end)
        else:
            with tracer.start_as_current_span("checkout", kind=SpanKind.SERVER, attributes=attrs) as root:
                with tracer.start_as_current_span("inventory.lookup", attributes=attrs) as child:
                    time.sleep(0.32 if kind == "slow" else 0.015)
                    if kind == "error":
                        child.set_status(Status(StatusCode.ERROR, "synthetic inventory error"))
                        root.set_status(Status(StatusCode.ERROR, "synthetic checkout failure"))
        sc = root.get_span_context()
        result = dict(attrs, trace_id=f"{sc.trace_id:032x}", sdk_sampled=bool(sc.trace_flags.sampled),
                      elapsed_ms=round((time.monotonic()-started)*1000, 1), http_status=500 if kind == "error" else 200)
        print(json.dumps({"event": "checkout.completed", **result}), flush=True)
        request_key.reset(token)
        # Error requests return actual HTTP 500; the driver records the body rather than treating it as a transport error.
        self.send(result, result["http_status"])

ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
