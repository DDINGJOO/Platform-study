"""Synthetic-only HTTP demo. Explicit SDK instrumentation keeps the data paths visible."""
import json, logging, os, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from opentelemetry import baggage, context, trace
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.trace import SpanKind, Status, StatusCode
ROLE = os.getenv('ROLE', 'front')
MARKER = 'PRIVATE_CUSTOMER_ALPHA'  # A dummy token, never a real person's identifier.
providers = {}
for mode, port in [('raw',4317),('narrow',4327),('scrubbed',4337),('minimized',4337)]:
    resource = Resource.create({'service.name': f'privacy-{ROLE}', 'lab.mode': mode})
    tp = TracerProvider(resource=resource)
    tp.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=f'collector:{port}', insecure=True)))
    lp = LoggerProvider(resource=resource)
    lp.add_log_record_processor(SimpleLogRecordProcessor(OTLPLogExporter(endpoint=f'collector:{port}', insecure=True)))
    logger = logging.getLogger(mode)
    logger.setLevel(logging.INFO)
    logger.addHandler(LoggingHandler(logger_provider=lp))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console)
    logger.propagate = False
    providers[mode] = tp.get_tracer('privacy-lab'), logger

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/health':
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok'); return
        args = urllib.parse.parse_qs(parsed.query)
        mode = args.get('mode', ['raw'])[0]
        if mode not in providers:
            self.send_error(400, 'unknown mode'); return
        run_id = args.get('run', ['manual'])[0]
        tracer, logger = providers[mode]
        ctx = extract({key.lower(): value for key, value in self.headers.items()})
        # Preserve trace context while replacing baggage, then attach exactly once.
        if mode == 'minimized':
            allowed = baggage.get_baggage('tier', context=ctx)
            ctx = baggage.clear(context=ctx)
            if allowed is not None: ctx = baggage.set_baggage('tier', allowed, context=ctx)
        token = context.attach(ctx)
        try:
            with tracer.start_as_current_span(f'{ROLE} GET /demo', kind=SpanKind.SERVER) as span:
                span.set_attribute('lab.mode', mode)
                span.set_attribute('lab.run', run_id)
                received = baggage.get_baggage('private.customer')
                # Attribute creation is explicit: baggage does not automatically become a span attribute.
                if mode != 'minimized':
                    span.set_attribute('synthetic.customer', MARKER)
                message = f'handled mode={mode} run={run_id} customer=' + ('[omitted]' if mode == 'minimized' else MARKER)
                logger.info(message, extra={'lab.mode': mode, 'lab.run': run_id, 'synthetic.customer': '[omitted]' if mode == 'minimized' else MARKER})
                if ROLE == 'front':
                    try:
                        raise ValueError('invalid customer=' + ('[omitted]' if mode == 'minimized' else MARKER))
                    except ValueError as exc:
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                    with tracer.start_as_current_span('GET downstream /demo', kind=SpanKind.CLIENT):
                        headers = {}
                        inject(headers)
                        req = urllib.request.Request(f'http://downstream:8080/demo?mode={mode}&run={run_id}', headers=headers)
                        result = json.load(urllib.request.urlopen(req))
                    result['trace_id'] = format(span.get_span_context().trace_id, '032x')
                else:
                    result = {'mode':mode, 'run':run_id, 'received_private_baggage':received, 'received_tier':baggage.get_baggage('tier'), 'raw_baggage_header':self.headers.get('baggage')}
            data = json.dumps(result).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
        finally:
            context.detach(token)

ThreadingHTTPServer(('0.0.0.0',8080), Handler).serve_forever()
