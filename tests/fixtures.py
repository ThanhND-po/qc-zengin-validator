"""Synthetic fixtures with independently specified positions; no real bank/customer data."""
def sample(count=2, type_code='21', amount=12500, ending=b'\n'):
    header = (b'1' + type_code.encode() + b'0' + b'0000000001' + b'TEST SENDER'.ljust(40)
              + b'0915' + b'0001' + b'TEST BANK'.ljust(15) + b'001' + b'TEST BRANCH'.ljust(15)
              + b'1' + b'0000001' + b' ' * 17)
    data = (b'2' + b'0001' + b'TEST BANK'.ljust(15) + b'001' + b'TEST BRANCH'.ljust(15)
            + b'0000' + b'1' + b'0000002' + 'ﾀﾅｶ ﾀﾛｳ'.encode('cp932').ljust(30)
            + str(amount).zfill(10).encode() + b'0' + b' ' * 20 + b'0' + b' ' + b' ' * 7)
    trailer = b'8' + str(count).zfill(6).encode() + str(count * amount).zfill(12).encode() + b' ' * 101
    end = b'9' + b' ' * 119
    assert len(header) == len(data) == len(trailer) == len(end) == 120
    return ending.join([header] + [data] * count + [trailer, end]) + ending


def change(content, row, start, replacement, remove=None):
    ending = b'\r\n' if b'\r\n' in content else b'\n'
    lines = content.split(ending)
    raw = lines[row - 1]
    remove = len(replacement) if remove is None else remove
    lines[row - 1] = raw[:start - 1] + replacement + raw[start - 1 + remove:]
    return ending.join(lines)
