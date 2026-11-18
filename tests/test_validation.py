import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from skytrace.__main__ import benchmark, evaluate, read_metrics
from skytrace.validation import score_frames


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.metrics = self.root / "metrics.csv"
        self.metrics.write_text(
            "frame,video_ms,inference_ms,track_ids\n"
            "1,0,2,7\n2,33,6,\n3,66,4,8\n4,99,8,\n",
            encoding="utf-8",
        )
        self.labels = self.root / "labels.csv"

    def test_summary_and_annotated_subset(self):
        self.labels.write_text("frame,present\n1,1\n2,1\n3,0\n", encoding="utf-8")
        self.assertEqual(read_metrics(self.metrics)["p95_inference_ms"], 8)
        result = score_frames(self.metrics, self.labels)
        self.assertEqual((result["f1"], result["unannotated_frames"]), (0.5, 1))

    def test_missing_measurement_is_not_counted_as_negative(self):
        self.labels.write_text("frame,present\n5,1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing measurements"):
            score_frames(self.metrics, self.labels)

    def test_duplicate_labels_are_rejected(self):
        self.labels.write_text("frame,present\n1,1\n1,0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "positive and unique"):
            score_frames(self.metrics, self.labels)

    def test_benchmark_collects_one_result_per_size(self):
        video, weights = self.root / "clip.avi", self.root / "best.pt"
        video.touch()
        weights.touch()
        output = self.root / "benchmark"
        args = SimpleNamespace(
            video=video, weights=weights, output=output, sizes=[320, 640],
            device="cpu", confidence=0.5, frames=3,
        )

        def fake_evaluate(options):
            options.output.write_bytes(self.metrics.read_bytes())

        with patch("skytrace.__main__.evaluate", side_effect=fake_evaluate) as evaluate:
            benchmark(args)
        self.assertEqual([call.args[0].image_size for call in evaluate.call_args_list], [320, 640])
        self.assertIn("metrics-640.csv", (output / "report.html").read_text(encoding="utf-8"))

    def test_offline_evaluation_writes_tracks_and_releases_decoder(self):
        video, weights = self.root / "clip.avi", self.root / "best.pt"
        video.touch()
        weights.touch()
        decoder = Mock()
        decoder.isOpened.return_value = True
        decoder.read.side_effect = [(True, object()), (True, object()), (False, None)]
        decoder.get.side_effect = [0, 33]
        ids = Mock()
        ids.tolist.return_value = [7]
        model = Mock()
        model.track.side_effect = [
            [SimpleNamespace(boxes=SimpleNamespace(id=ids))],
            [SimpleNamespace(boxes=None)],
        ]
        modules = {
            "cv2": SimpleNamespace(CAP_PROP_POS_MSEC=0, VideoCapture=Mock(return_value=decoder)),
            "ultralytics": SimpleNamespace(YOLO=Mock(return_value=model)),
        }
        output = self.root / "actual.csv"
        args = SimpleNamespace(
            video=video, weights=weights, output=output, image_size=640,
            device="cpu", confidence=0.5, frames=None,
        )
        with patch.dict(sys.modules, modules):
            evaluate(args)
        self.assertEqual(read_metrics(output)["frames_with_track"], 1)
        self.assertEqual(model.track.call_count, 2)
        decoder.release.assert_called_once()
