"""Generate deliberately synthetic fixtures for manual browser QA; never use at a bank."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from fixtures import sample, change


def samples():
    raw = sample()
    return {
        'valid-2-records.txt': raw,
        'valid-10000-records.txt': sample(10000),
        'multibyte-121-bytes.txt': change(raw, 2, 51, 'ア'.encode('cp932'), remove=1),
        'trailer-mismatch.txt': change(raw, 4, 8, b'000000000001'),
        'edi-unverified.txt': change(raw, 2, 113, b'Y'),
        'invalid-150-records.txt': sample(150).replace(b'TEST BANK', b'tEST BANK'),
        'invalid-crlf.txt': sample(ending=b'\r\n'),
        'invalid-cr-only.txt': sample(ending=b'\r'),
    }


if __name__ == '__main__':
    dest = Path(__file__).resolve().parents[1] / 'samples'
    dest.mkdir(exist_ok=True)
    for name, raw in samples().items():
        (dest / name).write_bytes(raw)
    print('Đã tạo 8 file mẫu tổng hợp trong samples/. Không upload các mẫu này lên ngân hàng.')
