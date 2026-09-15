"""Loopback-only development app. Request bytes are never written to disk."""
import base64
import json
import mimetypes
import os
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from validator import TYPE_CODES, RULE_VERSION, validate, preview, fields_for

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
MAX_UPLOAD = int(os.environ.get('MAX_UPLOAD_BYTES', 16 * 1024 * 1024))
DEFAULT_LIMIT = int(os.environ.get('MAX_DATA_RECORDS', '10000'))
if not 1 <= DEFAULT_LIMIT <= 999999 or MAX_UPLOAD < 122:
    raise SystemExit('ENV không hợp lệ: MAX_DATA_RECORDS = 1..999999; MAX_UPLOAD_BYTES >= 122.')
VERIFY_SLOT = threading.BoundedSemaphore(1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No access logs, names, bytes, or results.

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        super().end_headers()

    def send_bytes(self, body, content_type='application/json; charset=utf-8', status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, obj, status=200):
        self.send_bytes(json.dumps(obj, ensure_ascii=True, separators=(',', ':')).encode(), status=status)

    def local_request(self):
        port = self.server.server_port
        valid_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        if host not in valid_hosts or (origin is not None and origin != 'http://' + host):
            self.json({'error': 'Chỉ cho phép request từ app local cùng origin.'}, 403)
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == '/api/config':
            self.json(dict(defaultLimit=DEFAULT_LIMIT, maxUploadBytes=MAX_UPLOAD, typeCodes=TYPE_CODES, ruleVersion=RULE_VERSION))
            return
        allowed = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg'}
        if path not in allowed:
            self.json({'error': 'Không tìm thấy.'}, 404)
            return
        file = PUBLIC / allowed[path]
        self.send_bytes(file.read_bytes(), mimetypes.guess_type(str(file))[0] + '; charset=utf-8')

    def do_POST(self):
        if not self.local_request():
            return
        route = urlsplit(self.path).path
        if route not in ('/api/verify', '/api/preview'):
            self.json({'error': 'Không tìm thấy.'}, 404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            bound = MAX_UPLOAD if route == '/api/verify' else 512 * 1024
            if self.headers.get('Transfer-Encoding') or length < 0 or length > bound:
                self.close_connection = True
                self.json({'error': 'Vượt giới hạn dung lượng xử lý của app local.'}, 413)
                return
            expected_type = 'application/octet-stream' if route == '/api/verify' else 'application/json'
            if self.headers.get('Content-Type', '').split(';')[0] != expected_type:
                self.close_connection = True
                self.json({'error': 'Content-Type không hợp lệ.'}, 415)
                return
            self.connection.settimeout(30)
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError('Request chưa đủ bytes.')
            if route == '/api/verify':
                if not VERIFY_SLOT.acquire(blocking=False):
                    self.json({'error': 'App đang kiểm tra một file khác. Vui lòng thử lại sau.'}, 429)
                    return
                try:
                    result = validate(body, self.headers.get('X-Type-Code', '21'), int(self.headers.get('X-Max-Records', str(DEFAULT_LIMIT))))
                    self.json(result)
                finally:
                    VERIFY_SLOT.release()
            else:
                data = json.loads(body)
                if not isinstance(data, list) or len(data) > 25:
                    raise ValueError('Preview tối đa 25 dòng mỗi request.')
                output = []
                for item in data:
                    raw = base64.b64decode(item['bytes'], validate=True)
                    if len(raw) > 8192:
                        raise ValueError('Preview tối đa 8192 bytes mỗi dòng.')
                    offset = item.get('offset', 0)
                    if not isinstance(offset, int) or not 0 <= offset <= MAX_UPLOAD:
                        raise ValueError('Byte offset không hợp lệ.')
                    view = preview(raw)
                    if offset:
                        prefix = base64.b64decode(item.get('prefix', ''), validate=True)
                        view['fields'] = fields_for(prefix[:120])
                        for token in view['tokens']:
                            token['start'] += offset
                            token['end'] += offset
                    output.append(view)
                self.json(output)
        except (ValueError, TypeError, KeyError, UnicodeError):
            self.json({'error': 'Request hoặc Settings không hợp lệ.'}, 400)
        except (TimeoutError, OSError):
            self.close_connection = True


def main():
    ThreadingHTTPServer.allow_reuse_address = True
    start_port = int(os.environ.get('PORT', '4173'))
    max_attempts = 20
    server = None
    chosen_port = None

    for offset in range(max_attempts):
        candidate_port = start_port + offset
        try:
            server = ThreadingHTTPServer(('127.0.0.1', candidate_port), Handler)
            chosen_port = candidate_port
            break
        except OSError:
            continue

    if not server:
        raise SystemExit(f'Không thể mở port nào trong khoảng {start_port}–{start_port + max_attempts - 1}.')

    if chosen_port != start_port:
        print(f'Port {start_port} đang bận, đã tự động chuyển sang: http://127.0.0.1:{chosen_port}', flush=True)
    else:
        print(f'Zengin Validator: http://127.0.0.1:{chosen_port}', flush=True)
    print('Chỉ xử lý local. Ctrl+C để dừng.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
