import { fieldCopy, fieldLabel, issueCopy, issueDetails, issueMessage } from './locale-vi.js';

const $ = id => document.getElementById(id);
const icons = {
  scan: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h4"/>',
  settings: '<path d="M10 4h4l.5 2 1.5 .9 2-.6 2 3.4-1.5 1.4v1.8l1.5 1.4-2 3.4-2-.6-1.5 .9-.5 2h-4l-.5-2-1.5-.9-2 .6-2-3.4 1.5-1.4v-1.8L4 9.7l2-3.4 2 .6L9.5 6Z"/><circle cx="12" cy="12" r="3"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  home: '<path d="m3 10 9-7 9 7M5 9v11h5v-6h4v6h5V9"/>',
  upload: '<path d="M7 16H6a4 4 0 0 1-1-8 7 7 0 0 1 13-1 4.5 4.5 0 0 1 0 9h-1M12 20V10m-4 4 4-4 4 4"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
  file: '<path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10l-7-7Zm0 0v7h7M8 14h8M8 17h5"/>',
  refresh: '<path d="M5 8a8 8 0 0 1 14 0M19 3v5h-5M19 16a8 8 0 0 1-14 0M5 21v-5h5"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  alert: '<path d="m12 3 10 18H2L12 3ZM12 9v5M12 17v.1"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.file}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
const nf = new Intl.NumberFormat('vi-VN');
const number = n => nf.format(n);
const money = n => n === null ? 'Chưa xác định' : `${nf.format(BigInt(n))} ¥`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const visible = value => String(value ?? '').replaceAll(' ', '·').replaceAll('\t', '⇥');
const storageKey = 'zengin-validator.settings.v1';
const pageSize = 20;
let config = { defaultLimit: 10000, maxUploadBytes: 16777216, typeCodes: ['21', '11', '71', '12', '72'], issueCodes: [], fieldCodes: [] };
let settings = { typeCode: '21', maxRecords: 10000 };
let file = null, bytes = null, rows = [], result = null, localFailure = null;
let aborter = null, timer = null, runId = 0, previewId = 0, page = 0, byteStart = 1, mode = 'grid', selection = null, lastPreview = [];
let issuesByRow = new Map();
const sameSettings = (a, b) => a.typeCode === b.typeCode && a.maxRecords === b.maxRecords;
function showError(message) { $('app-error').textContent = message; $('app-error').hidden = !message; }
function validSettings(s) { return s && config.typeCodes.includes(s.typeCode) && Number.isInteger(s.maxRecords) && s.maxRecords >= 1 && s.maxRecords <= 999999; }
function syncSettings() {
  $('active-type').textContent = settings.typeCode;
  $('active-limit').textContent = number(settings.maxRecords);
  $('setting-type').value = settings.typeCode;
  $('setting-limit').value = settings.maxRecords;
  $('stale-notice').hidden = !result || sameSettings(settings, result.settings);
}
function route() {
  const isSettings = location.hash === '#settings';
  $('settings-page').hidden = !isSettings;
  $('verify-page').hidden = isSettings;
  $('nav-settings').classList.toggle('active', isSettings);
  $('nav-verify').classList.toggle('active', !isSettings);
  $('nav-settings').setAttribute('aria-current', isSettings ? 'page' : 'false');
  $('nav-verify').setAttribute('aria-current', isSettings ? 'false' : 'page');
  $('breadcrumb').textContent = isSettings ? 'Settings' : 'Kiểm tra file';
  document.title = `Zengin Validator · ${isSettings ? 'Settings' : 'Kiểm tra file'}`;
}
window.addEventListener('hashchange', route);
route();
try {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error();
  config = await response.json();
  const missingIssueCopy = config.issueCodes.filter(code => !issueCopy[code]);
  const missingFieldCopy = config.fieldCodes.filter(code => !fieldCopy[code]);
  if (config.resultSchemaVersion !== 2 || missingIssueCopy.length || missingFieldCopy.length) throw new Error();
  settings.maxRecords = config.defaultLimit;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (validSettings(saved)) settings = saved;
  } catch { /* Only configuration is persisted; corrupt storage falls back to defaults. */ }
} catch { showError('Không kết nối được server local. Kiểm tra terminal npm run dev rồi tải lại trang.'); }
syncSettings();
$('upload-hint').textContent = `Tối đa ${number(config.maxUploadBytes / 1048576)} MiB mỗi file. Dữ liệu chỉ xử lý trên máy này.`;
$('technical-limit').textContent = `Giới hạn kỹ thuật hiện tại: ${number(config.maxUploadBytes / 1048576)} MiB/file. Có thể đổi bằng ENV MAX_UPLOAD_BYTES khi khởi động app.`;
$('settings-form').addEventListener('submit', event => {
  event.preventDefault();
  const next = { typeCode: $('setting-type').value, maxRecords: Number($('setting-limit').value) };
  if (!validSettings(next)) { $('settings-message').textContent = 'Cấu hình không hợp lệ.'; return; }
  settings = next;
  try {
    localStorage.setItem(storageKey, JSON.stringify(settings));
    $('settings-message').textContent = 'Đã lưu cấu hình trên browser này. Áp dụng cho lần kiểm tra tiếp theo.';
  } catch { $('settings-message').textContent = 'Đã áp dụng trong phiên. Browser không cho phép lưu Settings lâu dài.'; }
  syncSettings();
});
$('reset-settings').addEventListener('click', () => {
  $('setting-type').value = '21'; $('setting-limit').value = config.defaultLimit;
  $('settings-message').textContent = 'Đã điền giá trị mặc định. Chọn Lưu cấu hình để áp dụng.';
});
function clearFile() {
  runId++; previewId++; aborter?.abort(); aborter = null; clearInterval(timer);
  file = null; bytes = null; rows = []; result = null; localFailure = null; lastPreview = []; issuesByRow.clear();
  $('file-input').value = ''; $('file-bar').hidden = true; $('dropzone').hidden = false;
  $('results').hidden = true; $('progress').hidden = true; $('empty-state').hidden = false;
  $('download-log').hidden = true; $('stale-notice').hidden = true;
  $('rerun').disabled = false;
  $('byte-grid').querySelector('tbody').replaceChildren(); $('text-scroll').replaceChildren(); $('issue-list').replaceChildren();
  $('filename').textContent = ''; showError('');
}
$('clear').addEventListener('click', clearFile);
$('dropzone').addEventListener('click', () => $('file-input').click());
$('replace').addEventListener('click', () => $('file-input').click());
$('file-input').addEventListener('change', event => { if (event.target.files[0]) useFile(event.target.files[0]); });
for (const name of ['dragenter', 'dragover']) $('dropzone').addEventListener(name, event => { event.preventDefault(); $('dropzone').classList.add('dragging'); });
for (const name of ['dragleave', 'drop']) $('dropzone').addEventListener(name, () => $('dropzone').classList.remove('dragging'));
$('dropzone').addEventListener('drop', event => {
  event.preventDefault();
  if (event.dataTransfer.files.length !== 1) { showError('Vui lòng chọn một file TXT mỗi lần.'); return; }
  useFile(event.dataTransfer.files[0]);
});
async function useFile(chosen) {
  clearFile();
  if (!/\.txt$/i.test(chosen.name)) { showError('Chỉ hỗ trợ file .TXT. File chưa được kiểm tra.'); return; }
  file = chosen;
  $('filename').textContent = chosen.name;
  $('file-meta').textContent = `${number(chosen.size)} bytes · TXT · Chỉ tồn tại trong phiên`;
  $('file-bar').hidden = false; $('dropzone').hidden = true; $('empty-state').hidden = true;
  if (chosen.size > config.maxUploadBytes) {
    localFailure = `Vượt giới hạn dung lượng: ${number(chosen.size)} bytes; tối đa ${number(config.maxUploadBytes)} bytes. Dừng trước khi đọc file.`;
    showError(localFailure); $('download-log').hidden = false; return;
  }
  const id = runId;
  try { const buffer = await chosen.arrayBuffer(); if (id !== runId) return; bytes = new Uint8Array(buffer); await run(); }
  catch { if (id === runId) showError('Không đọc được file đã chọn. Vui lòng chọn lại.'); }
}
async function indexRows(id) {
  const indexed = []; let start = 0;
  for (let i = 0; i < bytes.length; i++) {
    if (bytes[i] === 13 || bytes[i] === 10) {
      const ending = bytes[i] === 13 && bytes[i + 1] === 10 ? 'CRLF' : bytes[i] === 13 ? 'CR' : 'LF';
      indexed.push({ start, end: i, ending });
      if (ending === 'CRLF') i++;
      start = i + 1;
    }
    if (i % 262144 === 0) { await new Promise(requestAnimationFrame); if (id !== runId) return null; }
  }
  if (start < bytes.length) indexed.push({ start, end: bytes.length, ending: 'thiếu ký tự xuống dòng' });
  return indexed;
}
async function run() {
  if (!bytes) return;
  const id = ++runId; previewId++; aborter?.abort(); aborter = new AbortController();
  const applied = { ...settings }; result = null; selection = null; page = 0; byteStart = 1; localFailure = null;
  $('results').hidden = true; $('progress').hidden = false; $('download-log').hidden = true; $('stale-notice').hidden = true;
  $('rerun').disabled = true; showError('');
  const start = performance.now(); $('elapsed').textContent = '0 giây'; clearInterval(timer);
  timer = setInterval(() => { $('elapsed').textContent = `${((performance.now() - start) / 1000).toFixed(1)} giây`; }, 100);
  try {
    const response = await fetch('/api/verify', { method: 'POST', headers: {
      'Content-Type': 'application/octet-stream', 'X-Type-Code': applied.typeCode, 'X-Max-Records': String(applied.maxRecords),
    }, body: bytes, signal: aborter.signal });
    const data = await response.json(); if (id !== runId) return;
    if (!response.ok) throw new Error(data.error || 'Không thể kiểm tra file.');
    const indexed = await indexRows(id); if (!indexed || id !== runId) return;
    rows = indexed; result = data;
    issuesByRow = new Map();
    for (const issue of result.issues) { if (!issuesByRow.has(issue.row)) issuesByRow.set(issue.row, []); issuesByRow.get(issue.row).push(issue); }
    result.clientDurationMs = Math.round(performance.now() - start);
    renderResult(); await renderPreview();
  } catch (error) {
    if (id !== runId || error.name === 'AbortError') return;
    localFailure = error.message; showError(error.message); $('download-log').hidden = false;
  } finally {
    if (id === runId) { clearInterval(timer); $('progress').hidden = true; $('rerun').disabled = false; }
  }
}
$('rerun').addEventListener('click', run);
$('cancel').addEventListener('click', () => {
  runId++; previewId++; aborter?.abort(); clearInterval(timer); $('progress').hidden = true; $('rerun').disabled = false;
  showError('Đã hủy chờ kết quả. Bạn có thể thay file hoặc kiểm tra lại. Server local có thể cần hoàn tất request đang chạy.');
});
function renderResult() {
  $('results').hidden = false; $('download-log').hidden = false;
  syncSettings();
  const status = result.status;
  const warning = status === 'incomplete';
  const bad = status === 'invalid' || status === 'stopped';
  $('status-banner').className = `status-banner ${bad ? 'error' : warning ? 'warning' : ''}`;
  $('status-icon').innerHTML = icon(bad || warning ? 'alert' : 'check');
  $('status-title').textContent = { valid: 'Hợp lệ trong phạm vi rule set đã kiểm tra', invalid: 'Phát hiện lỗi trong file', incomplete: 'Chưa xác minh đầy đủ', stopped: 'Đã dừng kiểm tra' }[status];
  $('status-description').textContent = status === 'valid' ? 'Cấu trúc, field và control totals khớp các quy tắc đang áp dụng.'
    : `${number(result.errorCount)} lỗi · ${number(result.unverifiedCount)} mục chưa xác minh.${result.complete ? '' : ' Các phần còn lại chưa được kiểm tra.'}`;
  $('duration').textContent = `${(result.clientDurationMs / 1000).toFixed(2)} giây`;
  $('metric-count').textContent = `${result.complete ? '' : '≥ '}${number(result.dataCount)}`;
  $('metric-count-detail').textContent = result.complete ? `Trailer: ${result.trailerCount === null ? 'chưa đọc được' : number(result.trailerCount)} records` : 'Số đã gặp trước khi dừng, không phải tổng toàn file';
  $('metric-amount').textContent = money(result.totalAmount);
  $('metric-amount-detail').textContent = `Trailer: ${money(result.trailerAmount)}`;
  $('metric-trailer').textContent = result.countMatches === false || result.amountMatches === false ? 'Không khớp'
    : result.countMatches === true && result.amountMatches === true ? 'Khớp' : 'Chưa đủ dữ liệu';
  $('metric-trailer-detail').textContent = 'Đối chiếu độc lập số lượng và tổng Amount';
  $('preview-subtitle').textContent = `${number(rows.length)} dòng vật lý · CP932 · line ending ngoài 120 bytes`;
  $('jump-row').max = Math.max(1, rows.length);
  $('issue-badge').textContent = number(result.issues.length);
  $('issue-summary').textContent = `${number(result.errorCount)} lỗi, ${number(result.unverifiedCount)} mục chưa xác minh${result.complete ? '' : ' trước khi dừng'}`;
  $('issue-limit-note').hidden = result.issues.length <= 100;
  $('issue-list').innerHTML = result.issues.length ? result.issues.slice(0, 100).map((issue, i) => `
    <button class="issue-button" data-issue="${i}"><span class="issue-meta ${issue.severity === 'unverified' ? 'unverified' : ''}">${issue.severity === 'unverified' ? 'CHƯA XÁC MINH' : 'LỖI'} <span>· Dòng ${number(issue.row)}</span></span><strong>${esc(fieldLabel(issue.fieldCode))}</strong><p>${esc(issueMessage(issue))}</p><p>Byte ${number(issue.start)}${issue.end !== issue.start ? '–' + number(issue.end) : ''}</p>${issue.excerpt ? `<code>${esc(visible(issue.excerpt).slice(0, 140))}</code>` : ''}</button>`).join('')
    : `<div class="issue-empty"><span>${icon('check')}</span><h2>Không phát hiện lỗi</h2><p>Chọn một byte trong preview để xem chi tiết field.</p></div>`;
  $('issue-list').querySelectorAll('[data-issue]').forEach(button => button.addEventListener('click', () => {
    const index = Number(button.dataset.issue); const issue = result.issues[index];
    $('issue-list').querySelectorAll('.active').forEach(el => el.classList.remove('active')); button.classList.add('active');
    selection = { row: issue.row, byte: issue.start, issue };
    $('jump-row').value = Math.min(issue.row, Math.max(1, rows.length)); $('jump-byte').value = issue.start;
    page = Math.floor((Math.min(issue.row, rows.length) - 1) / pageSize); byteStart = Math.floor((issue.start - 1) / 120) * 120 + 1;
    mode = 'grid'; syncMode(); renderPreview();
    $('cell-detail').textContent = `${issue.code} · ${issueMessage(issue)}${issueDetails(issue) ? ' · ' + issueDetails(issue) : ''}${issue.hex ? ' · Hex: ' + issue.hex.slice(0, 600) : ''}`;
  }));
  $('result-provenance').textContent = `${result.ruleVersion} · Type Code ${result.settings.typeCode} · Limit ${number(result.settings.maxRecords)} · ${new Date(result.checkedAt).toLocaleString('vi-VN')} · Không xác nhận ngân hàng sẽ tiếp nhận file.`;
}
function toBase64(array) { let text = ''; for (const b of array) text += String.fromCharCode(b); return btoa(text); }
function affected(row, byte) { return (issuesByRow.get(row) || []).find(i => i.start <= byte && i.end >= byte); }
async function renderPreview() {
  if (!result || !bytes) return;
  const id = ++previewId;
  const from = Math.max(0, page * pageSize), subset = rows.slice(from, from + pageSize);
  $('preview-loading').hidden = false;
  try {
    const payload = subset.map(row => {
      // Walk CP932 token boundaries up to the requested byte window, preserving multibyte pairs.
      let offset = 0, target = Math.min(byteStart - 1, row.end - row.start);
      while (offset < target) {
        const b = bytes[row.start + offset]; const lead = (b >= 0x81 && b <= 0x9f) || (b >= 0xe0 && b <= 0xfc);
        if (lead && offset + 1 >= target) break;
        offset += lead ? 2 : 1;
      }
      return { bytes: toBase64(bytes.subarray(row.start + offset, Math.min(row.end, row.start + offset + 360))), offset,
        prefix: toBase64(bytes.subarray(row.start, Math.min(row.end, row.start + 120))) };
    });
    const response = await fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error();
    const views = await response.json(); if (id !== previewId) return;
    lastPreview = subset.map((row, index) => ({ ...row, ...views[index], number: from + index + 1 }));
    drawPreview();
  } catch { if (id === previewId) $('cell-detail').textContent = 'Không đọc được preview. Kiểm tra kết nối server local và thử chuyển trang.'; }
  finally { if (id === previewId) $('preview-loading').hidden = true; }
}
function drawPreview() {
  if (!lastPreview.length) { $('byte-grid').querySelector('tbody').replaceChildren(); return; }
  const maxLength = Math.max(120, ...lastPreview.map(r => r.end - r.start));
  const byteEnd = Math.min(Math.max(byteStart + 119, maxLength), byteStart + 239);
  const columns = Array.from({ length: byteEnd - byteStart + 1 }, (_, i) => i + byteStart);
  $('byte-grid').querySelector('thead').innerHTML = `<tr><th scope="col">Dòng / Loại</th>${columns.map(c => `<th scope="col">${c}</th>`).join('')}</tr>`;
  const spaces = $('show-spaces').checked;
  $('byte-grid').querySelector('tbody').innerHTML = lastPreview.map(row => {
    const byByte = new Map(); for (const token of row.tokens) for (let i = token.start; i <= token.end; i++) byByte.set(i, token);
    const names = { 49: 'Header', 50: 'Data', 56: 'Trailer', 57: 'End' };
    const fieldStarts = new Set(row.fields.map(f => f.start));
    return `<tr><th scope="row">${row.number} · ${names[bytes[row.start]] || '?'}</th>${columns.map(col => {
      const token = byByte.get(col), issue = affected(row.number, col);
      let label = token ? (col > token.start ? '↳' : token.valid ? token.char : '×') : '';
      if (label === ' ') label = spaces ? '·' : ' ';
      const field = row.fields.find(f => f.start <= col && col <= f.end);
      const classes = [fieldStarts.has(col) ? 'field-start' : '', token?.char === ' ' ? 'space' : '', col > 120 ? 'overflow-cell' : '', issue ? issue.severity === 'unverified' ? 'unverified-cell' : 'error-cell' : '', selection?.row === row.number && selection?.byte === col ? 'selected-cell' : ''].filter(Boolean).join(' ');
      const title = `Dòng ${row.number} · byte ${col} · ${field ? fieldLabel(field.code) : 'Ngoài record'} · ${token?.hex || 'không có byte'}${issue ? ' · ' + issueMessage(issue) : ''}`;
      return `<td data-row="${row.number}" data-byte="${col}" tabindex="${col === byteStart ? '0' : '-1'}" class="${classes}" aria-label="${esc(title)}" title="${esc(title)}">${esc(label)}</td>`;
    }).join('')}</tr>`;
  }).join('');
  $('text-scroll').innerHTML = lastPreview.map(row => `<div class="text-row"><span class="text-row-number">${row.number}</span><span>${row.tokens.filter(t => t.start >= byteStart && t.start <= byteEnd).map(t => {
    const label = t.valid ? (spaces ? visible(t.char) : t.char) : `<${t.hex}>`;
    const issue = affected(row.number, t.start);
    return issue ? `<mark class="${issue.severity === 'unverified' ? 'unverified' : ''}" title="${esc(issueMessage(issue))}">${esc(label)}</mark>` : esc(label);
  }).join('')}</span><span class="eol">${row.end - row.start > byteEnd ? '… còn bytes phía sau' : esc(row.ending)}</span></div>`).join('');
  $('page-label').textContent = `Dòng ${lastPreview[0].number}–${lastPreview.at(-1).number} / ${number(rows.length)} · byte ${byteStart}–${byteEnd}`;
  $('previous').disabled = page === 0; $('next').disabled = (page + 1) * pageSize >= rows.length;
  const selectedCell = $('byte-grid').querySelector('.selected-cell');
  if (selectedCell) selectedCell.scrollIntoView({ block: 'nearest', inline: 'center' });
}
$('byte-grid').addEventListener('click', event => {
  const cell = event.target.closest('[data-byte]'); if (!cell) return;
  const rowNum = Number(cell.dataset.row), byte = Number(cell.dataset.byte);
  const row = lastPreview.find(r => r.number === rowNum), token = row.tokens.find(t => t.start <= byte && t.end >= byte);
  const field = row.fields.find(f => f.start <= byte && f.end >= byte), issue = affected(rowNum, byte);
  selection = { row: rowNum, byte };
  $('byte-grid').querySelector('.selected-cell')?.classList.remove('selected-cell'); cell.classList.add('selected-cell');
  $('cell-detail').textContent = `Dòng ${rowNum}, byte ${byte} · ${field ? fieldLabel(field.code) : 'Ngoài record'}${field ? ` (${field.start}–${field.end})` : ''} · Ký tự: ${token ? token.valid ? visible(token.char) : 'không decode được' : 'không có byte'} · Hex: ${token?.hex || 'không có'}${token ? ` · ${token.end - token.start + 1} byte(s)` : ''}${issue ? ' · ' + issueMessage(issue) : ''}`;
});
$('byte-grid').addEventListener('keydown', event => {
  const cell = event.target.closest('[data-byte]'); if (!cell) return;
  if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); cell.click(); return; }
  const delta = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[event.key];
  if (!delta) return;
  event.preventDefault();
  const target = $('byte-grid').querySelector(`[data-row="${Number(cell.dataset.row) + delta[0]}"][data-byte="${Number(cell.dataset.byte) + delta[1]}"]`);
  if (target) { cell.tabIndex = -1; target.tabIndex = 0; target.focus(); target.click(); }
});
function syncMode() { $('grid-scroll').hidden = mode !== 'grid'; $('text-scroll').hidden = mode !== 'text'; $('grid-mode').setAttribute('aria-pressed', String(mode === 'grid')); $('text-mode').setAttribute('aria-pressed', String(mode === 'text')); }
$('grid-mode').addEventListener('click', () => { mode = 'grid'; syncMode(); });
$('text-mode').addEventListener('click', () => { mode = 'text'; syncMode(); });
$('show-spaces').addEventListener('change', drawPreview);
$('previous').addEventListener('click', () => { if (page > 0) { page--; renderPreview(); } });
$('next').addEventListener('click', () => { if ((page + 1) * pageSize < rows.length) { page++; renderPreview(); } });
$('jump-form').addEventListener('submit', event => {
  event.preventDefault(); const row = Number($('jump-row').value), byte = Number($('jump-byte').value);
  if (!Number.isInteger(row) || row < 1 || row > rows.length || !Number.isInteger(byte) || byte < 1 || byte > Math.max(120, rows[row - 1].end - rows[row - 1].start) + 1) return;
  selection = { row, byte }; page = Math.floor((row - 1) / pageSize); byteStart = Math.floor((byte - 1) / 120) * 120 + 1; renderPreview();
});
$('download-log').addEventListener('click', () => {
  if (!file) return;
  const log = ['ZENGIN VALIDATOR - LOG KIỂM TRA', `File: ${JSON.stringify(file.name)}`, `Thời điểm: ${result?.checkedAt || new Date().toISOString()}`];
  if (result) {
    log.push(`Rule set: ${result.ruleVersion}`, `Line endings đã đọc: LF=${result.lineEndings.LF}; CRLF=${result.lineEndings.CRLF}; final file chỉ chấp nhận LF`, `SHA-256: ${result.sha256}`, `Settings: Type Code=${result.settings.typeCode}; max Data Records=${result.settings.maxRecords}`,
      `Trạng thái: ${$('status-title').textContent}`, `Kiểm tra toàn bộ: ${result.complete ? 'Có' : 'Không'}`,
      `Data Records ${result.complete ? 'thực tế' : 'đã gặp trước khi dừng'}: ${result.dataCount}`, `Tổng tiền: ${money(result.totalAmount)}`,
      `Trailer Count: ${result.trailerCount ?? 'Chưa xác định'}`, `Trailer Amount: ${money(result.trailerAmount)}`,
      `Lỗi: ${result.errorCount}; Chưa xác minh: ${result.unverifiedCount}`, `Thời gian engine: ${result.durationMs} ms`,
      'Log bao gồm tất cả mục đã phát hiện; các phần sau điểm dừng chưa được kiểm tra.', '');
    result.issues.forEach((i, index) => log.push(`[${index + 1}] ${i.severity === 'error' ? 'LỖI' : 'CHƯA XÁC MINH'} ${i.code}`,
      `Dòng ${i.row}; byte ${i.start}–${i.end}; field ${fieldLabel(i.fieldCode)}`, issueMessage(i),
      `Chi tiết kỹ thuật: ${issueDetails(i) || '(không áp dụng)'}`,
      `Chuỗi gốc (JSON escaped): ${JSON.stringify(i.excerpt)}`, `Hex: ${i.hex || '(không có bytes)'}`, ''));
  } else log.push(`Đã dừng: ${localFailure || 'Chưa có kết quả'}`);
  const url = URL.createObjectURL(new Blob([log.join('\r\n')], { type: 'text/plain;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = file.name.replace(/\.txt$/i, '') + '.verification-log.txt'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
