import json
import platform
import sys
import time
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'tests')]
from validator import validate
from fixtures import sample

print('Environment:', platform.platform(), platform.machine(), 'Python', platform.python_version())
for label, raw in [('valid-10000', sample(10000)), ('invalid-10000', sample(10000).replace(b'TEST BANK', b'tEST BANK'))]:
    start = time.perf_counter()
    result = validate(raw)
    payload = json.dumps(result, ensure_ascii=True).encode()
    elapsed = time.perf_counter() - start
    print(f'{label}: {len(raw)} input bytes; {len(payload)} response bytes; {result["errorCount"]} errors; engine+JSON {elapsed:.3f}s')
    if elapsed > 10:
        raise SystemExit('Vượt mục tiêu 10 giây; cần kiểm tra trên máy benchmark.')
