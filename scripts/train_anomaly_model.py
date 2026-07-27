#!/usr/bin/env python3
"""Train Isolation Forest trên dữ liệu cảm biến giả lập và export ONNX.

Chạy: python scripts/train_anomaly_model.py
Output: models/anomaly.onnx + models/anomaly_meta.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

FEATURE_NAMES = ["temperature_c", "humidity_pct", "pm25_ugm3", "co2_ppm"]


def _sample_normal(n: int, rng: np.random.Generator) -> np.ndarray:
    return np.column_stack(
        [
            rng.uniform(22.0, 32.0, n),
            rng.uniform(40.0, 70.0, n),
            rng.uniform(8.0, 35.0, n),
            rng.uniform(400.0, 900.0, n),
        ]
    )


def _sample_anomaly(n: int, rng: np.random.Generator) -> np.ndarray:
    return np.column_stack(
        [
            rng.uniform(42.0, 55.0, n),
            rng.uniform(85.0, 99.0, n),
            rng.uniform(90.0, 180.0, n),
            rng.uniform(1600.0, 2500.0, n),
        ]
    )


def main() -> None:
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:
        raise SystemExit(
            "Cần skl2onnx để export. Chạy: pip install skl2onnx onnx"
        ) from exc

    rng = np.random.default_rng(42)
    x_train = _sample_normal(2000, rng)

    pipe = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "iforest",
                IsolationForest(
                    n_estimators=100,
                    contamination=0.05,
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipe.fit(x_train)

    # Sanity check
    x_ok = _sample_normal(50, rng)
    x_bad = _sample_anomaly(50, rng)
    pred_ok = pipe.predict(x_ok)
    pred_bad = pipe.predict(x_bad)
    ok_rate = float(np.mean(pred_ok == 1))
    bad_rate = float(np.mean(pred_bad == -1))
    print(f"normal detected as normal: {ok_rate:.2%}")
    print(f"anomaly detected as anomaly: {bad_rate:.2%}")

    initial_type = [("input", FloatTensorType([None, len(FEATURE_NAMES)]))]
    onnx_model = convert_sklearn(
        pipe,
        initial_types=initial_type,
        target_opset={"": 12, "ai.onnx.ml": 3},
    )

    out_dir = _ROOT / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = out_dir / "anomaly.onnx"
    with onnx_path.open("wb") as f:
        f.write(onnx_model.SerializeToString())

    meta = {
        "model": "IsolationForest",
        "pipeline": ["StandardScaler", "IsolationForest"],
        "features": FEATURE_NAMES,
        "label_anomaly": -1,
        "label_normal": 1,
        "contamination": 0.05,
        "n_estimators": 100,
        "train_samples": int(x_train.shape[0]),
        "normal_recall_approx": ok_rate,
        "anomaly_recall_approx": bad_rate,
        "onnx_path": str(onnx_path.relative_to(_ROOT)),
    }
    meta_path = out_dir / "anomaly_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {onnx_path} ({onnx_path.stat().st_size} bytes)")
    print(f"Wrote {meta_path}")


if __name__ == "__main__":
    main()
