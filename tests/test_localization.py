import json
from pathlib import Path
import subprocess
import unittest

from validator import FIELD_CODES, ISSUE_CODES


ROOT = Path(__file__).resolve().parents[1]


class LocalizationTests(unittest.TestCase):
    def locale_exports(self):
        script = """
import { fieldCopy, issueCopy, issueMessage } from './public/locale-vi.js';
console.log(JSON.stringify({
  fieldCodes: Object.keys(fieldCopy),
  issueCodes: Object.keys(issueCopy),
  crlf: issueMessage({ code: 'CRLF_LINE_ENDING' }),
}));
"""
        output = subprocess.check_output(
            ['node', '--input-type=module', '--eval', script], cwd=ROOT, text=True
        )
        return json.loads(output)

    def test_vietnamese_copy_covers_every_core_code(self):
        locale = self.locale_exports()
        self.assertEqual(set(locale['issueCodes']), set(ISSUE_CODES))
        self.assertEqual(set(locale['fieldCodes']), set(FIELD_CODES))
        self.assertIn('CRLF không hợp lệ', locale['crlf'])


if __name__ == '__main__':
    unittest.main()
