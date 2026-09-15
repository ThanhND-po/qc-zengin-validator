# QC Zengin Validator

> Standalone, offline, byte-level inspector and validation utility for Japanese Zengin (全銀) fixed-length interbank transfer files.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

---

### Language / Ngôn ngữ
- [English Documentation](#english)
- [Tài liệu Tiếng Việt](#tiếng-việt)

---

## English

### Overview

**QC Zengin Validator** is a high-precision, lightweight desktop-grade utility designed for Quality Assurance (QA/QC) engineers, software developers, and financial operations teams who work with Japanese banking data. It performs strict, byte-level parsing and validation of Zengin fixed-length text files against official interbank specifications.

> **Local-Only Execution Notice**: This application is intentionally built to run purely in your local environment via loopback (`127.0.0.1`). It is **not** a hosted cloud web service. Because Zengin files frequently contain sensitive financial details (bank account numbers, branch codes, recipient names, and transaction amounts), all file reading, CP932 decoding, and payload verifications are executed entirely in volatile memory on your local machine. No data is ever sent to external servers, cloud databases, or telemetry services.

### Key Highlights

- **Zero External Dependencies**: Pure Python standard library backend and vanilla browser UI. No `npm install` or `pip install` required.
- **Byte-Level Precision**: Validates exact 120-byte records, Shift_JIS / CP932 byte encoding, dummy padding, numeric zero-padding, and alphanumeric alignments.
- **Multibyte & Malformed Detection**: Instantly detects and flags illegal full-width characters, lowercase ASCII, and invalid CP932 sequences with exact row, byte range, and hex dump coordinates.
- **Interactive Visual Inspector**: Switch between an interactive **Byte Grid** and a **TXT view** with character and hex preview, direct error navigation, and row/byte positioning.
- **Trailer & Mathematical Reconciliation**: Verifies Data Record counts and cumulative transfer amounts against Trailer records using exact 64-bit integer arithmetic.
- **EDI Information Support**: Automatically switches parsing mode for bytes 92–111 when the EDI flag is set to `Y`.
- **Exportable Audit Logs**: Download comprehensive, line-by-line verification logs formatted as UTF-8 TXT.

### Supported Type Codes

In accordance with Japanese Bankers Association (全銀協) standards:
- **`21`**: General Transfer (総合振込 - Sōgō Furikomi)
- **`11`**: Salary Transfer (給与振込 - Kyūyo Furikomi)
- **`12`**: Bonus Transfer (賞与振込 - Shōyo Furikomi)
- **`71` / `72`**: Direct Debit / Account Transfer (口座振替 - Kōza Furikae)

For complete byte offsets and field layouts, refer to [RULES.md](RULES.md).

---

### Prerequisites

- **Node.js**: Version 18+ (includes `node` and `npm`)
- **Python**: Version 3.9+ (Python standard library only)
- **Browser**: Google Chrome, Mozilla Firefox, Apple Safari, or Microsoft Edge

---

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ThanhND-po/qc-zengin-validator.git
   cd qc-zengin-validator
   ```

2. **Launch the local server**:
   ```bash
   npm run dev
   ```

3. **Open the application**:
   Open **http://127.0.0.1:4173** in your web browser. (Press `Ctrl + C` in your terminal to stop).

#### Environment Variables

- **Custom Port**:
  ```bash
  PORT=4174 npm run dev
  ```
- **Custom Python Interpreter**:
  ```bash
  PYTHON=/usr/local/bin/python3 npm run dev
  ```
- **Higher Record Limits**:
  ```bash
  MAX_DATA_RECORDS=50000 npm run dev
  ```

---

### How to Use

1. **Configure Settings**: Select your expected Type Code (default `21`) and maximum Data Records limit (default `10,000`). Click **Save Settings**.
2. **Verify File**: Drag and drop a `.txt` Zengin file into the upload zone or browse your filesystem. Verification runs instantly.
3. **Inspect Metrics**: View total record count, cumulative amount, Trailer balance status, and categorized error items.
4. **Byte Grid Navigation**: Click any error in the list to jump directly to its row and byte position. Click any cell to inspect its field name, byte range, character, and raw hex representation.
5. **Download Log**: Click **Download Verification Log** to save all errors, warnings, and unverified items to a UTF-8 text file.

---

### Validation Scope

- **Encoding**: CP932 / Shift_JIS compatible, strictly no BOM.
- **Record Length**: Exactly 120 payload bytes per record.
- **Line Endings**: LF (`0x0A`) terminated by default. CRLF (`0x0D 0x0A`) is automatically supported and handled per record. Standalone CR or missing line breaks are flagged as structural errors.
- **Structural Integrity**: Exactly 1 Header (`1`), $\ge 1$ Data (`2`), 1 Trailer (`8`), 1 End (`9`) in strict chronological sequence. No empty lines or trailing data.
- **Allowed Character Set**: Half-width Katakana (`ｱ`–`ﾝ`), prolonged sound mark `ｰ` (`0xB0`), uppercase `A`–`Z`, `0`–`9`, and permitted half-width symbols (` `, `.`, `/`, `-`, `(`, `)`, `｢`, `｣`, `\`).
- **Trailer Balance**: Exact mathematical match between Data record counts/amounts and Trailer values.

---

### Performance & Testing

- **Benchmark**: Validates **10,000 Data Records (~1.2 MB)** in approximately **0.21 seconds** on standard modern hardware.
- **Automated Tests**: 44 test cases covering CP932 parsing, line ending variations, exact byte boundary checks, and loopback HTTP handlers:
  ```bash
  npm test
  ```
- **Benchmark Command**:
  ```bash
  npm run benchmark
  ```
- **Create Standalone Archive**:
  ```bash
  npm run share
  ```

---

## Tiếng Việt

### Tổng quan

**QC Zengin Validator** là công cụ kiểm tra và phân tích cấu trúc file chuyển tiền ngân hàng Nhật Bản (chuẩn Zengin - 全銀フォーマット) ở mức độ raw bytes (từng byte nhị phân). Công cụ được thiết kế chuyên biệt cho kỹ sư kiểm thử (QC/QA), lập trình viên và chuyên viên vận hành tài chính.

> **Lưu ý quan trọng về thực thi Local**: Ứng dụng này được thiết kế **hoàn toàn để chạy offline trên máy cá nhân** qua địa chỉ loopback (`127.0.0.1`), **không phải webapp triển khai public trên đám mây**. Do file Zengin thường chứa dữ liệu nhạy cảm (số tài khoản, tên người thụ hưởng, chi nhánh ngân hàng, số tiền), toàn bộ quá trình đọc file, phân tích CP932 và đối soát diễn ra 100% trong bộ nhớ tạm (RAM) của máy tính. Không có bất kỳ dữ liệu nào được lưu trữ vào database hay gửi ra dịch vụ ngoài.

### Điểm nổi bật

- **Không cần cài đặt thư viện ngoài**: Backend dùng thuần Python Standard Library, giao diện Web thuần JavaScript/CSS. Không cần chạy `npm install` hay `pip install`.
- **Độ chính xác cấp độ byte**: Kiểm tra nghiêm ngặt 120 bytes/record, bảng mã CP932 (Shift_JIS), căn lề số/chữ, padding số 0 và khoảng trắng chuẩn ngân hàng.
- **Phát hiện ký tự multibyte và lỗi định dạng**: Chỉ rõ dòng, khoảng byte (1-based) và mã hex của các ký tự toàn giác (full-width), chữ thường, hoặc ký tự ngoài bảng mã.
- **Giao diện trực quan Byte Grid & TXT**: Chuyển đổi linh hoạt giữa lưới byte và chế độ văn bản, hỗ trợ phím điều hướng, xem chi tiết từng ô byte kèm mã hex.
- **Đối chiếu số học Trailer**: Khớp số lượng bản ghi Data và tổng số tiền lũy kế với Trailer bằng số nguyên chính xác tuyệt đối.
- **Hỗ trợ cờ EDI**: Tự động chuyển đổi chế độ kiểm tra trường thông tin EDI (bytes 92–111) khi cờ EDI mang giá trị `Y`.
- **Xuất nhật ký kiểm tra**: Cho phép tải toàn bộ danh sách lỗi và mục chưa xác minh dưới dạng file TXT UTF-8 hoàn chỉnh.

### Các loại nghiệp vụ hỗ trợ

Tuân thủ quy chuẩn của Hiệp hội Ngân hàng Nhật Bản (全国銀行協会 - 全銀協):
- **`21`**: Chuyển tiền tổng hợp (総合振込 - General Transfer)
- **`11`**: Chuyển lương (給与振込 - Salary Transfer)
- **`12`**: Chuyển thưởng (賞与振込 - Bonus Transfer)
- **`71` / `72`**: Trích nợ tự động / Chuyển khoản tài khoản (口座振替 - Direct Debit)

Chi tiết quy cách từng byte và quy tắc nghiệp vụ xem tại [RULES.md](RULES.md).

---

### Yêu cầu môi trường

- **Node.js**: Phiên bản 18+ (kèm `npm`)
- **Python**: Phiên bản 3.9+ (chỉ dùng thư viện chuẩn có sẵn của Python)
- **Trình duyệt**: Google Chrome, Mozilla Firefox, Apple Safari hoặc Microsoft Edge

---

### Khởi chạy nhanh

1. **Clone repository về máy**:
   ```bash
   git clone https://github.com/ThanhND-po/qc-zengin-validator.git
   cd qc-zengin-validator
   ```

2. **Khởi động server local**:
   ```bash
   npm run dev
   ```

3. **Truy cập ứng dụng**:
   Mở trình duyệt tại **http://127.0.0.1:4173**. (Nhấn `Ctrl + C` trên Terminal để dừng server).

#### Tùy chỉnh cổng và Python

- **Đổi cổng port**:
  ```bash
  PORT=4174 npm run dev
  ```
- **Chỉ định đường dẫn Python**:
  ```bash
  PYTHON=/usr/bin/python3 npm run dev
  ```
- **Tăng giới hạn bản ghi kiểm tra**:
  ```bash
  MAX_DATA_RECORDS=50000 npm run dev
  ```

---

### Cách sử dụng

1. **Cấu hình Settings**: Chọn Type Code kỳ vọng (mặc định `21`) và giới hạn Data Records tối đa (mặc định `10.000`). Bấm **Lưu cấu hình**.
2. **Kiểm tra file**: Kéo thả hoặc chọn file `.txt` Zengin cần xác minh. App sẽ tự động phân tích ngay lập tức.
3. **Xem kết quả**: Xem số lượng Data Records thực tế, tổng số tiền, trạng thái đối chiếu Trailer và danh sách chi tiết lỗi.
4. **Điều hướng Byte Grid**: Bấm vào bất kỳ dòng lỗi nào để tự động cuộn đến vị trí dòng và byte tương ứng. Nhấp vào ô byte để xem chi tiết tên field, khoảng byte, ký tự hiển thị và mã hex.
5. **Tải log kiểm tra**: Bấm **Tải log kiểm tra** để lưu toàn bộ kết quả phát hiện về máy dưới dạng file text UTF-8.

---

### Phạm vi kiểm tra

- **Mã hóa**: Tương thích CP932 / Shift_JIS, tuyệt đối không có BOM.
- **Độ dài bản ghi**: Đúng 120 bytes dữ liệu cho mỗi record.
- **Ký tự xuống dòng**: Mặc định LF (`0x0A`). Tự động hỗ trợ CRLF (`0x0D 0x0A`) theo từng dòng. Dòng có CR đứng riêng hoặc thiếu xuống dòng ở cuối file sẽ bị báo lỗi cấu trúc.
- **Trình tự cấu trúc**: Bắt buộc gồm 1 Header (`1`), $\ge 1$ Data (`2`), 1 Trailer (`8`), 1 End (`9`) đúng thứ tự. Không có dòng trống hoặc dữ liệu thừa sau End.
- **Bộ ký tự cho phép**: Katakana nửa độ rộng (`ｱ`–`ﾝ`), dấu trường âm bán giác `ｰ` (`0xB0`), chữ hoa La-tinh `A`–`Z`, chữ số `0`–`9`, và các ký hiệu nửa độ rộng hợp lệ (` `, `.`, `/`, `-`, `(`, `)`, `｢`, `｣`, `\`).
- **Đối soát Trailer**: Khớp số học chính xác tuyệt đối giữa số bản ghi và tổng tiền thực tế với số liệu khai báo ở Trailer.

---

### Hiệu năng và Kiểm thử

- **Hiệu năng thực tế**: Kiểm tra file **10.000 bản ghi (~1.2 MB)** chỉ mất khoảng **0.21 giây** trên máy tính cá nhân tiêu chuẩn.
- **Bộ kiểm thử tự động**: 44 test suites kiểm chứng toàn diện từ engine lõi, các trường hợp encoding/line endings đến API loopback:
  ```bash
  npm test
  ```
- **Chạy đo kiểm hiệu năng**:
  ```bash
  npm run benchmark
  ```
- **Đóng gói file ZIP chia sẻ**:
  ```bash
  npm run share
  ```

---

## Project Structure

```text
qc-zengin-validator/
├── public/          # Giao diện người dùng (HTML, CSS, JS)
├── validator.py     # Engine thuần Python kiểm tra cấu trúc 120 bytes & mã hóa CP932
├── server.py        # Server local loopback (127.0.0.1) an toàn, không telemetry
├── tests/           # Dữ liệu mẫu tổng hợp và kịch bản test tự động
├── scripts/         # Bộ script tiện ích (launcher, benchmark, samples generator)
├── RULES.md         # Tài liệu đặc tả kỹ thuật và quy tắc 120 bytes chuẩn 全銀協
├── package.json     # Cấu hình package và scripts khởi chạy
└── LICENSE          # Giấy phép mã nguồn mở MIT
```

---

## License

Dự án được phát hành theo giấy phép [MIT License](LICENSE).
