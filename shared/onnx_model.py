"""ONNX anomaly detector for environmental sensor vectors."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

FEATURE_NAMES = ["temperature_c", "humidity_pct", "pm25_ugm3", "co2_ppm"]


@dataclass
class InferenceOutput:
    anomaly_score: float
    is_anomaly: bool
    label: str
    inference_ms: float


class OnnxAnomalyModel:
    """Load IsolationForest pipeline exported by scripts/train_anomaly_model.py."""

    def __init__(self, model_path: str | Path, meta_path: str | Path | None = None):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"ONNX model not found: {self.model_path}. "
                "Run: python scripts/train_anomaly_model.py"
            )
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

        self.meta: dict = {}
        meta_file = Path(meta_path) if meta_path else self.model_path.with_name("anomaly_meta.json")
        if meta_file.is_file():
            self.meta = json.loads(meta_file.read_text(encoding="utf-8"))

    def features_from_reading(self, reading) -> np.ndarray:
        vec = np.array(
            [
                [
                    float(reading.temperature_c),
                    float(reading.humidity_pct),
                    float(reading.pm25_ugm3),
                    float(reading.co2_ppm),
                ]
            ],
            dtype=np.float32,
        )
        return vec

    def predict(self, reading) -> InferenceOutput:
        x = self.features_from_reading(reading)
        t0 = time.perf_counter()
        outputs = self.session.run(self.output_names, {self.input_name: x})
        inference_ms = (time.perf_counter() - t0) * 1000.0

        # skl2onnx IsolationForest: output[0]=label (-1/1), output[1]=scores (optional)
        label_raw = int(np.asarray(outputs[0]).reshape(-1)[0])
        if len(outputs) > 1:
            raw_score = float(np.asarray(outputs[1]).reshape(-1)[0])
            # sklearn: higher score = more normal → anomaly_score = -score
            anomaly_score = float(-raw_score)
        else:
            anomaly_score = 1.0 if label_raw == -1 else 0.0

        is_anomaly = label_raw == -1
        label = "anomaly" if is_anomaly else "normal"
        return InferenceOutput(
            anomaly_score=round(anomaly_score, 6),
            is_anomaly=is_anomaly,
            label=label,
            inference_ms=round(inference_ms, 3),
        )
