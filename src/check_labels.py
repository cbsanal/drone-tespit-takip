
from pathlib import Path
import random
import cv2

dataset = Path("datasets/drone/train")
images_dir = dataset / "images"
labels_dir = dataset / "labels"

extensions = {".jpg", ".jpeg", ".png"}
images = [p for p in images_dir.iterdir()
          if p.suffix.lower() in extensions]

random.seed(42)
samples = random.sample(images, min(5, len(images)))

for image_path in samples:
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"Goruntu okunamadi: {image_path}")
        continue

    height, width = image.shape[:2]
    label_path = labels_dir / (image_path.stem + ".txt")

    if label_path.exists():
        for line in label_path.read_text().splitlines():
            values = line.split()

            if len(values) != 5:
                print(f"Gecersiz etiket: {label_path}")
                continue

            class_id, x, y, w, h = map(float, values)

            x1 = int((x - w / 2) * width)
            y1 = int((y - h / 2) * height)
            x2 = int((x + w / 2) * width)
            y2 = int((y + h / 2) * height)

            cv2.rectangle(
                image, (x1, y1), (x2, y2),
                (0, 255, 0), 2
            )

            cv2.putText(
                image, "Drone", (max(0, x1), max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2
            )

    cv2.imshow("Drone Label Check", image)
    print(f"Goruntu: {image_path.name}")

    key = cv2.waitKey(0)
    cv2.destroyAllWindows()

    if key == ord("q"):
        break
