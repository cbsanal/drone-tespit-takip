"""İncelenmiş negatifleri ve korunmuş drone ayrımını yeni deneyde birleştirir."""
from pathlib import Path
import csv
import hashlib
import json
import random
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'task04-model-egitimi'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    candidates = json.loads((ROOT/'raporlar/negatif-adaylari.json').read_text())
    # Karanlık gökyüzünün güvenle incelenemediği kare dışarıda bırakılır.
    accepted = [r for r in candidates if r['dosya'] != '000000000359.jpg']
    groups = {r['dosya']: r['dosya'] for r in accepted}
    for numbers in [(192,357,488,544), (415,564), (322,589)]:
        names = [f'{n:012d}.jpg' for n in numbers]
        for name in names: groups[name] = names[0]
    grouped = {}
    for row in accepted: grouped.setdefault(groups[row['dosya']], []).append(row)
    rng = random.Random(42)
    assignments = {}
    # İnsan ve araç örnekleri her bölümde temsil edilsin.
    for vehicles in (True, False):
        keys = sorted(k for k, rows in grouped.items() if any(set(r['siniflar']) & {2,3,5,7} for r in rows) == vehicles)
        rng.shuffle(keys)
        n = max(1, round(len(keys)*.2))
        for i,key in enumerate(keys): assignments[key] = 'test' if i<n else ('val' if i<2*n else 'train')
    manifest = []
    for split in ('train','val','test'):
        for kind in ('images','labels'): (ROOT/'data'/kind/split).mkdir(parents=True,exist_ok=True)
        for image in sorted((OLD/'data/images'/split).iterdir()):
            shutil.copy2(image, ROOT/'data/images'/split/image.name)
            shutil.copy2(OLD/'data/labels'/split/(image.stem+'.txt'), ROOT/'data/labels'/split/(image.stem+'.txt'))
            manifest.append({'dosya':image.name,'split':split,'tur':'drone','grup':'onceki_'+split,'sha256':sha(image)})
    for row in accepted:
        name=row['dosya']; split=assignments[groups[name]]
        image=ROOT/'kaynak/coco128/images/train2017'/name
        with Image.open(image) as im: im.verify()
        new_name='coco_'+name
        shutil.copy2(image,ROOT/'data/images'/split/new_name)
        (ROOT/'data/labels'/split/('coco_'+Path(name).stem+'.txt')).write_text('')
        manifest.append({'dosya':new_name,'split':split,'tur':'negatif','grup':groups[name],'sha256':sha(image)})
    # Kamera kayıtları ancak ayrı inceleme listesindeki açık onaydan sonra eklenir.
    approved=ROOT/'raporlar/kamera-onay.json'
    if approved.exists():
        for i,row in enumerate(json.loads(approved.read_text(encoding='utf-8'))):
            image=ROOT/row['dosya']
            name=f'kamera_{i:03d}.jpg'
            shutil.copy2(image,ROOT/'data/images/train'/name)
            (ROOT/'data/labels/train'/Path(name).with_suffix('.txt')).write_text('')
            manifest.append({'dosya':name,'split':'train','tur':'kamera_negatif','grup':row['grup'],'sha256':sha(image)})
    seen={}
    for row in manifest:
        assert row['sha256'] not in seen, (row['dosya'],seen.get(row['sha256']))
        seen[row['sha256']]=row['dosya']
    with (ROOT/'raporlar/split-manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
    (ROOT/'data.yaml').write_text('path: '+json.dumps(str(ROOT/'data'),ensure_ascii=False)+'\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: drone\n',encoding='utf-8')
    (ROOT/'raporlar/negatif-inceleme.json').write_text(json.dumps({'kabul':[r['dosya'] for r in accepted],'dislanan':{'000000000359.jpg':'Karanlık sahne; güvenilir negatif kabul edilmedi.'},'yontem':'Gerçek fotoğrafların görsel incelemesi; COCO sınıf listesi yalnız aday seçimi için kullanıldı.','kamera_tamami':'Tek oturumun onaylı kareleri yalnız eğitimde; başarı kanıtı olarak bağımsız test sayılmaz.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print({s:{t:sum(r['split']==s and r['tur']==t for r in manifest) for t in ('drone','negatif','kamera_negatif')} for s in ('train','val','test')})

if __name__=='__main__':
    main()
