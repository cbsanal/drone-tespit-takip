"""Task 02: Orijinalleri değiştirmeden görüntü ve Pascal VOC etiketlerini inceler."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('Dataset'))
    parser.add_argument('--output', type=Path, default=Path('task02-veri-hazirligi'))
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    reports = output / 'raporlar'
    review = output / 'inceleme'
    reports.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.rglob('*') if p.is_file())
    images = [p for p in files if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}]
    xmls = {p.relative_to(source).with_suffix('').as_posix(): p for p in files if p.suffix.lower() == '.xml'}
    inventory, problems, boxes, fingerprints, hashes = [], [], [], [], []
    for path in files:
        hashes.append({'dosya': path.relative_to(source).as_posix(), 'bayt': path.stat().st_size, 'sha256': sha256(path)})
    hash_map = {row['dosya']: row['sha256'] for row in hashes}
    for index, path in enumerate(images):
        rel = path.relative_to(source).as_posix()
        key = path.relative_to(source).with_suffix('').as_posix()
        row = {'dosya': rel, 'format': '', 'genislik': 0, 'yukseklik': 0, 'xml': '', 'nesne_sayisi': 0, 'hata': ''}
        errors = []
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                row.update(format=im.format, genislik=im.width, yukseklik=im.height)
                rgb = im.convert('RGB')
                small = np.asarray(rgb.resize((32, 32)), dtype=np.float32)
                gray = np.asarray(rgb.convert('L').resize((9, 8)))
                dhash = sum(int(bit) << bit_index for bit_index, bit in enumerate((gray[:, 1:] > gray[:, :-1]).flat))
                pixels = hashlib.sha256(rgb.size[0].to_bytes(4, 'big') + rgb.size[1].to_bytes(4, 'big') + rgb.tobytes()).hexdigest()
                fingerprints.append((rel, dhash, small, pixels))
        except Exception as exc:
            errors.append('goruntu_okunamiyor: ' + str(exc))
        label = xmls.get(key)
        if label is None:
            errors.append('etiket_eksik')
        else:
            row['xml'] = label.relative_to(source).as_posix()
            try:
                annotation = ET.parse(label).getroot()
                if annotation.findtext('filename') != path.name:
                    errors.append('xml_dosya_adi_uyusmuyor')
                width = int(annotation.findtext('size/width', '0'))
                height = int(annotation.findtext('size/height', '0'))
                if (width, height) != (row['genislik'], row['yukseklik']):
                    errors.append('xml_cozunurlugu_uyusmuyor')
                objects = annotation.findall('object')
                row['nesne_sayisi'] = len(objects)
                for number, obj in enumerate(objects, 1):
                    name = obj.findtext('name', '').strip()
                    coords = [float(obj.findtext('bndbox/' + tag, 'nan')) for tag in ('xmin', 'ymin', 'xmax', 'ymax')]
                    x1, y1, x2, y2 = coords
                    valid = bool(name) and all(np.isfinite(coords)) and 0 <= x1 < x2 <= row['genislik'] and 0 <= y1 < y2 <= row['yukseklik']
                    if not valid:
                        errors.append(f'gecersiz_kutu_{number}')
                    area = (x2-x1)*(y2-y1)
                    boxes.append({'dosya': rel, 'nesne': number, 'sinif': name, 'xmin': x1, 'ymin': y1, 'xmax': x2, 'ymax': y2, 'genislik': x2-x1, 'yukseklik': y2-y1, 'alan_orani': area/(row['genislik']*row['yukseklik']) if row['genislik']*row['yukseklik'] else 0, 'alan_1024_alti': valid and area < 1024, 'gecerli': valid})
            except Exception as exc:
                errors.append('xml_okunamiyor: ' + str(exc))
        row['hata'] = '; '.join(errors)
        inventory.append(row)
        for error in errors:
            problems.append({'dosya': rel, 'sorun': error})
    image_keys = {p.relative_to(source).with_suffix('').as_posix() for p in images}
    for key, path in xmls.items():
        if key not in image_keys:
            problems.append({'dosya': path.relative_to(source).as_posix(), 'sorun': 'goruntu_eksik'})
    pairs = []
    parent = {f[0]: f[0] for f in fingerprints}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, (name1, hash1, thumb1, pixel1) in enumerate(fingerprints):
        for name2, hash2, thumb2, pixel2 in fingerprints[i+1:]:
            distance = (hash1 ^ hash2).bit_count()
            exact = hash_map[name1] == hash_map[name2]
            pixel_exact = pixel1 == pixel2
            if not (exact or pixel_exact or distance <= 4):
                continue
            rmse = float(np.sqrt(np.mean((thumb1-thumb2)**2)))
            if exact or pixel_exact or rmse <= 12:
                kind = 'birebir_dosya' if exact else 'ayni_pikseller' if pixel_exact else 'benzerlik_adayi'
                pairs.append({'dosya1': name1, 'dosya2': name2, 'tur': kind, 'dhash_mesafesi': distance, 'rmse_32': round(rmse, 4)})
                parent[find(name2)] = find(name1)
    roots = sorted({find(name) for name in parent})
    group_ids = {name: i+1 for i, name in enumerate(roots)}
    groups = [{'dosya': name, 'grup': group_ids[find(name)]} for name in parent]
    save_csv(reports/'dosya-envanteri.csv', inventory, list(inventory[0]))
    save_csv(reports/'etiket-kontrolu.csv', problems, ['dosya', 'sorun'])
    save_csv(reports/'kutular.csv', boxes, ['dosya','nesne','sinif','xmin','ymin','xmax','ymax','genislik','yukseklik','alan_orani','alan_1024_alti','gecerli'])
    save_csv(reports/'sha256.csv', hashes, ['dosya','bayt','sha256'])
    save_csv(reports/'tekrarlar.csv', pairs, ['dosya1','dosya2','tur','dhash_mesafesi','rmse_32'])
    save_csv(reports/'benzerlik-gruplari.csv', groups, ['dosya','grup'])
    valid_boxes = [b for b in boxes if b['gecerli']]
    summary = {'dosya_sayisi': len(files), 'goruntu_sayisi': len(images), 'xml_sayisi': len(xmls), 'toplam_bayt': sum(h['bayt'] for h in hashes), 'formatlar': dict(Counter(r['format'] for r in inventory)), 'cozunurlukler': dict(Counter(f"{r['genislik']}x{r['yukseklik']}" for r in inventory)), 'sorun_sayisi': len(problems), 'sorunlu_goruntu_sayisi': sum(bool(r['hata']) for r in inventory), 'kutu_sayisi': len(boxes), 'siniflar': dict(Counter(b['sinif'] for b in boxes)), 'kucuk_kutu_alan_1024_alti': sum(b['alan_1024_alti'] for b in valid_boxes), 'alan_orani_yuzde1_alti': sum(b['alan_orani'] < .01 for b in valid_boxes), 'sifir_nesneli_xml_goruntu': sum(r['nesne_sayisi']==0 and bool(r['xml']) and not r['hata'] for r in inventory), 'tekrar_ciftleri': dict(Counter(p['tur'] for p in pairs)), 'benzerlik_grubu_sayisi': len(roots), 'alt_klasorler': [p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_dir()]}
    (reports/'ozet.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    # Tam görüntü ve mevcut etiketten alınan nesne görünümü yalnızca inceleme içindir.
    box_map = defaultdict(list)
    for box in valid_boxes:
        box_map[box['dosya']].append(box)
    for start in range(0, len(images), 60):
        sheet = Image.new('RGB', (1500, 1440), 'white')
        draw = ImageDraw.Draw(sheet)
        for offset, path in enumerate(images[start:start+60]):
            x, y = (offset % 5)*300, (offset//5)*120
            rel = path.relative_to(source).as_posix()
            with Image.open(path) as im:
                rgb = im.convert('RGB')
                thumb = rgb.copy()
                thumb.thumbnail((195, 95))
                sheet.paste(thumb, (x, y+20))
                if box_map[rel]:
                    b = box_map[rel][0]
                    crop = rgb.crop((max(0,b['xmin']-4), max(0,b['ymin']-4), min(rgb.width,b['xmax']+4), min(rgb.height,b['ymax']+4)))
                    crop.thumbnail((100,95))
                    sheet.paste(crop, (x+198,y+20))
            draw.text((x+2,y+2), f'{start+offset+1}: {path.name}', fill='black')
        sheet.save(review/f'pafta-{start//60+1:02}.jpg', quality=90)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
