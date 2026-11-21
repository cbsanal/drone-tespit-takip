
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime
import csv
import time

import cv2
from ultralytics import YOLO


# ==========================================
# AYARLAR
# ==========================================

CAMERA_INDEX = 0

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

IMAGE_SIZE = 960

DEFAULT_CONFIDENCE = 0.40

TRACK_HISTORY_LENGTH = 60

DEVICE = 0


def main():

    # ==========================================
    # DOSYA YOLLARI
    # ==========================================

    project_dir = Path(__file__).resolve().parent.parent

    model_path = (
        project_dir
        / "runs"
        / "drone_yolo11s"
        / "weights"
        / "best.pt"
    )

    tracker_path = (
        project_dir
        / "config"
        / "bytetrack_drone.yaml"
    )

    output_dir = (
        project_dir
        / "runs"
        / "camera_tracking"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    if not model_path.is_file():
        print(f"Model bulunamadi: {model_path}")
        return

    if not tracker_path.is_file():
        print(f"Tracker dosyasi bulunamadi: {tracker_path}")
        return

    # ==========================================
    # MODEL
    # ==========================================

    model = YOLO(str(model_path))

    # ==========================================
    # KAMERA
    # ==========================================

    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        print("Kamera acilamadi!")
        return

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        CAMERA_WIDTH
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        CAMERA_HEIGHT
    )

    camera.set(
        cv2.CAP_PROP_FPS,
        CAMERA_FPS
    )

    width = int(
        camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    actual_camera_fps = camera.get(
        cv2.CAP_PROP_FPS
    )

    if actual_camera_fps <= 0 or actual_camera_fps > 120:
        actual_camera_fps = CAMERA_FPS

    print(f"Kamera cozunurlugu: {width}x{height}")
    print(f"Kamera FPS bilgisi: {actual_camera_fps}")

    # ==========================================
    # TAKIP AYARLARI
    # ==========================================

    confidence = DEFAULT_CONFIDENCE

    track_history = defaultdict(
        lambda: deque(
            maxlen=TRACK_HISTORY_LENGTH
        )
    )

    recording = False

    video_writer = None
    csv_file = None
    csv_writer = None

    recording_start = None
    recorded_frame = 0

    video_path = None
    csv_path = None

    previous_time = time.perf_counter()

    print("\nDrone Tracking baslatildi!")
    print("---------------------------")
    print("+ / = : Confidence artir")
    print("-     : Confidence azalt")
    print("R     : Kayit baslat/durdur")
    print("C     : Hareket izini temizle")
    print("Q     : Cikis")
    print("---------------------------\n")

    try:

        while True:

            # ==========================================
            # KAMERADAN GORUNTU AL
            # ==========================================

            success, frame = camera.read()

            if not success:
                print("Kameradan goruntu alinamadi.")
                break

            # ==========================================
            # YOLO + BYTETRACK
            # ==========================================

            results = model.track(
                source=frame,
                persist=True,
                tracker=str(tracker_path),
                conf=confidence,
                imgsz=IMAGE_SIZE,
                device=DEVICE,
                verbose=False
            )

            result = results[0]

            annotated = result.plot()

            boxes = result.boxes

            active_count = 0
            frame_records = []

            # ==========================================
            # TAKIP EDILEN DRONELAR
            # ==========================================

            if (
                boxes is not None
                and boxes.id is not None
            ):

                ids = boxes.id.int().cpu().tolist()
                coords = boxes.xyxy.cpu().tolist()
                scores = boxes.conf.cpu().tolist()

                active_count = len(ids)

                for track_id, box, score in zip(
                    ids,
                    coords,
                    scores
                ):

                    x1, y1, x2, y2 = box

                    center_x = int(
                        (x1 + x2) / 2
                    )

                    center_y = int(
                        (y1 + y2) / 2
                    )

                    # Hareket gecmisi
                    history = track_history[track_id]

                    history.append(
                        (center_x, center_y)
                    )

                    # Drone merkez noktasi
                    cv2.circle(
                        annotated,
                        (center_x, center_y),
                        5,
                        (0, 0, 255),
                        -1
                    )

                    # ==================================
                    # HAREKET IZINI CIZ
                    # ==================================

                    points = list(history)

                    for i in range(1, len(points)):

                        cv2.line(
                            annotated,
                            points[i - 1],
                            points[i],
                            (255, 0, 255),
                            2
                        )

                    # ==================================
                    # ID VE KOORDINATLAR
                    # ==================================

                    cv2.putText(
                        annotated,
                        (
                            f"ID {track_id} "
                            f"({center_x}, {center_y})"
                        ),
                        (
                            max(5, int(x1)),
                            max(90, int(y1) - 12)
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 255),
                        2
                    )

                    # ==================================
                    # CSV VERISI
                    # ==================================

                    frame_records.append([
                        track_id,
                        center_x,
                        center_y,
                        round(score, 4),
                        round(x1, 1),
                        round(y1, 1),
                        round(x2, 1),
                        round(y2, 1)
                    ])

            # ==========================================
            # FPS
            # ==========================================

            current_time = time.perf_counter()

            fps = 1.0 / max(
                current_time - previous_time,
                1e-6
            )

            previous_time = current_time

            # ==========================================
            # BILGI PANELI
            # ==========================================

            cv2.rectangle(
                annotated,
                (0, 0),
                (420, 85),
                (0, 0, 0),
                -1
            )

            cv2.putText(
                annotated,
                (
                    f"FPS: {fps:.1f} | "
                    f"Conf: {confidence:.2f}"
                ),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                annotated,
                f"Tracked Drones: {active_count}",
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # ==========================================
            # KAYIT
            # ==========================================

            if recording:

                cv2.putText(
                    annotated,
                    "REC",
                    (max(10, width - 85), 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

                recorded_frame += 1

                video_writer.write(
                    annotated
                )

                elapsed = (
                    time.perf_counter()
                    - recording_start
                )

                for record in frame_records:

                    csv_writer.writerow([
                        recorded_frame,
                        round(elapsed, 3),
                        *record
                    ])

            # ==========================================
            # GORUNTU
            # ==========================================

            cv2.imshow(
                "Drone Tracking - Live Camera",
                annotated
            )

            key = cv2.waitKey(1) & 0xFF

            # ==========================================
            # KLAVYE KONTROLLERI
            # ==========================================

            if key == ord("q"):
                break

            elif key in (
                ord("+"),
                ord("=")
            ):

                confidence = min(
                    0.95,
                    round(
                        confidence + 0.05,
                        2
                    )
                )

                print(
                    f"Confidence: {confidence:.2f}"
                )

            elif key == ord("-"):

                confidence = max(
                    0.05,
                    round(
                        confidence - 0.05,
                        2
                    )
                )

                print(
                    f"Confidence: {confidence:.2f}"
                )

            elif key == ord("c"):

                track_history.clear()

                print(
                    "Hareket izi temizlendi."
                )

            elif key == ord("r"):

                # ==============================
                # KAYDI BASLAT
                # ==============================

                if not recording:

                    timestamp = datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )

                    video_path = (
                        output_dir
                        / f"camera_{timestamp}.mp4"
                    )

                    csv_path = (
                        output_dir
                        / f"camera_{timestamp}.csv"
                    )

                    video_writer = cv2.VideoWriter(
                        str(video_path),
                        cv2.VideoWriter_fourcc(
                            *"mp4v"
                        ),
                        actual_camera_fps,
                        (width, height)
                    )

                    if not video_writer.isOpened():

                        print(
                            "Video kaydi baslatilamadi."
                        )

                        video_writer.release()
                        video_writer = None
                        continue

                    try:

                        csv_file = open(
                            csv_path,
                            "w",
                            newline="",
                            encoding="utf-8"
                        )

                    except OSError as error:

                        print(
                            f"CSV acilamadi: {error}"
                        )

                        video_writer.release()
                        video_writer = None
                        continue

                    csv_writer = csv.writer(
                        csv_file
                    )

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

                    recorded_frame = 0

                    recording_start = (
                        time.perf_counter()
                    )

                    recording = True

                    print(
                        f"Kayit basladi: {video_path}"
                    )

                # ==============================
                # KAYDI DURDUR
                # ==============================

                else:

                    recording = False

                    video_writer.release()
                    csv_file.close()

                    video_writer = None
                    csv_file = None
                    csv_writer = None

                    print(
                        "Kayit durduruldu."
                    )

                    print(
                        f"Video: {video_path}"
                    )

                    print(
                        f"CSV: {csv_path}"
                    )

    finally:

        if video_writer is not None:
            video_writer.release()

        if csv_file is not None:
            csv_file.close()

        camera.release()

        cv2.destroyAllWindows()

    print("\nProgram kapatildi.")


if __name__ == "__main__":
    main()
