
from pathlib import Path
import argparse
import time

import cv2
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="YOLO11s ile video uzerinde drone tespiti"
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Video dosyasinin yolu"
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.60,
        help="Guven esigi (0.0 - 1.0)"
    )

    args = parser.parse_args()

    if not 0.0 < args.conf <= 1.0:
        parser.error("--conf 0 ile 1 arasinda olmali.")

    project_dir = Path(__file__).resolve().parent.parent

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

    video_path = Path(args.source).resolve()

    if not video_path.is_file():
        print(f"Video bulunamadi: {video_path}")
        return

    output_dir = project_dir / "runs" / "video_predictions"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{video_path.stem}_detected.mp4"

    if output_path.resolve() == video_path:
        print("Giris ve cikis dosyalari ayni olamaz.")
        return

    model = YOLO(str(model_path))

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("Video acilamadi!")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS)

    if video_fps <= 0:
        video_fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        video_fps,
        (width, height)
    )

    if not writer.isOpened():
        print("Video cikis dosyasi olusturulamadi!")
        cap.release()
        return

    frame_count = 0
    start_time = time.perf_counter()

    print(f"Video: {video_path}")
    print(f"Confidence: {args.conf}")
    print("Cikmak icin Q tusuna basin.")

    try:
        while True:
            success, frame = cap.read()

            if not success:
                break

            frame_start = time.perf_counter()

            results = model.predict(
                source=frame,
                conf=args.conf,
                imgsz=640,
                device=0,
                verbose=False
            )

            result = results[0]
            annotated_frame = result.plot()

            drone_count = len(result.boxes)

            elapsed = time.perf_counter() - frame_start
            processing_fps = 1 / max(elapsed, 1e-6)

            cv2.putText(
                annotated_frame,
                f"Processing FPS: {processing_fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                annotated_frame,
                f"Drone Count: {drone_count}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            writer.write(annotated_frame)
            frame_count += 1

            cv2.imshow(
                "Drone Detection - Video",
                annotated_frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()

    total_time = time.perf_counter() - start_time

    print(f"Islenen kare: {frame_count}")
    print(f"Toplam sure: {total_time:.2f} saniye")
    print(f"Kaydedilen video: {output_path}")


if __name__ == "__main__":
    main()
