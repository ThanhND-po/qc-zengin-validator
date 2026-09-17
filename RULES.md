# Zengin Format Specification and Verification Rules

Version: `zengin-standard-120byte-v5-schema2-lf-only`

This document defines the byte-level layout, field constraints, character encodings, and verification rules implemented by **QC Zengin Validator**.

The rules are based on the standard banking specifications established by the **Japanese Bankers Association (全国銀行協会 - Zenginkyo / JBA)** for fixed 120-byte interbank file transfers (*全銀協 振込・振替データレコードフォーマット*), widely adopted across Japanese financial institutions (including MUFG, Mizuho, SMBC, and regional banks).

---

## 1. General File Specifications

| Specification | Requirement |
|---|---|
| **Record Length** | Exactly 120 payload bytes per record (excluding line delimiters). |
| **Character Encoding** | CP932 (Shift_JIS compatible, JIS X 0201 half-width Katakana and ASCII). Strictly no Byte Order Mark (BOM). |
| **Line Delimiters** | Every record, including End, must end with exactly one LF (`0x0A`). CRLF (`0x0D 0x0A`), standalone CR (`0x0D`), and a missing final LF are invalid. CRLF records remain inspectable, but they do not pass validation. |
| **Record Sequence** | Exactly one Header Record (`1`), one or more Data Records (`2`), exactly one Trailer Record (`8`), and exactly one End Record (`9`). No empty lines or trailing data after the End Record. |
| **Field Padding** | **Numeric (`N`)**: Right-aligned, zero-padded (`0`) on the left.<br>**Text / Alphanumeric (`C`)**: Left-aligned, space-padded (`0x20`) on the right.<br>**Dummy Fields**: Padded entirely with ASCII spaces (`0x20`). |

---

## 2. Header Record Layout (ヘッダ・レコード)

* **Data Division (データ区分)**: `1`

| Field Name | Japanese Name | Bytes (1-based) | Type & Length | Description / Rules |
|---|---|---|---|---|
| Data Division | データ区分 | 1 | Numeric(1) | Fixed value: `1` |
| Type Code | 種別コード | 2–3 | Numeric(2) | `21` (General / 総合振込), `11` (Salary / 給与振込), `12` (Bonus / 賞与振込), `71` or `72` (Direct Debit / 口座振替). Matches configured setting. |
| Code Division | コード区分 | 4 | Numeric(1) | Fixed value: `0` (JIS code) |
| Requester Code | 委託者コード | 5–14 | Numeric(10) | 10-digit company / requester ID |
| Requester Name | 委託者名 | 15–54 | Text(40) | Half-width allowed text, left-aligned; can be blank |
| Transfer Date | 取組日 | 55–58 | Numeric(4) | `MMDD` format with valid calendar date (e.g., `0415`). `0229` allowed as year is omitted. |
| Source Bank Code | 仕向金融機関番号 | 59–62 | Numeric(4) | 4-digit unified financial institution code |
| Source Bank Name | 仕向金融機関名 | 63–77 | Text(15) | Half-width allowed text, left-aligned; can be blank |
| Source Branch Code | 仕向支店番号 | 78–80 | Numeric(3) | 3-digit branch code |
| Source Branch Name | 仕向支店名 | 81–95 | Text(15) | Half-width allowed text, left-aligned; can be blank |
| Account Type | 預金種目 | 96 | Numeric(1) | `1` (Ordinary / 普通), `2` (Current / 当座), `4` (Savings / 貯蓄) |
| Account Number | 口座番号 | 97–103 | Numeric(7) | 7-digit bank account number, zero-padded |
| Dummy | ダミー | 104–120 | Space(17) | 17 ASCII spaces (`0x20`) |

---

## 3. Data Record Layout (データ・レコード)

* **Data Division (データ区分)**: `2`

| Field Name | Japanese Name | Bytes (1-based) | Type & Length | Description / Rules |
|---|---|---|---|---|
| Data Division | データ区分 | 1 | Numeric(1) | Fixed value: `2` |
| Destination Bank Code | 被仕向金融機関番号 | 2–5 | Numeric(4) | 4-digit receiving bank code |
| Destination Bank Name | 被仕向金融機関名 | 6–20 | Text(15) | Half-width allowed text, non-blank |
| Destination Branch Code | 被仕向支店番号 | 21–23 | Numeric(3) | 3-digit receiving branch code |
| Destination Branch Name | 被仕向支店名 | 24–38 | Text(15) | Half-width allowed text, non-blank |
| Clearing House No. | 手形交換所番号 | 39–42 | Numeric(4) | Usually `0000` |
| Account Type | 預金種目 | 43 | Numeric(1) | `1` (Ordinary / 普通), `2` (Current / 当座), `4` (Savings / 貯蓄) |
| Account Number | 口座番号 | 44–50 | Numeric(7) | 7-digit receiving account number, zero-padded |
| Beneficiary Name | 受取人名 | 51–80 | Text(30) | Half-width allowed Katakana/text, non-blank |
| Amount | 振込金額 | 81–90 | Numeric(10) | 10-digit transfer amount in integer Yen, zero-padded |
| New Code | 新規コード | 91 | Numeric(1) | Fixed value: `0` (First transfer / unchanged) |
| Customer Code 1 | 顧客コード1 | 92–101 | Text(10) | Used when EDI Flag is NOT `Y`. Allowed text. |
| Customer Code 2 | 顧客コード2 | 102–111 | Text(10) | Used when EDI Flag is NOT `Y`. Allowed text. |
| *EDI Information* | *EDI情報* | *92–111* | *Text(20)* | *20-byte combined field replacing Customer Codes 1 & 2 when EDI Flag is `Y`.* |
| Transfer Type | 振込区分 | 112 | Numeric(1) | Fixed value: `0` |
| EDI Flag | 識別表示 | 113 | Text(1) | Allowed character. `Y` activates EDI field branch; blank represents standard transfer. |
| Dummy | ダミー | 114–120 | Space(7) | 7 ASCII spaces (`0x20`) |

> **EDI Handling Note**: When EDI Flag is `Y`, bytes 92–111 are validated for character set and length, but flagged as `EDI_UNVERIFIED` because external business rules vary by financial institution.

---

## 4. Trailer Record Layout (トレーラ・レコード)

* **Data Division (データ区分)**: `8`

| Field Name | Japanese Name | Bytes (1-based) | Type & Length | Description / Rules |
|---|---|---|---|---|
| Data Division | データ区分 | 1 | Numeric(1) | Fixed value: `8` |
| Total Count | 合計件数 | 2–7 | Numeric(6) | 6-digit total number of Data Records. Reconciled strictly against actual counted records. |
| Total Amount | 合計金額 | 8–19 | Numeric(12) | 12-digit cumulative transfer sum. Reconciled strictly against actual sum of Data Record amounts using exact 64-bit integer arithmetic. |
| Dummy | ダミー | 20–120 | Space(101) | 101 ASCII spaces (`0x20`) |

---

## 5. End Record Layout (エンド・レコード)

* **Data Division (データ区分)**: `9`

| Field Name | Japanese Name | Bytes (1-based) | Type & Length | Description / Rules |
|---|---|---|---|---|
| Data Division | データ区分 | 1 | Numeric(1) | Fixed value: `9` |
| Dummy | ダミー | 2–120 | Space(119) | 119 ASCII spaces (`0x20`) |

---

## 6. Allowed Character Set

All characters must strictly occupy **1 byte** under CP932 / JIS X 0201 encoding.

* **Alphanumeric**: `0–9`, uppercase `A–Z`.
* **Half-width Katakana**:  
  `ｱ ｲ ｳ ｴ ｵ ｶ ｷ ｸ ｹ ｺ ｻ ｼ ｽ ｾ ｿ ﾀ ﾁ ﾂ ﾃ ﾄ ﾅ ﾆ ﾇ ﾈ ﾉ ﾊ ﾋ ﾌ ﾍ ﾎ ﾏ ﾐ ﾑ ﾒ ﾓ ﾔ ﾕ ﾖ ﾗ ﾘ ﾙ ﾚ ﾛ ﾜ ｦ ﾝ`
* **Half-width Kana Symbols**:  
  - Prolonged sound mark: `ｰ` (U+FF70, CP932 hex `0xB0`, 1 byte)  
  - Dakuten (voiced sound mark): `ﾞ` (U+FF9E, CP932 hex `0xDE`, 1 byte)  
  - Handakuten (semi-voiced sound mark): `ﾟ` (U+FF9F, CP932 hex `0xDF`, 1 byte)
* **Permitted Symbols & Punctuation**:  
  - Half-width space (`0x20`)  
  - Hyphen / minus: `-`  
  - Period: `.`  
  - Slash: `/`  
  - Parentheses: `(` and `)`  
  - Japanese brackets: `｢` and `｣`  
  - Yen sign / backslash: `\`
* **Strictly Prohibited**:
  - Full-width characters (e.g., `ー`, `ア`, `１`, `Ａ`).
  - Lowercase ASCII (`a–z`).
  - Unregistered CP932 multibyte characters or control codes (e.g., tabs, null bytes).

---

## 7. Verification Scope and Boundaries

1. **Syntax vs. Live Bank Verification**: The validator checks byte accuracy, schema adherence, character sets, and internal mathematical consistency. It does **not** connect to live banking networks or verify whether a given bank account, branch, or beneficiary exists.
2. **Deterministic Offline Execution**: Verification runs completely in memory within a local loopback server (`127.0.0.1`). Payload data is never transmitted across the network or stored in external databases.
3. **Leading Space Allowance**: Standard banking text fields allow leading and internal spaces. Fields are validated for allowed character bytes and dummy space padding without imposing overly restrictive trim constraints.
4. **Validation Status Outcomes**:
   - `valid`: All checks passed with zero errors or unverified fields.
   - `incomplete`: Syntax is valid, but contains unverified items (such as EDI payloads).
   - `invalid`: Syntax, character, length, or mathematical discrepancy errors were detected.
   - `stopped`: Verification aborted early due to structural failure (e.g., corrupt line endings) or exceeding configured record limit.

## 8. Validation Result Contract

The validator returns result schema version `2`. Core findings contain stable `code` and `fieldCode` identifiers, byte evidence, severity, and machine-readable `details`. The core does not return localized messages or display labels. QC Zengin Validator owns the Vietnamese presentation mapping in `public/locale-vi.js`.
