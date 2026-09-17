"""HTTP boundary tests use an ephemeral loopback port and synthetic data only."""
import base64
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from server import Handler
from fixtures import sample


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_lf_passes_and_crlf_fails_without_transport_rewriting(self):
        for ending, expected_status in ((b'\n', 'valid'), (b'\r\n', 'invalid')):
            raw = sample(ending=ending)
            status, headers, body = self.request('POST', '/api/verify', raw,
                                                {'Content-Type': 'application/octet-stream'})
            result = json.loads(body)
            self.assertEqual(status, 200)
            self.assertEqual(result['status'], expected_status)
            self.assertEqual(result['fileBytes'], len(raw))
            self.assertEqual(result['lineEndings']['CRLF'], 5 if ending == b'\r\n' else 0)
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_cross_origin_and_foreign_host_denied(self):
        for headers in ({'Origin': 'https://example.org'}, {'Host': 'example.org'}):
            self.assertEqual(self.request('GET', '/api/config', headers=headers)[0], 403)

    def test_source_and_path_traversal_unavailable(self):
        for path in ('/validator.py', '/../README.md', '/.env', '/samples/valid-2-records.txt'):
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_localization_contract_is_exposed_to_the_ui(self):
        status, _, body = self.request('GET', '/api/config')
        config = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(config['resultSchemaVersion'], 2)
        self.assertIn('CRLF_LINE_ENDING', config['issueCodes'])
        self.assertIn('line_ending', config['fieldCodes'])
        self.assertEqual(self.request('GET', '/locale-vi.js')[0], 200)

    def test_bad_settings_and_content_type(self):
        self.assertEqual(self.request('POST', '/api/verify', sample(), {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request('POST', '/api/verify', sample(),
                                      {'Content-Type': 'application/octet-stream', 'X-Max-Records': '0'})[0], 400)

    def test_preview_cp932_byte_range(self):
        raw = b'A' + 'ア'.encode('cp932')
        status, _, body = self.request('POST', '/api/preview',
            json.dumps([{'bytes': base64.b64encode(raw).decode()}]), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        token = json.loads(body)[0]['tokens'][1]
        self.assertEqual((token['char'], token['start'], token['end'], token['hex']), ('ア', 2, 3, '83 41'))

    def test_oversized_request_rejected_before_read(self):
        self.assertEqual(self.request('POST', '/api/verify', b'',
            {'Content-Type': 'application/octet-stream', 'Content-Length': '999999999'})[0], 413)
