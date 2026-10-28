"""Paket taşındığında veri yolunu yerel klasöre göre günceller."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]

def main():
    text = 'path: ' + json.dumps(str(ROOT / 'data'), ensure_ascii=False) + '\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: drone\n'
    (ROOT / 'data.yaml').write_text(text, encoding='utf-8')
    print('Veri yolu güncellendi:', ROOT / 'data')

if __name__ == '__main__':
    main()
