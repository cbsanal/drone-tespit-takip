"""Score recorded clips against frame-level human annotations."""

import csv
from fractions import Fraction


def read_presence(path, column, parse_value):
    values = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"frame", column}.issubset(reader.fieldnames or ()):
            raise ValueError(f"{path}: expected frame and {column} columns")
        for line, row in enumerate(reader, start=2):
            try:
                frame = int(row["frame"])
                if frame < 1 or frame in values:
                    raise ValueError("frame numbers must be positive and unique")
                values[frame] = parse_value(row[column].strip())
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"{path}:{line}: {error}") from error
    if not values:
        raise ValueError(f"{path}: no frames")
    return values


def annotation(value):
    if value not in {"0", "1"}:
        raise ValueError("present must be 0 or 1")
    return value == "1"


def score_frames(metrics_path, labels_path):
    expected = read_presence(labels_path, "present", annotation)
    observed = read_presence(metrics_path, "track_ids", bool)
    missing = expected.keys() - observed.keys()
    if missing:
        raise ValueError(f"missing measurements for {len(missing)} annotated frames")
    tp = sum(expected[frame] and observed[frame] for frame in expected)
    fp = sum(not expected[frame] and observed[frame] for frame in expected)
    fn = sum(expected[frame] and not observed[frame] for frame in expected)

    def ratio(numerator, denominator):
        return round(float(Fraction(numerator, denominator)), 4) if denominator else None

    return {
        "annotated_frames": len(expected),
        "unannotated_frames": len(observed) - len(expected),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": len(expected) - tp - fp - fn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }
