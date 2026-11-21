
from pathlib import Path
from collections import Counter
import argparse
import csv
import json
import statistics
import time

import cv2
import torch
from ultralytics import YOLO


def synchronize(device):
    if device == "cuda":
        torch.cuda.synchronize()


def main():
    parser = argparse.ArgumentParser(
        description="YOLO11s + ByteTrack benchmark"
    )
    parser.add_argument(
        "--source",
        default="videos/drone_test.mp4"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.40
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10
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

    tracker_path = (
        project_dir
        / "config"
        / "bytetrack_drone.yaml"
    )

    source = Path(args.source)
    if not source.is_absolute():
        source = project_dir / source

    if not source.is_file():
        print(f"Video bulunamadi: {source}")
        return

    if not model_path.is_file():
        print(f"Model bulunamadi: {model_path}")
        return

    if not tracker_path.is_file():
        print(f"Tracker bulunamadi: {tracker_path}")
        return

    output_dir = project_dir / "runs" / "benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / "benchmark_frames.csv"
    output_json = output_dir / "benchmark_summary.json"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_device = 0 if device == "cuda" else "cpu"

    print(f"Device: {device}")

    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    model = YOLO(str(model_path))

    cap = cv2.VideoCapture(str(source))

    if not cap.isOpened():
        print("Video acilamadi.")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video FPS: {video_fps:.2f}")
    print(f"Toplam kare: {total_frames}")

    # Modeli onceden hazirla.
    # Tracker bu asamada baslatilmaz.
    warmup_frame = None
    success, warmup_frame = cap.read()

    if not success:
        print("Video bos veya okunamiyor.")
        cap.release()
        return

    print("Warmup baslatiliyor...")

    for _ in range(max(0, args.warmup)):
        model.predict(
            source=warmup_frame,
            conf=args.conf,
            imgsz=args.imgsz,
            device=model_device,
            verbose=False
        )

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    frame_number = 0
    tracked_frames = 0
    detected_frames = 0

    processing_times = []
    confidences = []
    observed_ids = set()
    id_counts = Counter()

    previous_single_id = None
    adjacent_id_changes = 0

    rows = []

    print("Benchmark baslatildi...")

    total_start = time.perf_counter()

    try:
        while True:
            success, frame = cap.read()

            if not success:
                break

            frame_number += 1

            synchronize(device)
            start = time.perf_counter()

            results = model.track(
                source=frame,
                persist=True,
                tracker=str(tracker_path),
                conf=args.conf,
                imgsz=args.imgsz,
                device=model_device,
                verbose=False
            )

            synchronize(device)
            elapsed_ms = (
                time.perf_counter() - start
            ) * 1000

            processing_times.append(elapsed_ms)

            result = results[0]
            boxes = result.boxes

            detection_count = 0
            track_ids = []
            frame_confidences = []

            if boxes is not None:
                detection_count = len(boxes)

                if detection_count > 0:
                    detected_frames += 1

                frame_confidences = (
                    boxes.conf.cpu().tolist()
                )

                confidences.extend(frame_confidences)

                if boxes.id is not None:
                    track_ids = (
                        boxes.id.int().cpu().tolist()
                    )

            if track_ids:
                tracked_frames += 1

            for track_id in track_ids:
                observed_ids.add(track_id)
                id_counts[track_id] += 1

            # Yalnizca iki ardisik karede de
            # tek ID varsa dogrudan gecisi say.
            if (
                len(track_ids) == 1
                and previous_single_id is not None
                and track_ids[0] != previous_single_id
            ):
                adjacent_id_changes += 1

            previous_single_id = (
                track_ids[0]
                if len(track_ids) == 1
                else None
            )

            rows.append({
                "frame": frame_number,
                "processing_ms": round(elapsed_ms, 3),
                "detection_count": detection_count,
                "track_count": len(track_ids),
                "track_ids": ";".join(map(str, track_ids)),
                "mean_confidence": (
                    round(statistics.mean(frame_confidences), 4)
                    if frame_confidences
                    else ""
                )
            })

            if frame_number % 100 == 0:
                print(f"Islenen kare: {frame_number}")

    finally:
        cap.release()

    total_elapsed = time.perf_counter() - total_start

    if not processing_times:
        print("Olculecek kare bulunamadi.")
        return

    mean_ms = statistics.mean(processing_times)
    median_ms = statistics.median(processing_times)

    processing_fps = 1000.0 / mean_ms

    summary = {
        "source": str(source),
        "model": str(model_path),
        "tracker": str(tracker_path),
        "device": device,
        "video_fps": round(video_fps, 3),
        "frames_processed": frame_number,
        "frames_with_detections": detected_frames,
        "frames_with_tracks": tracked_frames,
        "track_coverage_percent": round(
            100 * tracked_frames / frame_number, 2
        ),
        "unique_track_ids": len(observed_ids),
        "track_ids": sorted(observed_ids),
        "id_counts": dict(id_counts),
        "adjacent_id_changes": adjacent_id_changes,
        "mean_processing_ms": round(mean_ms, 3),
        "median_processing_ms": round(median_ms, 3),
        "processing_fps": round(processing_fps, 2),
        "total_wall_time_seconds": round(total_elapsed, 3),
        "average_confidence": (
            round(statistics.mean(confidences), 4)
            if confidences
            else None
        ),
        "confidence_threshold": args.conf,
        "image_size": args.imgsz
    }

    with open(
        output_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "frame",
                "processing_ms",
                "detection_count",
                "track_count",
                "track_ids",
                "mean_confidence"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(
        output_json,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            summary,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n========== BENCHMARK ==========")
    print(f"Islenen kare: {frame_number}")
    print(f"Video FPS: {video_fps:.2f}")
    print(f"Ortalama islem FPS: {processing_fps:.2f}")
    print(f"Ortalama kare suresi: {mean_ms:.2f} ms")
    print(f"Medyan kare suresi: {median_ms:.2f} ms")
    print(f"Tespit bulunan kare: {detected_frames}")
    print(f"Takip bulunan kare: {tracked_frames}")
    print(f"Farkli takip ID sayisi: {len(observed_ids)}")
    print(f"Ardisik kare ID degisimi: {adjacent_id_changes}")
    print(f"Toplam duvar saati suresi: {total_elapsed:.2f} sn")
    print(f"\nCSV: {output_csv}")
    print(f"JSON: {output_json}")


if __name__ == "__main__":
    main()
