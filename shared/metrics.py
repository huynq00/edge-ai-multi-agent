"""Lightweight resource & latency metrics collector for edge agents."""

from __future__ import annotations

import json
import statistics
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


@dataclass
class MetricsSnapshot:
    agent_id: str
    peak_rss_mb: float
    cpu_avg_pct: float
    cpu_peak_pct: float
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    throughput_per_sec: float
    samples: int
    wall_sec: float


class MetricsCollector:
    def __init__(self, agent_id: str, sample_interval_sec: float = 1.0):
        self.agent_id = agent_id
        self.sample_interval_sec = sample_interval_sec
        self._latencies_ms: list[float] = []
        self._cpu_samples: list[float] = []
        self._peak_rss_mb = 0.0
        self._peak_cpu = 0.0
        self._ops = 0
        self._start = time.time()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc = psutil.Process() if psutil else None

    def start(self) -> None:
        if self._proc is None:
            return
        self._proc.cpu_percent(interval=None)  # prime
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def record_latency(self, ms: float) -> None:
        self._latencies_ms.append(ms)
        self._ops += 1

    def _sample_loop(self) -> None:
        assert self._proc is not None
        while not self._stop.wait(self.sample_interval_sec):
            rss_mb = self._proc.memory_info().rss / (1024 * 1024)
            cpu = self._proc.cpu_percent(interval=None)
            self._peak_rss_mb = max(self._peak_rss_mb, rss_mb)
            self._peak_cpu = max(self._peak_cpu, cpu)
            self._cpu_samples.append(cpu)

    def snapshot(self) -> MetricsSnapshot:
        wall = max(time.time() - self._start, 1e-6)
        p50 = p95 = None
        if self._latencies_ms:
            sorted_l = sorted(self._latencies_ms)
            p50 = statistics.median(sorted_l)
            idx = min(len(sorted_l) - 1, int(len(sorted_l) * 0.95))
            p95 = sorted_l[idx]
        return MetricsSnapshot(
            agent_id=self.agent_id,
            peak_rss_mb=round(self._peak_rss_mb, 2),
            cpu_avg_pct=round(statistics.mean(self._cpu_samples), 2) if self._cpu_samples else 0.0,
            cpu_peak_pct=round(self._peak_cpu, 2),
            latency_p50_ms=round(p50, 2) if p50 is not None else None,
            latency_p95_ms=round(p95, 2) if p95 is not None else None,
            throughput_per_sec=round(self._ops / wall, 3),
            samples=len(self._latencies_ms),
            wall_sec=round(wall, 2),
        )

    def dump(self, path: str | Path) -> MetricsSnapshot:
        snap = self.snapshot()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(snap), indent=2), encoding="utf-8")
        return snap
