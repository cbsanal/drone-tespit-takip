"""Mevcut drone modelini doğrulanmış negatiflerle iyileştirir."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.ultralytics')
os.environ['WANDB_MODE']='disabled'
import hashlib
import json
import platform
import shutil
import torch
import ultralytics
from ultralytics import YOLO


def main():
    from yollari_ayarla import main as yollari_ayarla
    yollari_ayarla()
    (ROOT/"weights").mkdir(exist_ok=True)
    (ROOT/"raporlar").mkdir(exist_ok=True)
    os.chdir(ROOT)
    device=0 if torch.cuda.is_available() else 'cpu'
    info={'python':platform.python_version(),'torch':torch.__version__,'torchvision':__import__('torchvision').__version__,'ultralytics':ultralytics.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'device_capability':torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None}
    (ROOT/'raporlar/ortam.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    # Önceki model yalnız okunur; yeni sonuçlar bu deney klasörüne yazılır.
    model=YOLO(ROOT.parent/'task04-model-egitimi/weights/best.pt')
    pretrained=ROOT.parent/'task04-model-egitimi/weights/best.pt'
    with pretrained.open('rb') as f: initial_hash=hashlib.file_digest(f,'sha256').hexdigest()
    (ROOT/'raporlar/baslangic-agirligi.json').write_text(json.dumps({'model':'task04-model-egitimi/weights/best.pt','sha256':initial_hash},indent=2),encoding='utf-8')
    result=model.train(data=str(ROOT/'data.yaml'),epochs=60,patience=12,imgsz=640,batch=8,device=device,workers=0,seed=42,deterministic=True,optimizer='AdamW',lr0=0.0002,lrf=0.01,weight_decay=0.0005,warmup_epochs=3,amp=False,cache=False,project=str(ROOT/'runs'),name='egitim',exist_ok=False,plots=True,save=True,
        mosaic=0.0,mixup=0.0,cutmix=0.0,copy_paste=0.0,hsv_h=0.0,hsv_s=0.0,hsv_v=0.0,degrees=0.0,translate=0.0,scale=0.0,shear=0.0,perspective=0.0,flipud=0.0,fliplr=0.0,close_mosaic=0)
    best=Path(model.trainer.best)
    shutil.copy2(best,ROOT/'weights/best.pt')
    (ROOT/'raporlar/egitim-durumu.json').write_text(json.dumps({'tamamlandi':True,'best':str(best),'epoch':model.trainer.epoch+1,'secim':'Doğrulama fitness değerine göre best.pt; test kullanılmadı.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Eğitim tamamlandı:',best)

if __name__=='__main__':
    main()
