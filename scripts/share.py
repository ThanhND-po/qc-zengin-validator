"""Explicit allowlist archive: excludes user uploads, local settings, secrets and repo history."""
from pathlib import Path
import datetime
import zipfile
from samples import samples

root = Path(__file__).resolve().parents[1]
output = root / 'dist'
output.mkdir(exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
archive = output / f'zengin-validator-{stamp}.zip'
files = ['package.json', 'README.md', 'RULES.md', 'VALIDATION.md', 'server.py', 'validator.py', '.gitignore']
for directory, pattern in [('public', '*'), ('scripts', '*.py'), ('scripts', '*.mjs'), ('tests', '*.py')]:
    files.extend(str(p.relative_to(root)) for p in (root / directory).glob(pattern) if p.is_file())
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
    for name in sorted(set(files)):
        bundle.write(root / name, 'zengin-validator/' + name)
    for name, raw in samples().items():
        bundle.writestr('zengin-validator/samples/' + name, raw)
print('ZIP:', archive)
