"""Pure, offline validator. No filesystem, network, logging or mutable session state."""
import datetime
import hashlib
import re
import time

RULE_VERSION = 'zengin-workbook-2026-09-17.v5-schema2-lf-only'
RESULT_SCHEMA_VERSION = 2
TYPE_CODES = ('21', '11', '71', '12', '72')
ISSUE_CODES = (
    'EMPTY_FILE', 'BOM', 'MISSING_LINE_ENDING', 'CRLF_LINE_ENDING', 'LINE_ENDING',
    'STRUCTURE', 'STRUCTURE_EOF', 'RECORD_LIMIT', 'RECORD_LENGTH', 'INVALID_CP932',
    'MULTIBYTE', 'CHARSET', 'FIELD_ALIGNMENT_UNVERIFIED', 'NUMERIC', 'PADDING',
    'REQUIRED', 'VALUE', 'TYPE_MISMATCH', 'DATE', 'EDI_UNVERIFIED',
    'COUNT_MISMATCH', 'AMOUNT_MISMATCH', 'TOTAL_UNVERIFIED',
)
# zengin-0.2.2/kanakana.py: fullwidth_to_halfwidth_kana maps U+30FC to U+FF70.
# Accept the half-width output; never normalize the uploaded evidence.
KANA = 'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝｰ'
ALLOWED = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ' + KANA + 'ﾞﾟ\\｢｣()/.-')
ALLOWED_BYTES = {ord(c.encode('cp932')) for c in ALLOWED}

# field code, width, kind, required, fixed/enumerated values. Offsets are derived, never sample LEN caches.
HEADER = [
    ('data_division', 1, 'N', True, ('1',)), ('type_code', 2, 'N', True, TYPE_CODES),
    ('code_division', 1, 'N', True, ('0',)), ('requester_code', 10, 'N', True, None),
    ('requester_name', 40, 'T', False, None), ('transfer_date', 4, 'N', True, None),
    ('source_bank_code', 4, 'N', True, None), ('source_bank_name', 15, 'T', False, None),
    ('source_branch_code', 3, 'N', True, None), ('source_branch_name', 15, 'T', False, None),
    ('account_type', 1, 'N', True, ('1', '2', '4')), ('account_number', 7, 'N', True, None),
    ('dummy', 17, 'S', False, None),
]
DATA = [
    ('data_division', 1, 'N', True, ('2',)), ('destination_bank_code', 4, 'N', True, None),
    ('destination_bank_name', 15, 'T', True, None), ('destination_branch_code', 3, 'N', True, None),
    ('destination_branch_name', 15, 'T', True, None), ('clearing_house_number', 4, 'N', False, ('0000',)),
    ('account_type', 1, 'N', True, ('1', '2', '4')), ('account_number', 7, 'N', True, None),
    ('beneficiary_name', 30, 'T', True, None), ('amount', 10, 'N', True, None),
    ('new_code', 1, 'N', False, ('0',)), ('customer_code_1', 10, 'T', False, None),
    ('customer_code_2', 10, 'T', False, None), ('transfer_type', 1, 'N', False, ('0',)),
    ('edi_flag', 1, 'T', False, None), ('dummy', 7, 'S', False, None),
]
TRAILER = [('data_division', 1, 'N', True, ('8',)), ('total_count', 6, 'N', True, None),
           ('total_amount', 12, 'N', True, None), ('dummy', 101, 'S', False, None)]
END = [('data_division', 1, 'N', True, ('9',)), ('dummy', 119, 'S', False, None)]
LAYOUTS = {49: HEADER, 50: DATA, 56: TRAILER, 57: END}
FIELD_CODES = tuple(dict.fromkeys(
    ('file', 'record', 'line_ending', 'outside_record', 'edi_information')
    + tuple(field[0] for layout in LAYOUTS.values() for field in layout)
))


def fields_for(raw):
    layout = LAYOUTS.get(raw[0] if raw else 0, [])
    if raw[:1] == b'2' and raw[112:113] == b'Y':
        layout = DATA[:11] + [('edi_information', 20, 'T', False, None)] + DATA[13:]
    pos = 1
    result = []
    for code, width, kind, required, values in layout:
        result.append(dict(code=code, start=pos, end=pos + width - 1,
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
        raise ValueError('UNSUPPORTED_TYPE_CODE')
    if isinstance(max_records, bool) or not isinstance(max_records, int) or not 1 <= max_records <= 999999:
        raise ValueError('INVALID_DATA_RECORD_LIMIT')
    started = time.perf_counter()
    issues, lengths = [], []
    result = dict(resultSchemaVersion=RESULT_SCHEMA_VERSION, ruleVersion=RULE_VERSION,
                  settings=dict(typeCode=type_code, maxRecords=max_records),
                  checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  sha256=hashlib.sha256(content).hexdigest(), fileBytes=len(content),
                  dataCount=0, totalAmount=None, trailerCount=None, trailerAmount=None,
                  countMatches=None, amountMatches=None, complete=False, issues=issues,
                  rowLengths=lengths, invalidRows=[], rowsInspected=0, ediRows=0,
                  lineEndings=dict(LF=0, CRLF=0), requiredLineEnding='LF')

    def issue(code, row=1, start=1, end=None, field_code='file', raw=b'',
              details=None, severity='error'):
        if code not in ISSUE_CODES:
            raise ValueError('UNKNOWN_ISSUE_CODE')
        if field_code not in FIELD_CODES:
            raise ValueError('UNKNOWN_FIELD_CODE')
        issues.append(dict(code=code, row=row, start=start, end=end or start,
                           fieldCode=field_code, hex=raw.hex(' ').upper(), excerpt=excerpt(raw),
                           details=details or {}, severity=severity))

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
        issue('EMPTY_FILE', details=dict(expected=['1', '2', '8', '9'], actual='EMPTY_FILE'))
        return finish(True)
    bom = next((b for b in (b'\xef\xbb\xbf', b'\xff\xfe', b'\xfe\xff', b'\x00\x00\xfe\xff') if content.startswith(b)), None)
    if bom:
        issue('BOM', end=len(bom), raw=bom,
              details=dict(expected='CP932_NO_BOM', actual='BOM'))
        return finish(True)

    # Structural gate: inspect sequentially, stop at the first structural/limit failure.
    rows, pos, expected_state, count = [], 0, 'header', 0
    while pos < len(content):
        row_no = len(rows) + 1
        match = re.compile(b'[\r\n]').search(content, pos)
        if match is None:
            issue('MISSING_LINE_ENDING', row_no, len(content) - pos + 1,
                  field_code='line_ending', details=dict(expected='LF', actual='EOF'))
            return finish(True)
        line_end = match.start()
        raw = content[pos:line_end]
        lengths.append(len(raw))
        result['rowsInspected'] = row_no
        ending = 'CRLF' if content[line_end:line_end + 2] == b'\r\n' else 'LF'
        if content[line_end] == 13 and ending != 'CRLF':
            issue('LINE_ENDING', row_no, len(raw) + 1, field_code='line_ending', raw=b'\r',
                  details=dict(expected='LF', actual='CR'))
            return finish(True)
        result['lineEndings'][ending] += 1
        if ending == 'CRLF':
            issue('CRLF_LINE_ENDING', row_no, len(raw) + 1, len(raw) + 2,
                  'line_ending', b'\r\n', dict(expected='LF', actual='CRLF'))
        record = raw[:1]
        allowed_types = {'header': (b'1',), 'first_data': (b'2',), 'data': (b'2', b'8'), 'end': (b'9',), 'done': ()}
        if record not in allowed_types[expected_state]:
            issue('STRUCTURE', row_no, raw=record, details=dict(
                  expected={'header': ['1'], 'first_data': ['2'], 'data': ['2', '8'],
                            'end': ['9'], 'done': ['EOF']}[expected_state],
                  actual=excerpt(record) if record else 'EMPTY_ROW'))
            return finish(True)
        rows.append(raw)
        if record == b'1':
            expected_state = 'first_data'
        elif record == b'2':
            count += 1
            result['dataCount'] = count
            expected_state = 'data'
            if count > max_records:
                issue('RECORD_LIMIT', row_no, details=dict(expected=max_records, actual=count))
                return finish(True)
        elif record == b'8':
            expected_state = 'end'
        else:
            expected_state = 'done'
        pos = line_end + (2 if ending == 'CRLF' else 1)
    if expected_state != 'done':
        issue('STRUCTURE_EOF', len(rows) + 1,
              details=dict(expected=['1', '2', '8', '9'], actual=expected_state.upper()))
        return finish(True)

    total, amount_complete = 0, True
    for row_no, raw in enumerate(rows, 1):
        layout = fields_for(raw)
        if len(raw) != 120:
            issue('RECORD_LENGTH', row_no, min(len(raw) + 1, 121), max(120, len(raw)),
                  'record', raw[120:], dict(expected=120, actual=len(raw)))
        tokens = decode_tokens(raw) if any(b not in ALLOWED_BYTES for b in raw) else []
        for token in tokens:
            if token['valid'] and token['char'] in ALLOWED and token['end'] == token['start']:
                continue
            field_code = next((f['code'] for f in layout if f['start'] <= token['start'] <= f['end']), 'outside_record')
            width = token['end'] - token['start'] + 1
            code = 'INVALID_CP932' if not token['valid'] else 'MULTIBYTE' if width > 1 else 'CHARSET'
            issue(code, row_no, token['start'], token['end'], field_code,
                  raw[token['start'] - 1:token['end']],
                  dict(expected='CP932_SINGLE_BYTE_ALLOWED', actual=code, width=width))
        if len(raw) != 120:
            issue('FIELD_ALIGNMENT_UNVERIFIED', row_no, 1, max(1, len(raw)), 'record',
                  details=dict(expected=120, actual=len(raw)), severity='unverified')
            if raw[:1] == b'2':
                amount_complete = False
            continue

        invalid_field_codes = set()
        for f in layout:
            segment = raw[f['start'] - 1:f['end']]
            common = dict(row=row_no, start=f['start'], end=f['end'], field_code=f['code'], raw=segment)
            numeric = all(48 <= b <= 57 for b in segment)
            if f['kind'] == 'N' and not numeric:
                invalid_field_codes.add(f['code'])
                issue('NUMERIC', details=dict(expected=dict(kind='DIGITS', length=len(segment)), actual='NON_NUMERIC'), **common)
            if f['kind'] == 'S' and segment != b' ' * len(segment):
                issue('PADDING', details=dict(expected='SPACE_0X20', actual='OTHER_BYTES'), **common)
            if f['required'] and f['kind'] == 'T' and not segment.strip(b' '):
                issue('REQUIRED', details=dict(expected='NON_EMPTY', actual='EMPTY'), **common)
            if f['values'] and not (f['kind'] == 'N' and not numeric):
                if segment not in [v.encode('ascii') for v in f['values']]:
                    issue('VALUE', details=dict(expected=list(f['values']), actual=excerpt(segment)), **common)
        if raw[:1] == b'1':
            if raw[1:3] in [v.encode() for v in TYPE_CODES] and raw[1:3] != type_code.encode():
                issue('TYPE_MISMATCH', row_no, 2, 3, 'type_code', raw[1:3],
                      dict(expected=type_code, actual=excerpt(raw[1:3])))
            if 'transfer_date' not in invalid_field_codes:
                try:
                    # No year in MMDD. A leap year avoids inventing a rejection of 0229.
                    datetime.date(2000, int(raw[54:56]), int(raw[56:58]))
                except ValueError:
                    issue('DATE', row_no, 55, 58, 'transfer_date', raw[54:58],
                          dict(expected='MMDD', actual=excerpt(raw[54:58])))
        elif raw[:1] == b'2':
            if 'amount' in invalid_field_codes or any(t['start'] <= 90 and t['end'] >= 81 and t['end'] > t['start'] for t in tokens):
                amount_complete = False
            else:
                total += int(raw[80:90])
            if raw[112:113] == b'Y':
                result['ediRows'] += 1
                issue('EDI_UNVERIFIED', row_no, 92, 113, 'edi_information', raw[91:113],
                      dict(expected='EXTERNAL_BUSINESS_RULE', actual='UNVERIFIED'), severity='unverified')
        elif raw[:1] == b'8':
            if 'total_count' not in invalid_field_codes:
                result['trailerCount'] = int(raw[1:7])
            if 'total_amount' not in invalid_field_codes:
                result['trailerAmount'] = int(raw[7:19])

    trailer_row = len(rows) - 1
    if result['trailerCount'] is not None:
        result['countMatches'] = result['trailerCount'] == count
        if not result['countMatches']:
            issue('COUNT_MISMATCH', trailer_row, 2, 7, 'total_count', rows[-2][1:7],
                  dict(expected=count, actual=result['trailerCount']))
    if amount_complete:
        result['totalAmount'] = str(total)
        if result['trailerAmount'] is not None:
            result['amountMatches'] = total == result['trailerAmount']
            if not result['amountMatches']:
                issue('AMOUNT_MISMATCH', trailer_row, 8, 19, 'total_amount', rows[-2][7:19],
                      dict(expected=str(total), actual=str(result['trailerAmount'])))
    else:
        issue('TOTAL_UNVERIFIED', trailer_row, 8, 19, 'total_amount',
              details=dict(expected='COMPLETE_VALID_AMOUNTS', actual='INSUFFICIENT_VALID_DATA'), severity='unverified')
    if result['trailerAmount'] is not None:
        result['trailerAmount'] = str(result['trailerAmount'])
    return finish()


def preview(raw):
    return dict(tokens=decode_tokens(raw), fields=fields_for(raw))
