"""Record camera samples and evaluate saved clips."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from .validation import score_frames

COLUMNS = ("frame", "video_ms", "inference_ms", "track_ids")


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("enter an integer greater than zero")
    return number


def confidence(value):
    number = float(value)
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError("enter a confidence between 0 and 1")
    return number


def new_file(path):
    if path.exists():
        raise ValueError(f"output already exists: {path}")
    return path


def camera_capture(args):
    import cv2

    output = new_file(args.output)
    if output.suffix.lower() != ".avi":
        raise ValueError("camera output must have the .avi extension")
    camera = cv2.VideoCapture(args.camera)
    writer = None
    written = 0
    try:
        if not camera.isOpened():
            raise ValueError(f"could not open camera {args.camera}")
        ok, frame = camera.read()
        if not ok:
            raise ValueError("camera did not return an initial frame")
        height, width = frame.shape[:2]
        fps = camera.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            fps = args.fps
        writer = cv2.VideoWriter(
            str(output), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height)
        )
        if not writer.isOpened():
            raise ValueError(f"could not create video: {output}")
        while ok and written < args.frames:
            writer.write(frame)
            written += 1
            if written < args.frames:
                ok, frame = camera.read()
    finally:
        camera.release()
        if writer is not None:
            writer.release()
    if written != args.frames:
        raise ValueError(f"camera stopped after {written} frames; partial clip: {output}")
    print(f"{written} frames written to {output}")


def evaluate(args):
    if not args.video.is_file():
        raise ValueError(f"saved clip not found: {args.video}")
    if not args.weights.is_file():
        raise ValueError(f"local model weights not found: {args.weights}")
    new_file(args.output)

    import cv2
    from ultralytics import YOLO

    model = YOLO(str(args.weights))
    camera = cv2.VideoCapture(str(args.video))
    count = 0
    try:
        if not camera.isOpened():
            raise ValueError(f"could not decode clip: {args.video}")
        ok, frame = camera.read()
        if not ok:
            raise ValueError(f"clip contains no readable frames: {args.video}")
        with args.output.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            while ok:
                count += 1
                video_ms = camera.get(cv2.CAP_PROP_POS_MSEC)
                started = time.perf_counter()
                result = model.track(
                    frame, persist=True, tracker="bytetrack.yaml",
                    conf=args.confidence, imgsz=args.image_size,
                    device=args.device, verbose=False,
                )[0]
                inference_ms = (time.perf_counter() - started) * 1000
                ids = result.boxes.id if result.boxes is not None else None
                writer.writerow({
                    "frame": count,
                    "video_ms": f"{video_ms:.3f}",
                    "inference_ms": f"{inference_ms:.3f}",
                    "track_ids": " ".join(str(int(value)) for value in ids.tolist())
                    if ids is not None else "",
                })
                if args.frames is not None and count >= args.frames:
                    break
                ok, frame = camera.read()
    finally:
        camera.release()
    print(f"{count} frames evaluated; metrics: {args.output}")


def read_metrics(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("input is not a SkyTrace evaluation CSV")
        samples = list(reader)
    if not samples:
        raise ValueError("input contains no frame measurements")
    try:
        times = [float(sample["inference_ms"]) for sample in samples]
        tracked = sum(bool(sample["track_ids"].strip()) for sample in samples)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"{path}: malformed frame measurements") from error
    if any(not math.isfinite(value) or value < 0 for value in times):
        raise ValueError("input contains invalid inference times")
    report = {
        "frames": len(samples),
        "frames_with_track": tracked,
        "frame_coverage_percent": round(tracked * 100 / len(samples), 2),
        "median_inference_ms": round(statistics.median(times), 3),
        "p95_inference_ms": sorted(times)[math.ceil(len(times) * 0.95) - 1],
    }
    return report


def summarize(args):
    print(json.dumps(read_metrics(args.input), indent=2))


def score(args):
    print(json.dumps(score_frames(args.input, args.labels), indent=2))


def doctor(args):
    packages = {}
    for name in ("opencv-python", "ultralytics", "torch"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    report = {"python": platform.python_version(), "machine": platform.machine(), "packages": packages}
    if args.weights:
        with args.weights.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        report["weights_sha256"] = actual
        if args.sha256 and actual != args.sha256.lower():
            raise ValueError(f"weight SHA-256 does not match: {actual}")
    print(json.dumps(report, indent=2))


def benchmark(args):
    if len(set(args.sizes)) != len(args.sizes):
        raise ValueError("benchmark sizes must be unique")
    for path in (args.video, args.weights):
        if not path.is_file():
            raise ValueError(f"input file not found: {path}")
    args.output.mkdir()
    results = []
    for size in args.sizes:
        destination = args.output / f"metrics-{size}.csv"
        evaluate(SimpleNamespace(
            video=args.video, weights=args.weights, output=destination,
            image_size=size, confidence=args.confidence, device=args.device,
            frames=args.frames,
        ))
        results.append(destination)
    report_html(SimpleNamespace(output=args.output / "report.html", inputs=results))



def report_html(args):
    from html import escape

    captions = ("Kare", "İzli kare", "İzli kare (%)", "Medyan (ms)", "P95 (ms)")
    header = "".join(f"<th>{caption}</th>" for caption in captions)
    rows = []
    for path in args.inputs:
        metrics = read_metrics(path)
        values = "".join(f"<td>{value}</td>" for value in metrics.values())
        rows.append(f"<tr><th scope='row'>{escape(path.name)}</th>{values}</tr>")
    document = (
        '<!doctype html><html lang="tr"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SkyTrace Test Sonuçları</title>"
        "<style>body{font:1rem system-ui;margin:2rem}table{border-collapse:collapse}"
        "th,td{border:1px solid #ccc;padding:.6rem;text-align:left}</style>"
        "<h1>SkyTrace Test Sonuçları</h1>"
        "<p>Kayıtlı videoların tespit ve takip ölçümleri.</p>"
        f"<table><thead><tr><th>Dosya</th>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></html>"
    )
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(document)
    print(f"report written to {args.output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    capture = commands.add_parser("capture", help="record a bounded test clip")
    capture.add_argument("--camera", type=int, default=0)
    capture.add_argument("--frames", type=positive_int, default=120)
    capture.add_argument("--fps", type=positive_int, default=30, help="fallback video FPS")
    capture.add_argument("output", type=Path)
    capture.set_defaults(run=camera_capture)

    evaluation = commands.add_parser("evaluate", help="track objects in a saved clip")
    evaluation.add_argument("video", type=Path)
    evaluation.add_argument("weights", type=Path)
    evaluation.add_argument("output", type=Path)
    evaluation.add_argument("--device", default="cpu")
    evaluation.add_argument("--confidence", type=confidence, default=0.5)
    evaluation.add_argument("--image-size", type=positive_int, default=640)
    evaluation.add_argument("--frames", type=positive_int)
    evaluation.set_defaults(run=evaluate)

    summary = commands.add_parser("summarize", help="summarize a frame metrics CSV")
    summary.add_argument("input", type=Path)
    summary.set_defaults(run=summarize)

    report = commands.add_parser("report", help="generate a browser-readable comparison")
    report.add_argument("output", type=Path)
    report.add_argument("inputs", type=Path, nargs="+")
    report.set_defaults(run=report_html)

    scoring = commands.add_parser("score", help="score tracks against frame-level labels")
    scoring.add_argument("input", type=Path)
    scoring.add_argument("labels", type=Path)
    scoring.set_defaults(run=score)

    diagnostics = commands.add_parser("doctor", help="inspect Python, packages and optional weights")
    diagnostics.add_argument("--weights", type=Path)
    diagnostics.add_argument("--sha256")
    diagnostics.set_defaults(run=doctor)

    bench = commands.add_parser("benchmark", help="compare image sizes on the same saved clip")
    bench.add_argument("video", type=Path)
    bench.add_argument("weights", type=Path)
    bench.add_argument("output", type=Path, help="new directory for CSVs and report")
    bench.add_argument("--sizes", type=positive_int, nargs="+", default=[320, 480, 640])
    bench.add_argument("--device", default="cpu")
    bench.add_argument("--confidence", type=confidence, default=0.5)
    bench.add_argument("--frames", type=positive_int)
    bench.set_defaults(run=benchmark)

    args = parser.parse_args()
    if args.command == "doctor" and args.sha256 and not args.weights:
        parser.error("--sha256 requires --weights")
    try:
        args.run(args)
    except (ImportError, OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
