import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const candidates = process.env.PYTHON ? [process.env.PYTHON] : ['python3', 'python'];
const python = candidates.find(command => {
  const check = spawnSync(command, ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'], { stdio: 'ignore' });
  return check.status === 0;
});
if (!python) {
  console.error('Cần Python 3.9 trở lên. Cài Python rồi chạy lại npm run dev. Có thể chọn interpreter bằng ENV PYTHON.');
  process.exit(1);
}
const mode = process.argv[2];
const args = mode === '--test' ? ['-m', 'unittest', 'discover', '-s', 'tests', '-v']
  : mode === '--benchmark' ? ['scripts/benchmark.py']
  : mode === '--share' ? ['scripts/share.py'] : ['server.py'];
const child = spawn(python, ['-B', ...args], {
  cwd: path.resolve(root), stdio: 'inherit', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('error', () => { console.error('Không thể khởi động Python.'); process.exitCode = 1; });
child.on('exit', (code, signal) => { process.exitCode = signal === 'SIGINT' ? 0 : (code ?? 0); });
