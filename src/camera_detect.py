
from pathlib import Path
import time

import cv2
from ultralytics import YOLO


def main():
    # Projenin ana klasoru
    project_dir = Path(__file__).resolve().parent.parent

    # Egitilmis modelimizin yolu
    model_path = (
        project_dir
        / "runs"
        / "drone_yolo11s"
        / "weights"
        / "best.pt"
    )

    if not model_path.exists():
        print(f"Model bulunamadi: {model_path}")
        return

    # YOLO11s modelini yukle
    model = YOLO(str(model_path))

    # Laptop kamerasini ac
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Kamera acilamadi!")
        return

    # Baslangic guven esigi
    confidence = 0.60

    previous_time = time.perf_counter()

    print("Drone tespiti baslatildi.")
    print("Kontroller:")
    print("  + : Guven esigini artir")
    print("  - : Guven esigini azalt")
    print("  Q : Programdan cik")

    try:
        while True:
            # Kameradan goruntu al
            success, frame = camera.read()

            if not success:
                print("Kameradan goruntu alinamadi.")
                break

            # Drone tespiti
            results = model.predict(
                source=frame,
                conf=confidence,
                imgsz=640,
                device=0,
                verbose=False
            )

            result = results[0]

            # Tespit kutularini ciz
            annotated_frame = result.plot()

            # Tespit edilen drone sayisi
            drone_count = len(result.boxes)

            # FPS hesapla
            current_time = time.perf_counter()

            elapsed_time = current_time - previous_time
            fps = 1 / max(elapsed_time, 1e-6)

            previous_time = current_time

            # FPS ve guven esigini goster
            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.1f} | Confidence: {confidence:.2f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # Drone sayisini goster
            cv2.putText(
                annotated_frame,
                f"Drone Count: {drone_count}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # Kamera goruntusunu goster
            cv2.imshow(
                "Drone Detection - YOLO11s",
                annotated_frame
            )

            # Klavye kontrolleri
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            elif key in (ord("+"), ord("=")):
                confidence = min(
                    0.95,
                    round(confidence + 0.05, 2)
                )
                print(f"Confidence: {confidence:.2f}")

            elif key == ord("-"):
                confidence = max(
                    0.05,
                    round(confidence - 0.05, 2)
                )
                print(f"Confidence: {confidence:.2f}")

    finally:
        # Kamerayi serbest birak
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
