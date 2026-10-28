"""Modeli, ayrılmış veriyi, kodları ve sonuçları yerel ZIP paketine toplar."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    destination = ROOT.parent / 'task04-paylasim-paketi.zip'
    excluded = {'.venv', '.ultralytics', '.opencv4', '__pycache__'}
    files = []
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in excluded for part in relative.parts):
            continue
        if path.suffix == '.cache' or path.name == 'yolo26n.pt':
            continue
        if relative.parts[0] == 'runs' and 'weights' in relative.parts:
            continue
        if path.name.endswith('-orijinal.jpg') or path.name.endswith('kurulum.log'):
            continue
        files.append(path)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, ROOT.name + '/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    with destination.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'dosya': destination.name, 'dosya_sayisi': len(files), 'bayt': destination.stat().st_size, 'sha256': digest}
    destination.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
