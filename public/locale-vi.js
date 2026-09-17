export const issueCopy = {
  EMPTY_FILE: 'File không có dữ liệu.',
  BOM: 'File có BOM nên record đầu không bắt đầu đúng tại byte 1.',
  MISSING_LINE_ENDING: 'Record chưa kết thúc bằng LF bắt buộc.',
  CRLF_LINE_ENDING: 'Final Zengin file chỉ chấp nhận LF; CRLF không hợp lệ.',
  LINE_ENDING: 'CR đứng riêng không phải line ending hợp lệ.',
  STRUCTURE: 'Thiếu, thừa hoặc sai thứ tự record.',
  STRUCTURE_EOF: 'File kết thúc trước khi hoàn thành cấu trúc bắt buộc.',
  RECORD_LIMIT: 'File vượt giới hạn Data Records đang áp dụng.',
  RECORD_LENGTH: 'Record không có đúng 120 encoded bytes, không tính line ending.',
  INVALID_CP932: 'Byte sequence không decode được bằng CP932.',
  MULTIBYTE: 'Ký tự chiếm nhiều hơn một encoded byte.',
  CHARSET: 'Ký tự không thuộc allowed character set.',
  FIELD_ALIGNMENT_UNVERIFIED: 'Không thể xác minh field alignment và totals vì record sai độ dài.',
  NUMERIC: 'Numeric field chỉ chấp nhận digits 0-9 và zero-padding bên trái.',
  PADDING: 'Reserved field chỉ được chứa half-width spaces.',
  REQUIRED: 'Required field đang trống.',
  VALUE: 'Giá trị không thuộc active rule set.',
  TYPE_MISMATCH: 'Type Code trong Header không khớp Settings.',
  DATE: 'Transfer Date không phải giá trị MMDD hợp lệ.',
  EDI_UNVERIFIED: 'Chưa xác minh nội dung nghiệp vụ EDI; format và bytes vẫn được kiểm tra.',
  COUNT_MISMATCH: 'Trailer Total Count không khớp số Data Records.',
  AMOUNT_MISMATCH: 'Trailer Total Amount không khớp tổng Amount của Data Records.',
  TOTAL_UNVERIFIED: 'Không đủ dữ liệu hợp lệ để tính và đối chiếu toàn bộ Amount.',
};

export const fieldCopy = {
  file: 'File',
  record: 'Record',
  line_ending: 'Ký tự xuống dòng',
  outside_record: 'Ngoài record',
  data_division: 'Data Division',
  type_code: 'Type Code',
  code_division: 'Code Division',
  requester_code: 'Requester Code',
  requester_name: 'Requester Name',
  transfer_date: 'Transfer Date',
  source_bank_code: 'Source Bank Code',
  source_bank_name: 'Source Bank Name',
  source_branch_code: 'Source Branch Code',
  source_branch_name: 'Source Branch Name',
  account_type: 'Account Type',
  account_number: 'Account Number',
  dummy: 'Dummy',
  destination_bank_code: 'Destination Bank Code',
  destination_bank_name: 'Destination Bank Name',
  destination_branch_code: 'Destination Branch Code',
  destination_branch_name: 'Destination Branch Name',
  clearing_house_number: 'Clearing House No.',
  beneficiary_name: 'Beneficiary Name',
  amount: 'Amount',
  new_code: 'New Code',
  customer_code_1: 'Customer Code 1',
  customer_code_2: 'Customer Code 2',
  transfer_type: 'Transfer Type',
  edi_flag: 'EDI Flag (識別表示)',
  edi_information: 'EDI Information (識別表示)',
  total_count: 'Total Count',
  total_amount: 'Total Amount',
};

export function issueMessage(issue) {
  return issueCopy[issue.code] || `Rule set trả về issue code chưa được hỗ trợ: ${issue.code}.`;
}

export function fieldLabel(fieldCode) {
  return fieldCopy[fieldCode] || `Field chưa xác định (${fieldCode})`;
}

function technicalValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (value && typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}=${technicalValue(item)}`).join(', ');
  return String(value ?? 'không có');
}

export function issueDetails(issue) {
  const details = issue.details || {};
  const parts = [];
  if (Object.hasOwn(details, 'expected')) parts.push(`Kỳ vọng: ${technicalValue(details.expected)}`);
  if (Object.hasOwn(details, 'actual')) parts.push(`Thực tế: ${technicalValue(details.actual)}`);
  for (const [key, value] of Object.entries(details)) {
    if (key !== 'expected' && key !== 'actual') parts.push(`${key}: ${technicalValue(value)}`);
  }
  return parts.join(' · ');
}
