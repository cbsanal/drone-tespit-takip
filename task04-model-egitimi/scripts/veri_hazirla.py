"""Mevcut XML kutularını YOLO biçimine çevirir; sahne gruplarını birlikte tutar."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import random
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent/'task02-veri-hazirligi/secilen'
REPORTS = ROOT/'raporlar'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    files=sorted(p for p in SOURCE.iterdir() if p.suffix.lower() in {'.png','.jpg'})
    names={p.name for p in files}
    parent={p.name:p.name for p in files}
    # Önce tüm kaynak envanterindeki benzerlik bağlantılarını birleştir.
    pairs=list(csv.DictReader((ROOT.parent/'task02-veri-hazirligi/raporlar/birlesik-benzerlik-adaylari.csv').open(encoding='utf-8-sig')))
    for pair in pairs:
        for key in ('dosya1','dosya2'):
            parent.setdefault(pair[key],pair[key])
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def join(a,b):
        parent[find(b)]=find(a)
    for pair in pairs:
        join(pair['dosya1'],pair['dosya2'])
    for prefix in ('foto','moto','yoto'):
        group=sorted(n for n in names if n.startswith(prefix))
        for n in group[1:]: join(group[0],n)
    extra=json.loads((REPORTS/'genis-benzerlik-taramasi.json').read_text())
    for pair in extra: join(pair['dosya1'],pair['dosya2'])
    # Kaynak fotoğrafı/sahnesi benzer görünen kadrajlar için muhafazakâr gruplar.
    for group in [('pic_097.jpg','pic_241.jpg'),('pic_260.jpg','pic_312.jpg','pic_386.jpg','pic_331.jpg'),('pic_1127.jpg','pic_403.jpg','pic_517.jpg','pic_532.jpg','pic_838.jpg')]:
        for n in group[1:]: join(group[0],n)
    groups={}
    for name in sorted(names): groups.setdefault(find(name),[]).append(name)
    assigned={}
    for key,group in groups.items():
        if any(n.startswith('foto') for n in group): assigned[key]='test'
        elif any(n.startswith('yoto') for n in group): assigned[key]='val'
        elif any(n.startswith('moto') for n in group): assigned[key]='train'
    remaining=sorted(k for k in groups if k not in assigned)
    random.Random(42).shuffle(remaining)
    for split,target in [('test',11),('val',10)]:
        count=sum(len(groups[k]) for k,s in assigned.items() if s==split)
        for key in remaining:
            if key not in assigned and count+len(groups[key])<=target:
                assigned[key]=split; count+=len(groups[key])
    for key in remaining: assigned.setdefault(key,'train')
    manifest=[]
    for key,group in sorted(groups.items()):
        split=assigned[key]
        image_dir=ROOT/'data/images'/split; label_dir=ROOT/'data/labels'/split
        image_dir.mkdir(parents=True,exist_ok=True); label_dir.mkdir(parents=True,exist_ok=True)
        for name in group:
            image=SOURCE/name; xml=image.with_suffix('.xml')
            annotation=ET.parse(xml).getroot()
            assert annotation.findtext('filename')==name
            width=int(annotation.findtext('size/width')); height=int(annotation.findtext('size/height'))
            lines=[]; small=0
            for obj in annotation.findall('object'):
                assert obj.findtext('name')=='drone'
                x1,y1,x2,y2=[float(obj.findtext('bndbox/'+n)) for n in ['xmin','ymin','xmax','ymax']]
                assert 0<=x1<x2<=width and 0<=y1<y2<=height
                values=[(x1+x2)/(2*width),(y1+y2)/(2*height),(x2-x1)/width,(y2-y1)/height]
                lines.append('0 '+' '.join(f'{v:.10f}' for v in values))
                small+=(x2-x1)*(y2-y1)<1024
                xc,yc,bw,bh=map(float,lines[-1].split()[1:])
                assert max(abs(a-b) for a,b in zip([x1,y1,x2,y2],[(xc-bw/2)*width,(yc-bh/2)*height,(xc+bw/2)*width,(yc+bh/2)*height]))<1e-5
            assert lines
            shutil.copy2(image,image_dir/name)
            (label_dir/(image.stem+'.txt')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
            manifest.append({'dosya':name,'split':split,'sahne_grubu':key,'kutu':len(lines),'kucuk_kutu':small,'sha256':digest(image),'xml_sha256':digest(xml)})
    assert len(manifest)==70
    assert all(len({r['split'] for r in manifest if r['sahne_grubu']==key})==1 for key in groups)
    assert len({r['sha256'] for r in manifest})==70
    with (REPORTS/'split-manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0])); writer.writeheader(); writer.writerows(manifest)
    # Mutlak yol her çalıştırmada yerel bilgisayara göre yeniden üretilir.
    (ROOT/'data.yaml').write_text('path: '+json.dumps((ROOT/'data').as_posix(),ensure_ascii=False)+'\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: drone\n',encoding='utf-8')
    summary={split:{'goruntu':sum(r['split']==split for r in manifest),'kutu':sum(r['kutu'] for r in manifest if r['split']==split),'kucuk_kutu':sum(r['kucuk_kutu'] for r in manifest if r['split']==split)} for split in ['train','val','test']}
    summary['kontrol']='Aynı grup farklı split içinde yok; SHA256 tekrar yok; XML-YOLO koordinat geri dönüş farkı < 0.00001 piksel.'
    (REPORTS/'veri-kontrolu.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
