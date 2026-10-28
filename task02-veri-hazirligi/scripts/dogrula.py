"""Orijinal dosyaların ve seçilen kopyaların SHA-256 bütünlüğünü doğrular."""
from pathlib import Path
import csv
import json
from veri_analizi import sha256

root = Path('task02-veri-hazirligi')
rows = list(csv.DictReader((root/'raporlar/sha256.csv').open(encoding='utf-8-sig')))
local = {r['dosya']: r for r in rows}
assert {p.name for p in Path('Dataset').iterdir() if p.is_file()} == set(local)
assert all(sha256(Path('Dataset')/r['dosya']) == r['sha256'] for r in rows)
archive = json.loads((root/'kaynak/arsiv-sha256.json').read_text(encoding='utf-8-sig'))
assert sha256(Path('dataset_xml_format.rar')).lower() == archive['Hash'].lower()
selected = list(csv.DictReader((root/'raporlar/secilen-sha256.csv').open(encoding='utf-8-sig')))
assert {p.name for p in (root/'secilen').iterdir()} == {r['dosya'] for r in selected}
assert all(sha256(root/'secilen'/r['dosya']) == r['sha256'] == local[r['dosya']]['sha256'] for r in selected)
preview = list((root/'onizleme').iterdir())
assert len(preview) == 10 and all(sha256(p) == local[p.name]['sha256'] for p in preview)
result = {'orijinal_dosya_dogrulandi': len(rows), 'orijinal_rar_degismedi': True, 'secilen_kopyalar_dogrulandi': len(selected), 'onizleme_dogrulandi': len(preview), 'not': 'RAR ve açılmış klasörün kendi başlangıç özetleri doğrulandı; RAR içeriğinin açılmış dosyalarla bayt eşitliği doğrulanmadı.'}
(root/'raporlar/butunluk-dogrulama.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
