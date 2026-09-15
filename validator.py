"""Pure, offline validator. No filesystem, network, logging or mutable session state."""
import datetime
import hashlib
import re
import time

RULE_VERSION = 'zengin-workbook-2026-09-09.v3-kana-long-mark'
TYPE_CODES = ('21', '11', '71', '12', '72')
# zengin-0.2.2/kanakana.py: fullwidth_to_halfwidth_kana maps U+30FC to U+FF70.
# Accept the half-width output; never normalize the uploaded evidence.
KANA = 'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝｰ'
ALLOWED = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ' + KANA + 'ﾞﾟ\\｢｣()/.-')
ALLOWED_BYTES = {ord(c.encode('cp932')) for c in ALLOWED}

# name, width, kind, required, fixed/enumerated values. Offsets are derived, never sample LEN caches.
HEADER = [
    ('Data Division', 1, 'N', True, ('1',)), ('Type Code', 2, 'N', True, TYPE_CODES),
    ('Code Division', 1, 'N', True, ('0',)), ('Requester Code', 10, 'N', True, None),
    ('Requester Name', 40, 'T', False, None), ('Transfer Date', 4, 'N', True, None),
    ('Source Bank Code', 4, 'N', True, None), ('Source Bank Name', 15, 'T', False, None),
    ('Source Branch Code', 3, 'N', True, None), ('Source Branch Name', 15, 'T', False, None),
    ('Account Type', 1, 'N', True, ('1', '2', '4')), ('Account Number', 7, 'N', True, None),
    ('Dummy', 17, 'S', False, None),
]
DATA = [
    ('Data Division', 1, 'N', True, ('2',)), ('Destination Bank Code', 4, 'N', True, None),
    ('Destination Bank Name', 15, 'T', True, None), ('Destination Branch Code', 3, 'N', True, None),
    ('Destination Branch Name', 15, 'T', True, None), ('Clearing House No.', 4, 'N', False, ('0000',)),
    ('Account Type', 1, 'N', True, ('1', '2', '4')), ('Account Number', 7, 'N', True, None),
    ('Beneficiary Name', 30, 'T', True, None), ('Amount', 10, 'N', True, None),
    ('New Code', 1, 'N', False, ('0',)), ('Customer Code 1', 10, 'T', False, None),
    ('Customer Code 2', 10, 'T', False, None), ('Transfer type', 1, 'N', False, ('0',)),
    ('EDI Flag (識別表示)', 1, 'T', False, None), ('Dummy', 7, 'S', False, None),
]
TRAILER = [('Data Division', 1, 'N', True, ('8',)), ('Total Count', 6, 'N', True, None),
           ('Total Amount', 12, 'N', True, None), ('Dummy', 101, 'S', False, None)]
END = [('Data Division', 1, 'N', True, ('9',)), ('Dummy', 119, 'S', False, None)]
LAYOUTS = {49: HEADER, 50: DATA, 56: TRAILER, 57: END}
RECORD_NAMES = {49: 'Header', 50: 'Data', 56: 'Trailer', 57: 'End'}


def fields_for(raw):
    layout = LAYOUTS.get(raw[0] if raw else 0, [])
    if raw[:1] == b'2' and raw[112:113] == b'Y':
        layout = DATA[:11] + [('EDI Information', 20, 'T', False, None)] + DATA[13:]
    pos = 1
    result = []
    for name, width, kind, required, values in layout:
        result.append(dict(name=name, start=pos, end=pos + width - 1,
                           kind=kind, required=required, values=values))
        pos += width
    return result


def decode_tokens(raw):
    """CP932 tokens with byte positions; undecodable bytes stay individually visible as hex."""
    tokens, i = [], 0
    while i < len(raw):
        width = 2 if 0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC else 1
        part = raw[i:i + width]
        try:
            if len(part) != width:
                raise UnicodeError()
            char = part.decode('cp932', errors='strict')
            valid = True
        except UnicodeError:
            width, part, char, valid = 1, raw[i:i + 1], None, False
        tokens.append(dict(start=i + 1, end=i + width, char=char,
                           hex=part.hex(' ').upper(), valid=valid))
        i += width
    return tokens


def excerpt(raw):
    return ''.join(t['char'] if t['valid'] else '<' + t['hex'] + '>' for t in decode_tokens(raw))


def validate(content, type_code='21', max_records=10000):
    if type_code not in TYPE_CODES:
        raise ValueError('Type Code không được hỗ trợ.')
    if isinstance(max_records, bool) or not isinstance(max_records, int) or not 1 <= max_records <= 999999:
        raise ValueError('Giới hạn Data Records phải là số nguyên từ 1 đến 999999 (Trailer có 6 digits).')
    started = time.perf_counter()
    issues, lengths = [], []
    result = dict(ruleVersion=RULE_VERSION, settings=dict(typeCode=type_code, maxRecords=max_records),
                  checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  sha256=hashlib.sha256(content).hexdigest(), fileBytes=len(content),
                  dataCount=0, totalAmount=None, trailerCount=None, trailerAmount=None,
                  countMatches=None, amountMatches=None, complete=False, issues=issues,
                  rowLengths=lengths, invalidRows=[], rowsInspected=0, ediRows=0,
                  lineEndings=dict(LF=0, CRLF=0), normalizedLineEnding='LF')

    def issue(code, message, row=1, start=1, end=None, field='File', raw=b'',
              expected='', actual='', severity='error'):
        issues.append(dict(code=code, message=message, row=row, start=start, end=end or start,
                           field=field, hex=raw.hex(' ').upper(), excerpt=excerpt(raw),
                           expected=str(expected), actual=str(actual), severity=severity))

    def finish(stopped=False):
        result['complete'] = not stopped
        result['errorCount'] = sum(i['severity'] == 'error' for i in issues)
        result['unverifiedCount'] = sum(i['severity'] == 'unverified' for i in issues)
        result['status'] = ('stopped' if stopped else 'invalid' if result['errorCount']
                            else 'incomplete' if result['unverifiedCount'] else 'valid')
        result['invalidRows'] = sorted({i['row'] for i in issues})
        result['durationMs'] = round((time.perf_counter() - started) * 1000, 2)
        return result

    if not content:
        issue('EMPTY_FILE', 'File không có dữ liệu.', expected='Header, Data, Trailer, End')
        return finish(True)
    bom = next((b for b in (b'\xef\xbb\xbf', b'\xff\xfe', b'\xfe\xff', b'\x00\x00\xfe\xff') if content.startswith(b)), None)
    if bom:
        issue('BOM', 'File có BOM. Không thể đọc record đầu tại byte 1 theo cấu trúc đã chọn.',
              end=len(bom), raw=bom, expected='CP932, không BOM')
        return finish(True)

    # Structural gate: inspect sequentially, stop at the first structural/limit failure.
    rows, pos, expected_state, count = [], 0, 'header', 0
    while pos < len(content):
        row_no = len(rows) + 1
        match = re.compile(b'[\r\n]').search(content, pos)
        if match is None:
            issue('MISSING_LINE_ENDING', 'Thiếu ký tự xuống dòng cuối record.', row_no,
                  len(content) - pos + 1, expected='LF (0A) hoặc CRLF (0D 0A) sau mỗi record')
            return finish(True)
        line_end = match.start()
        raw = content[pos:line_end]
        lengths.append(len(raw))
        result['rowsInspected'] = row_no
        ending = 'CRLF' if content[line_end:line_end + 2] == b'\r\n' else 'LF'
        if content[line_end] == 13 and ending != 'CRLF':
            issue('LINE_ENDING', 'CR đứng riêng không phải ký tự xuống dòng được hỗ trợ.', row_no, len(raw) + 1,
                  raw=b'\r', expected='LF (0A) hoặc CRLF (0D 0A)')
            return finish(True)
        # Treat CRLF as LF logically, without rewriting input or shifting byte evidence.
        result['lineEndings'][ending] += 1
        record = raw[:1]
        allowed_types = {'header': (b'1',), 'first_data': (b'2',), 'data': (b'2', b'8'), 'end': (b'9',), 'done': ()}
        if record not in allowed_types[expected_state]:
            issue('STRUCTURE', 'Thiếu, thừa hoặc sai thứ tự record.', row_no, raw=record,
                  expected={'header': 'Header (1)', 'first_data': 'ít nhất một Data (2)',
                            'data': 'Data (2) hoặc Trailer (8)', 'end': 'End (9)', 'done': 'kết thúc file'}[expected_state],
                  actual=excerpt(record) if record else 'dòng trống')
            return finish(True)
        rows.append(raw)
        if record == b'1':
            expected_state = 'first_data'
        elif record == b'2':
            count += 1
            result['dataCount'] = count
            expected_state = 'data'
            if count > max_records:
                issue('RECORD_LIMIT', 'Vượt giới hạn Data Records đang áp dụng. Dừng kiểm tra.', row_no,
                      expected=max_records, actual='ít nhất ' + str(count))
                return finish(True)
        elif record == b'8':
            expected_state = 'end'
        else:
            expected_state = 'done'
        pos = line_end + (2 if ending == 'CRLF' else 1)
    if expected_state != 'done':
        issue('STRUCTURE_EOF', 'File thiếu record kết thúc cấu trúc.', len(rows) + 1,
              expected='Header → Data → Trailer → End')
        return finish(True)

    total, amount_complete = 0, True
    for row_no, raw in enumerate(rows, 1):
        layout = fields_for(raw)
        if len(raw) != 120:
            issue('RECORD_LENGTH', 'Record không có đúng 120 encoded bytes (không tính ký tự xuống dòng).', row_no,
                  min(len(raw) + 1, 121), max(120, len(raw)), 'Record', raw[120:], '120 bytes', str(len(raw)) + ' bytes')
        tokens = decode_tokens(raw) if any(b not in ALLOWED_BYTES for b in raw) else []
        for token in tokens:
            if token['valid'] and token['char'] in ALLOWED and token['end'] == token['start']:
                continue
            field = next((f['name'] for f in layout if f['start'] <= token['start'] <= f['end']), 'Ngoài record')
            width = token['end'] - token['start'] + 1
            issue('INVALID_CP932' if not token['valid'] else 'MULTIBYTE' if width > 1 else 'CHARSET',
                  'Byte không decode được bằng CP932.' if not token['valid'] else
                  'Ký tự chiếm nhiều hơn 1 byte.' if width > 1 else 'Ký tự không thuộc allowed character set.',
                  row_no, token['start'], token['end'], field, raw[token['start'] - 1:token['end']],
                  'ký tự half-width hợp lệ, 1 byte', str(width) + ' byte(s)')
        if len(raw) != 120:
            issue('FIELD_ALIGNMENT_UNVERIFIED', 'Chưa thể xác minh field và totals của record sai độ dài; không tự dịch vị trí field.',
                  row_no, 1, max(1, len(raw)), 'Record', expected='120 bytes', severity='unverified')
            if raw[:1] == b'2':
                amount_complete = False
            continue

        invalid_field_names = set()
        for f in layout:
            segment = raw[f['start'] - 1:f['end']]
            common = dict(row=row_no, start=f['start'], end=f['end'], field=f['name'], raw=segment)
            numeric = all(48 <= b <= 57 for b in segment)
            if f['kind'] == 'N' and not numeric:
                invalid_field_names.add(f['name'])
                issue('NUMERIC', 'Field Numeric chỉ chấp nhận digits 0–9, zero-padding bên trái.',
                      expected=str(len(segment)) + ' digits', **common)
            if f['kind'] == 'S' and segment != b' ' * len(segment):
                issue('PADDING', 'Dummy phải chứa toàn bộ half-width spaces.', expected='space 0x20', **common)
            if f['required'] and f['kind'] == 'T' and not segment.strip(b' '):
                issue('REQUIRED', 'Field bắt buộc đang trống.', expected='có nội dung', **common)
            if f['values'] and not (f['kind'] == 'N' and not numeric):
                if segment not in [v.encode('ascii') for v in f['values']]:
                    issue('VALUE', 'Giá trị không thuộc specification.', expected=', '.join(f['values']), **common)
        if raw[:1] == b'1':
            if raw[1:3] in [v.encode() for v in TYPE_CODES] and raw[1:3] != type_code.encode():
                issue('TYPE_MISMATCH', 'Type Code không khớp Settings.', row_no, 2, 3, 'Type Code', raw[1:3], type_code, excerpt(raw[1:3]))
            if 'Transfer Date' not in invalid_field_names:
                try:
                    # No year in MMDD. A leap year avoids inventing a rejection of 0229.
                    datetime.date(2000, int(raw[54:56]), int(raw[56:58]))
                except ValueError:
                    issue('DATE', 'Transfer Date không phải MMDD hợp lệ.', row_no, 55, 58, 'Transfer Date', raw[54:58], 'MMDD hợp lệ')
        elif raw[:1] == b'2':
            if 'Amount' in invalid_field_names or any(t['start'] <= 90 and t['end'] >= 81 and t['end'] > t['start'] for t in tokens):
                amount_complete = False
            else:
                total += int(raw[80:90])
            if raw[112:113] == b'Y':
                result['ediRows'] += 1
                issue('EDI_UNVERIFIED', 'Chưa thể xác minh nội dung nghiệp vụ EDI Information. Đã kiểm tra format và bytes.',
                      row_no, 92, 113, 'EDI Information / 識別表示', raw[91:113],
                      'cần specification nghiệp vụ và dữ liệu kiểm chứng EDI', severity='unverified')
        elif raw[:1] == b'8':
            if 'Total Count' not in invalid_field_names:
                result['trailerCount'] = int(raw[1:7])
            if 'Total Amount' not in invalid_field_names:
                result['trailerAmount'] = int(raw[7:19])

    trailer_row = len(rows) - 1
    if result['trailerCount'] is not None:
        result['countMatches'] = result['trailerCount'] == count
        if not result['countMatches']:
            issue('COUNT_MISMATCH', 'Total Count trong Trailer không khớp số Data Records.', trailer_row,
                  2, 7, 'Total Count', rows[-2][1:7], count, result['trailerCount'])
    if amount_complete:
        result['totalAmount'] = str(total)
        if result['trailerAmount'] is not None:
            result['amountMatches'] = total == result['trailerAmount']
            if not result['amountMatches']:
                issue('AMOUNT_MISMATCH', 'Total Amount trong Trailer không khớp tổng Data Records.', trailer_row,
                      8, 19, 'Total Amount', rows[-2][7:19], total, result['trailerAmount'])
    else:
        issue('TOTAL_UNVERIFIED', 'Không đủ dữ liệu hợp lệ để tính toàn bộ tổng tiền và đối chiếu Trailer.',
              trailer_row, 8, 19, 'Total Amount', severity='unverified')
    if result['trailerAmount'] is not None:
        result['trailerAmount'] = str(result['trailerAmount'])
    return finish()


def preview(raw):
    return dict(tokens=decode_tokens(raw), fields=fields_for(raw))
