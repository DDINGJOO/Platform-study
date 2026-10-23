"""Synthetic-only sticky experiment. No packages beyond Python's standard library."""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPERIMENT = os.environ.get('EXPERIMENT_ID', 'checkout-copy-v1')
SALT = os.environ.get('ASSIGNMENT_SALT', 'synthetic-lab-salt-v1')
DB = os.environ.get('DB_PATH', '/data/events.sqlite')


def bucket(user, salt=SALT, experiment=EXPERIMENT):
    material = json.dumps([experiment, salt, user], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return int.from_bytes(hashlib.sha256(material).digest()[:8], 'big') % 10000


def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS experiments(experiment_id TEXT PRIMARY KEY, config TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(experiment_id TEXT, user_id TEXT, variant TEXT, bucket INTEGER, PRIMARY KEY(experiment_id,user_id));
        CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT, user_id TEXT, variant TEXT, event_type TEXT, request_id TEXT, occurred_at TEXT, UNIQUE(experiment_id,user_id,event_type));
        CREATE TABLE IF NOT EXISTS attempts(experiment_id TEXT, event_type TEXT, total INTEGER NOT NULL, PRIMARY KEY(experiment_id,event_type));
        ''')
        config = json.dumps({'salt': SALT, 'algorithm': 'sha256-first8-big-mod10000', 'a_threshold': 5000}, sort_keys=True)
        previous = db.execute('SELECT config FROM experiments WHERE experiment_id=?', (EXPERIMENT,)).fetchone()
        if previous and previous['config'] != config:
            raise RuntimeError('Existing experiment configuration changed: use a NEW experiment_id')
        db.execute('INSERT OR IGNORE INTO experiments VALUES(?,?)', (EXPERIMENT, config))


def export_data(db):
    return {'schema_version': 1, 'experiment_id': EXPERIMENT,
            'assignments': [dict(r) for r in db.execute('SELECT experiment_id,user_id,variant,bucket FROM assignments WHERE experiment_id=? ORDER BY user_id', (EXPERIMENT,))],
            'events': [dict(r) for r in db.execute('SELECT * FROM events WHERE experiment_id=? ORDER BY event_id', (EXPERIMENT,))]}


def summary(db):
    rows = {}
    for v in ('A', 'B'):
        row = {'assigned_users': db.execute('SELECT count(*) FROM assignments WHERE experiment_id=? AND variant=?', (EXPERIMENT, v)).fetchone()[0]}
        for event in ('entry', 'exposure', 'conversion'):
            row[event + '_users'] = db.execute('SELECT count(*) FROM events WHERE experiment_id=? AND variant=? AND event_type=?', (EXPERIMENT, v, event)).fetchone()[0]
        row['conversion_rate'] = row['conversion_users'] / row['exposure_users'] if row['exposure_users'] else None
        rows[v] = row
    attempts = {r['event_type']: r['total'] for r in db.execute('SELECT * FROM attempts WHERE experiment_id=?', (EXPERIMENT,))}
    return {'experiment_id': EXPERIMENT, 'variants': rows, 'accepted_event_attempts': attempts}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def respond(self, status, body, content_type='application/json'):
        raw = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        with connect() as db:
            if self.path == '/ready':
                return self.respond(200, {'ready': True, 'experiment_id': EXPERIMENT})
            if self.path == '/export':
                return self.respond(200, export_data(db))
            if self.path == '/summary':
                return self.respond(200, summary(db))
            if self.path == '/metrics':
                data = summary(db)
                lines = ['# HELP ab_users Distinct synthetic users in the current experiment.', '# TYPE ab_users gauge']
                for variant, values in data['variants'].items():
                    for stage in ('assigned', 'entry', 'exposure', 'conversion'):
                        labels = f'experiment_id="{EXPERIMENT}",variant="{variant}",stage="{stage}"'
                        lines.append(f'ab_users{{{labels}}} {values[stage + "_users"]}')
                lines += ['# HELP ab_event_attempts_total Accepted event submissions including duplicate users.', '# TYPE ab_event_attempts_total counter']
                for event in ('entry', 'exposure', 'conversion'):
                    lines.append(f'ab_event_attempts_total{{experiment_id="{EXPERIMENT}",event_type="{event}"}} {data["accepted_event_attempts"].get(event, 0)}')
                return self.respond(200, '\n'.join(lines) + '\n', 'text/plain; version=0.0.4')
        self.respond(404, {'error': 'unknown path'})

    def do_POST(self):
        event = self.path.removeprefix('/')
        if event not in ('entry', 'exposure', 'conversion'):
            return self.respond(404, {'error': 'unknown event'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size < 4096:
                raise ValueError('JSON body must be between 1 and 4095 bytes')
            body = json.loads(self.rfile.read(size))
            user, request = body.get('user_id'), body.get('request_id')
            if not isinstance(user, str) or not user.startswith('synthetic-user-') or not 1 <= len(user) <= 100:
                raise ValueError('user_id must be a synthetic-user- identifier')
            if not isinstance(request, str) or not 1 <= len(request) <= 120:
                raise ValueError('request_id is required')
            if 'variant' in body:
                raise ValueError('variant is assigned by the server')
        except (ValueError, TypeError, AttributeError) as e:
            return self.respond(400, {'error': str(e)})
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            assigned = db.execute('SELECT variant FROM assignments WHERE experiment_id=? AND user_id=?', (EXPERIMENT, user)).fetchone()
            if not assigned:
                if event != 'entry':
                    return self.respond(409, {'error': 'entry required before exposure/conversion'})
                b = bucket(user)
                variant = 'A' if b < 5000 else 'B'
                db.execute('INSERT INTO assignments VALUES(?,?,?,?)', (EXPERIMENT, user, variant, b))
            else:
                variant = assigned['variant']
            if event == 'conversion' and not db.execute('SELECT 1 FROM events WHERE experiment_id=? AND user_id=? AND event_type="exposure"', (EXPERIMENT, user)).fetchone():
                return self.respond(409, {'error': 'exposure required before conversion'})
            stamp = datetime.now(timezone.utc).isoformat(timespec='microseconds')
            cursor = db.execute('INSERT OR IGNORE INTO events(experiment_id,user_id,variant,event_type,request_id,occurred_at) VALUES(?,?,?,?,?,?)', (EXPERIMENT, user, variant, event, request, stamp))
            inserted = cursor.rowcount == 1
            db.execute('INSERT INTO attempts VALUES(?,?,1) ON CONFLICT(experiment_id,event_type) DO UPDATE SET total=total+1', (EXPERIMENT, event))
        self.respond(200, {'experiment_id': EXPERIMENT, 'user_id': user, 'variant': variant, 'event_type': event, 'inserted': inserted})


if __name__ == '__main__':
    initialize()
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
