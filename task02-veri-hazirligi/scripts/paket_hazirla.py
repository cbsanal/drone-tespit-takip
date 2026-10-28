"""Görsel inceleme kararlarına göre dosyaları değiştirmeden yerel paket hazırlar."""
from pathlib import Path
import csv
import json
import shutil
from collections import Counter
from veri_analizi import save_csv, sha256

root = Path('task02-veri-hazirligi')
reports = root/'raporlar'
source = Path('Dataset')
rows = list(csv.DictReader((reports/'dosya-envanteri.csv').open(encoding='utf-8-sig')))
by_name = {r['dosya']: r for r in rows}
draft = json.loads((reports/'secim-taslagi.json').read_text())
# Numaralar, mevcut kutularla gözden geçirilen secim-XX paftalarındaki sıralardır.
approved = list(range(1,18)) + [21,23,24,25,31,32,36,40,41,45,47,48,49,52,53,57,60,61,64,68,69,72,73,74,76,78,80,81,86,88,89,90,99,107,109,112,119,124,125,126,128,133,135,137,138,142,148,150,151,157,158,164,165]
partial_boxes = [18,20,27,37,39,42,43,44,46,50,51,54,56,58,62,66,67,70,71,75,79,82,84,87,91,92,93,95,96,97,98,101,103,105,108,111,113,114,115,117,118,120,122,123,127,129,130,132,134,139,141,143,144,145,149,153,154,155,156,159,160,162,163]
selected = {draft[i-1] for i in approved}
manual = {draft[i-1]: 'Mevcut kutu drone parcalarinin tamamini kapsamiyor; gorsel inceleme gerekli.' for i in partial_boxes}
# Açıkça görülen ürün/çizim ve uçuş dışı örnekler için örnek gerekçeler.
examples = {'pic_001.jpg':'Beyaz fonda urun gorseli.', 'pic_1010.jpg':'Drone cizimi/isaret levhasi.', 'pic_1049.jpg':'Bilgisayar grafikleri/simulasyon gorunumu.', 'pic_289.jpg':'Cizim/illustrasyon.'}
for n in range(1,62):
    name=rows[n-1]['dosya']
    if n not in range(3,10):
        examples[name]='Ucusta degil; elde, zeminde veya tanitim/kurulum sahnesi.'
for n in range(62,98):
    examples[rows[n-1]['dosya']]='Ic mekan ucusu; acik hava onceligi nedeniyle secilmedi.'
for n in list(range(1024,1040))+list(range(1043,1058))+list(range(1086,1094)):
    examples[rows[n-1]['dosya']]='Ucusta degil; elde veya masa uzerinde tanitim sahnesi.'
decisions=[]
for row in rows:
    name=row['dosya']
    mismatch=(Path(name).suffix.lower() in {'.jpg','.jpeg'} and row['format']!='JPEG')
    if name in selected:
        status,reason='secildi','Disaridan gorulen ucus; mevcut kutuyla gorsel kontrolden gecti.'
    elif row['hata']:
        status,reason='teknik_inceleme',row['hata']
    elif mismatch:
        status,reason='teknik_inceleme','Uzanti ile gercek dosya bicimi uyusmuyor.'
    elif name in manual:
        status,reason='etiket_inceleme',manual[name]
    elif name in examples:
        status,reason='kapsam_disi',examples[name]
    else:
        status,reason='secim_disi','Gorsel on elemede uygunluk onayi verilmedi veya benzer sahnenin alternatifi; gerekirse ayrintili yeniden inceleme.'
    decisions.append({'dosya':name,'durum':status,'gerekce':reason})
save_csv(reports/'secim-kararlari.csv',decisions,['dosya','durum','gerekce'])
save_csv(reports/'gorsel-etiket-sorunlari.csv',[{'dosya':n,'sorun':s} for n,s in manual.items()],['dosya','sorun'])
save_csv(reports/'format-uyusmazliklari.csv',[{'dosya':r['dosya'],'gercek_format':r['format']} for r in rows if Path(r['dosya']).suffix.lower() in {'.jpg','.jpeg'} and r['format']!='JPEG'],['dosya','gercek_format'])
save_csv(reports/'cozunurlukler.csv',[{'genislik':w,'yukseklik':h,'goruntu_sayisi':count} for (w,h),count in Counter((r['genislik'],r['yukseklik']) for r in rows).most_common()],['genislik','yukseklik','goruntu_sayisi'])
manifest=[]
for name in sorted(selected):
    row=by_name[name]
    assert not row['hata'], name
    for rel in [name,row['xml']]:
        target=root/'secilen'/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/rel,target)
        manifest.append({'dosya':rel,'sha256':sha256(target),'bayt':target.stat().st_size})
save_csv(reports/'secilen-sha256.csv',manifest,['dosya','sha256','bayt'])
preview_names=['foto00204.png','foto07338.png','foto14646.png','moto15458.png','pic_022.jpg','pic_083.jpg','pic_1135.jpg','pic_312.jpg','pic_870.jpg','yoto02814.png']
assert len(preview_names)==10 and set(preview_names)<=selected
for name in preview_names:
    shutil.copy2(source/name,root/'onizleme'/name)
save_csv(reports/'onizleme-listesi.csv',[{'dosya':n,'etiket':'../secilen/'+by_name[n]['xml']} for n in preview_names],['dosya','etiket'])
boxes=list(csv.DictReader((reports/'kutular.csv').open(encoding='utf-8-sig')))
chosen_boxes=[b for b in boxes if b['dosya'] in selected]
all_hashes=list(csv.DictReader((reports/'sha256.csv').open(encoding='utf-8-sig')))
assert all(sha256(source/h['dosya'])==h['sha256'] for h in all_hashes)
original={h['dosya']:h['sha256'] for h in all_hashes}
assert all(h['sha256']==original[h['dosya']] for h in manifest)
assert all(sha256(root/'onizleme'/n)==original[n] for n in preview_names)
summary={'goruntu':len(selected),'xml':len(selected),'kutu':len(chosen_boxes),'kucuk_kutu_alan_1024_alti':sum(b['alan_1024_alti']=='True' for b in chosen_boxes),'alan_orani_yuzde1_alti':sum(float(b['alan_orani'])<.01 for b in chosen_boxes),'bayt':sum(m['bayt'] for m in manifest),'kararlar':dict(Counter(r['durum'] for r in decisions)),'gorsel_kutu_sorunu':len(manual),'format_uyusmazligi':sum(Path(r['dosya']).suffix.lower() in {'.jpg','.jpeg'} and r['format']!='JPEG' for r in rows),'orijinal_hash_kontrolu':'2194 dosya degismedi','kopya_hash_kontrolu':'Tum secilen dosyalar ve 10 onizleme kaynakla birebir ayni'}
(reports/'secim-ozeti.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
