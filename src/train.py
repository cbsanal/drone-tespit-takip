
from pathlib import Path
from ultralytics import YOLO
import torch

def main():
    # Projenin ana klasoru
    project_dir = Path(__file__).resolve().parent.parent

    # Veri seti
    dataset_yaml = project_dir / "datasets" / "drone" / "data.yaml"

    # GPU kontrolu
    print("CUDA:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA kullanilamiyor!")

    print("GPU:", torch.cuda.get_device_name(0))

    # Onceden egitilmis YOLO11s modeli
    model = YOLO("yolo11s.pt")

    # Model egitimi
    model.train(
        data=str(dataset_yaml),
        epochs=50,
        imgsz=640,
        batch=16,
        device=0,
        workers=4,
        project=str(project_dir / "runs"),
        name="drone_yolo11s",
        patience=15,
        plots=True
    )

if __name__ == "__main__":
    main()
