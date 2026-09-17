import unittest
from validator import validate, decode_tokens, fields_for, TYPE_CODES
from fixtures import sample, change


class ValidatorTests(unittest.TestCase):
    def codes(self, content, **kwargs):
        return {i['code'] for i in validate(content, **kwargs)['issues']}

    def test_valid_reconciles_independently(self):
        result = validate(sample())
        self.assertEqual((result['status'], result['dataCount'], result['totalAmount']), ('valid', 2, '25000'))
        self.assertTrue(result['countMatches'] and result['amountMatches'])
        self.assertEqual(result['rowLengths'], [120] * 5)

    def test_all_type_codes(self):
        for code in TYPE_CODES:
            with self.subTest(code=code):
                self.assertEqual(validate(sample(type_code=code), code)['status'], 'valid')

    def test_expected_type_mismatch_continues(self):
        result = validate(sample(type_code='11'))
        self.assertTrue(result['complete'])
        self.assertIn('TYPE_MISMATCH', {x['code'] for x in result['issues']})

    def test_unrecognized_type(self):
        self.assertIn('VALUE', self.codes(change(sample(), 1, 2, b'99')))

    def test_empty_file_stops(self):
        self.assertEqual(validate(b'')['status'], 'stopped')

    def test_bom_stops(self):
        self.assertEqual(validate(b'\xef\xbb\xbf' + sample())['issues'][0]['code'], 'BOM')

    def test_lf_valid_and_excluded_from_record_bytes(self):
        r = validate(sample())
        self.assertEqual(r['status'], 'valid')
        self.assertEqual(r['lineEndings'], {'LF': 5, 'CRLF': 0})
        self.assertEqual(r['fileBytes'], 605)
        self.assertEqual(r['rowLengths'], [120] * 5)

    def test_crlf_is_invalid_and_preserves_raw_evidence(self):
        import hashlib
        raw = sample(ending=b'\r\n')
        r = validate(raw)
        self.assertEqual((r['status'], r['complete'], r['errorCount']), ('invalid', True, 5))
        self.assertEqual(r['lineEndings'], {'LF': 0, 'CRLF': 5})
        self.assertEqual(r['fileBytes'], 610)
        self.assertEqual(r['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(r['totalAmount'], validate(sample())['totalAmount'])
        issue = r['issues'][0]
        self.assertEqual((issue['code'], issue['row'], issue['start'], issue['end'], issue['hex']),
                         ('CRLF_LINE_ENDING', 1, 121, 122, '0D 0A'))
        self.assertEqual(issue['fieldCode'], 'line_ending')
        self.assertEqual(issue['details'], {'expected': 'LF', 'actual': 'CRLF'})
        self.assertNotIn('message', issue)
        self.assertNotIn('field', issue)
        self.assertNotIn('expected', issue)
        self.assertNotIn('actual', issue)

    def test_mixed_lf_crlf_is_invalid_without_shifting_other_issues(self):
        raw = change(sample(), 3, 51, 'ア'.encode('cp932'), remove=1).replace(b'\n', b'\r\n', 1)
        r = validate(raw)
        self.assertTrue(r['complete'])
        self.assertEqual(r['status'], 'invalid')
        self.assertEqual(r['lineEndings'], {'LF': 4, 'CRLF': 1})
        line_issue = next(i for i in r['issues'] if i['code'] == 'CRLF_LINE_ENDING')
        self.assertEqual((line_issue['row'], line_issue['start'], line_issue['end'], line_issue['hex']), (1, 121, 122, '0D 0A'))
        issue = next(i for i in r['issues'] if i['code'] == 'MULTIBYTE')
        self.assertEqual((issue['row'], issue['start'], issue['end'], issue['hex']), (3, 51, 52, '83 41'))

    def test_cr_only_stops(self):
        self.assertIn('LINE_ENDING', self.codes(sample(ending=b'\r')))

    def test_bare_cr_after_lf_keeps_row_and_hex(self):
        raw = sample().replace(b'\n', b'\r', 2).replace(b'\r', b'\n', 1)
        i = validate(raw)['issues'][0]
        self.assertEqual((i['code'], i['row'], i['start'], i['hex']), ('LINE_ENDING', 2, 121, '0D'))

    def test_missing_final_line_ending(self):
        for ending in (b'\n', b'\r\n'):
            self.assertIn('MISSING_LINE_ENDING', self.codes(sample(ending=ending)[:-len(ending)]))

    def test_blank_extra_line(self):
        self.assertIn('STRUCTURE', self.codes(sample() + b'\n'))

    def test_missing_end(self):
        self.assertIn('STRUCTURE_EOF', self.codes(sample()[:-121]))

    def test_duplicate_header_and_unknown_division(self):
        for division in (b'1', b'7'):
            self.assertEqual(validate(change(sample(), 2, 1, division))['status'], 'stopped')

    def test_no_data_is_structural(self):
        self.assertEqual(validate(sample(0))['status'], 'stopped')

    def test_limit_boundary(self):
        self.assertEqual(validate(sample(3), max_records=3)['status'], 'valid')
        r = validate(sample(4), max_records=3)
        self.assertEqual((r['status'], r['dataCount'], r['issues'][0]['code']), ('stopped', 4, 'RECORD_LIMIT'))
        self.assertIsNone(r['totalAmount'])

    def test_custom_limit_above_default(self):
        r = validate(sample(10001), max_records=10001)
        self.assertEqual(r['status'], 'valid')

    def test_invalid_settings_rejected(self):
        for limit in (0, -1, 1000000, 1.5, True):
            with self.assertRaises(ValueError): validate(sample(), max_records=limit)

    def test_121_bytes_continues_and_preserves_evidence(self):
        data = change(sample(), 2, 51, 'ア'.encode('cp932'), remove=1)
        original = bytes(data)
        r = validate(data)
        self.assertEqual(r['rowLengths'][1], 121)
        self.assertTrue(r['complete'])
        issue = next(i for i in r['issues'] if i['code'] == 'MULTIBYTE')
        self.assertEqual((issue['row'], issue['start'], issue['end'], issue['hex'], issue['excerpt']), (2, 51, 52, '83 41', 'ア'))
        self.assertIsNone(r['totalAmount'])
        self.assertEqual(data, original)

    def test_multibyte_even_when_total_120(self):
        r = validate(change(sample(), 2, 51, 'ア'.encode('cp932'), remove=2))
        self.assertEqual(r['rowLengths'][1], 120)
        self.assertIn('MULTIBYTE', {i['code'] for i in r['issues']})

    def test_single_byte_overflow_not_falsely_multibyte(self):
        r = validate(change(sample(), 2, 121, b'A', remove=0))
        self.assertIn('RECORD_LENGTH', {i['code'] for i in r['issues']})
        self.assertNotIn('MULTIBYTE', {i['code'] for i in r['issues']})

    def test_short_row_continues(self):
        self.assertIn('RECORD_LENGTH', self.codes(change(sample(), 2, 120, b'', remove=1)))

    def test_invalid_byte_preserved(self):
        r = validate(change(sample(), 2, 51, b'\x81\x30'))
        i = next(i for i in r['issues'] if i['code'] == 'INVALID_CP932')
        self.assertEqual((i['start'], i['hex'], i['excerpt']), (51, '81', '<81>'))

    def test_lowercase_small_kana_and_control_rejected(self):
        for character in ('a', 'ｧ', '\t', '\x00'):
            self.assertIn('CHARSET', self.codes(change(sample(), 2, 51, character.encode('cp932'))))

    def test_halfwidth_long_sound_mark_in_beneficiary_name(self):
        raw = change(sample(), 2, 51, '000024040404ﾄｳｰ'.encode('cp932').ljust(30))
        result = validate(raw)
        self.assertEqual(result['status'], 'valid')
        token = decode_tokens(raw.split(b'\n')[1])[64]
        self.assertEqual((token['char'], token['hex'], token['start'], token['end']), ('ｰ', 'B0', 65, 65))

    def test_fullwidth_long_sound_mark_still_rejected(self):
        raw = change(sample(), 2, 51, 'ー'.encode('cp932'), remove=2)
        issue = next(i for i in validate(raw)['issues'] if i['code'] == 'MULTIBYTE')
        self.assertEqual((issue['excerpt'], issue['start'], issue['end']), ('ー', 51, 52))

    def test_all_defined_kana_characters(self):
        from validator import ALLOWED
        for character in ALLOWED:
            if character == ' ': continue
            r = validate(change(sample(), 2, 51, character.encode('cp932')))
            self.assertNotIn('CHARSET', {i['code'] for i in r['issues']}, character)

    def test_required_name_empty(self):
        self.assertIn('REQUIRED', self.codes(change(sample(), 2, 51, b' ' * 30)))

    def test_leading_spaces_valid(self):
        self.assertEqual(validate(change(sample(), 2, 51, b'  TEST'.ljust(30)))['status'], 'valid')

    def test_numeric_space_and_bad_account_type(self):
        self.assertIn('NUMERIC', self.codes(change(sample(), 2, 44, b' ')))
        self.assertIn('VALUE', self.codes(change(sample(), 2, 43, b'9')))

    def test_dummy_and_unused_zero_padding(self):
        for row, col in ((1, 104), (2, 114), (4, 20), (5, 2)):
            self.assertIn('PADDING', self.codes(change(sample(), row, col, b'A')))
        self.assertIn('VALUE', self.codes(change(sample(), 2, 39, b'1111')))

    def test_amount_error_never_becomes_zero(self):
        r = validate(change(sample(), 2, 81, b'A'))
        self.assertIsNone(r['totalAmount'])
        self.assertIsNone(r['amountMatches'])
        self.assertIn('TOTAL_UNVERIFIED', {i['code'] for i in r['issues']})

    def test_independent_count_and_amount_mismatch(self):
        data = change(change(sample(), 4, 2, b'000003'), 4, 8, b'000000000001')
        self.assertTrue({'COUNT_MISMATCH', 'AMOUNT_MISMATCH'} <= self.codes(data))

    def test_bad_trailer_numbers(self):
        r = validate(change(sample(), 4, 2, b'A'))
        self.assertIsNone(r['countMatches'])
        self.assertTrue(r['amountMatches'])

    def test_invalid_date_and_leap_day(self):
        self.assertIn('DATE', self.codes(change(sample(), 1, 55, b'0230')))
        self.assertEqual(validate(change(sample(), 1, 55, b'0229'))['status'], 'valid')

    def test_edi_y_is_incomplete_not_error(self):
        content = change(sample(), 2, 113, b'Y')
        r = validate(content)
        self.assertEqual((r['status'], r['errorCount'], r['ediRows']), ('incomplete', 0, 1))
        field = next(f for f in fields_for(content.split(b'\n')[1]) if f['code'] == 'edi_information')
        self.assertEqual((field['start'], field['end']), (92, 111))

    def test_edi_character_errors_still_found(self):
        self.assertIn('CHARSET', self.codes(change(change(sample(), 2, 113, b'Y'), 2, 92, b'a')))

    def test_untruncated_error_list(self):
        r = validate(sample(150).replace(b'TEST BANK', b'tEST BANK'))
        self.assertGreater(r['errorCount'], 100)
        self.assertEqual(r['errorCount'], len(r['issues']))

    def test_preview_tokens_keep_byte_ranges(self):
        tokens = decode_tokens(b'A' + 'ア'.encode('cp932') + b'\x81')
        self.assertEqual([(x['start'], x['end']) for x in tokens], [(1, 1), (2, 3), (4, 4)])
        self.assertEqual(tokens[-1]['hex'], '81')


if __name__ == '__main__': unittest.main()
