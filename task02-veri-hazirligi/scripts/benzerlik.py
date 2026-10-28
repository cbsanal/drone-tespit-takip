"""Algısal benzerliği ikinci bir ölçümle tarar; kararlar aday niteliğindedir."""
from pathlib import Path
import csv
import math
import numpy as np
from PIL import Image
from veri_analizi import save_csv

root = Path('task02-veri-hazirligi')
rows = list(csv.DictReader((root/'raporlar/dosya-envanteri.csv').open(encoding='utf-8-sig')))
# pHash: 32x32 gri görüntünün düşük frekanslı 8x8 DCT katsayıları.
n = np.arange(32)
transform = np.cos(np.pi * (2*n+1)[None, :] * n[:, None] / 64)
hashes = []
for row in rows:
    if row['format'] == '':
        continue
    with Image.open(Path('Dataset')/row['dosya']) as im:
        pixels = np.asarray(im.convert('L').resize((32,32)), dtype=float)
    low = (transform @ pixels @ transform.T)[:8,:8].ravel()[1:]
    bits = low > np.median(low)
    value = sum(int(bit) << k for k, bit in enumerate(bits))
    hashes.append((row['dosya'], value))
pairs = []
for i, (name1, hash1) in enumerate(hashes):
    for name2, hash2 in hashes[i+1:]:
        distance = (hash1 ^ hash2).bit_count()
        if distance <= 6:
            pairs.append({'dosya1':name1,'dosya2':name2,'phash_mesafesi':distance})
save_csv(root/'raporlar/phash-adaylari.csv',pairs,['dosya1','dosya2','phash_mesafesi'])
print('pHash aday cifti:',len(pairs))
