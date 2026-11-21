
from pathlib import Path
from collections import defaultdict, deque
import argparse
import csv
import time

import cv2
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="YOLO11s + ByteTrack drone takibi"
    )

    parser.add_argument(
        "--source",
        default="videos/drone_test.mp4",
        help="Video dosyasinin yolu"
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.40,
        help="Guven esigi"
    )

    args = parser.parse_args()

    if not 0 < args.conf <= 1:
        parser.error("--conf 0 ile 1 arasinda olmali")

    project_dir = Path(__file__).resolve().parent.parent

    model_path = (
        project_dir
        / "runs"
        / "drone_yolo11s"
        / "weights"
        / "best.pt"
    )

    video_path = Path(args.source)
    if not video_path.is_absolute():
        video_path = project_dir / video_path

    if not model_path.is_file():
        print(f"Model bulunamadi: {model_path}")
        return

    if not video_path.is_file():
        print(f"Video bulunamadi: {video_path}")
        return

    output_dir = project_dir / "runs" / "tracking"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_video = (
        output_dir / f"{video_path.stem}_tracked.mp4"
    )
    output_csv = (
        output_dir / f"{video_path.stem}_tracking.csv"
    )

    if output_video.resolve() == video_path.resolve():
        print("Giris ve cikis dosyalari ayni olamaz.")
        return

    model = YOLO(str(model_path))
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("Video acilamadi!")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    if not writer.isOpened():
        print("Cikis videosu olusturulamadi!")
        cap.release()
        return

    # Her ID icin son 60 konumu sakla
    track_history = defaultdict(
        lambda: deque(maxlen=60)
    )

    frame_number = 0
    tracked_frames = 0
    observed_ids = set()

    start_time = time.perf_counter()

    print("Drone takibi baslatildi.")
    print(f"Video: {video_path}")
    print(f"Confidence: {args.conf}")
    print("Cikmak icin Q tusuna basin.")

    try:
        with open(
            output_csv,
            "w",
            newline="",
            encoding="utf-8"
        ) as csv_file:

            csv_writer = csv.writer(csv_file)

            csv_writer.writerow([
                "frame",
                "time_seconds",
                "track_id",
                "center_x",
                "center_y",
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2"
            ])

            while True:
                success, frame = cap.read()

                if not success:
                    break

                frame_number += 1

                results = model.track(
                    source=frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=args.conf,
                    imgsz=640,
                    device=0,
                    verbose=False
                )

                result = results[0]
                annotated = result.plot()

                boxes = result.boxes
                active_count = 0

                if (
                    boxes is not None
                    and boxes.id is not None
                ):
                    ids = boxes.id.int().cpu().tolist()
                    coords = boxes.xyxy.cpu().tolist()
                    scores = boxes.conf.cpu().tolist()

                    active_count = len(ids)

                    if active_count > 0:
                        tracked_frames += 1

                    for track_id, box, score in zip(
                        ids, coords, scores
                    ):
                        x1, y1, x2, y2 = box

                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)

                        observed_ids.add(track_id)

                        history = track_history[track_id]
                        history.append((center_x, center_y))

                        # Drone merkezini isaretle
                        cv2.circle(
                            annotated,
                            (center_x, center_y),
                            5,
                            (0, 0, 255),
                            -1
                        )

                        # Hareket izini ciz
                        points = list(history)

                        for i in range(1, len(points)):
                            cv2.line(
                                annotated,
                                points[i - 1],
                                points[i],
                                (255, 0, 255),
                                2
                            )

                        # Merkez koordinatlari
                        cv2.putText(
                            annotated,
                            f"ID {track_id}: ({center_x}, {center_y})",
                            (max(5, int(x1)), max(75, int(y1) - 12)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 255),
                            2
                        )

                        # CSV kaydi
                        csv_writer.writerow([
                            frame_number,
                            round((frame_number - 1) / fps, 3),
                            track_id,
                            center_x,
                            center_y,
                            round(score, 4),
                            round(x1, 1),
                            round(y1, 1),
                            round(x2, 1),
                            round(y2, 1)
                        ])

                cv2.putText(
                    annotated,
                    f"Tracked Drones: {active_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    annotated,
                    f"Frame: {frame_number}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                writer.write(annotated)

                cv2.imshow(
                    "Drone Tracking - YOLO11s + ByteTrack",
                    annotated
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()

    total_time = time.perf_counter() - start_time

    print("\nTakip tamamlandi!")
    print(f"Islenen kare: {frame_number}")
    print(f"Takip bulunan kare: {tracked_frames}")
    print(f"Gorulen farkli ID sayisi: {len(observed_ids)}")
    print(f"Toplam sure: {total_time:.2f} saniye")
    print(f"Video: {output_video}")
    print(f"CSV: {output_csv}")


if __name__ == "__main__":
    main()
