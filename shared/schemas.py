# Message schemas & shared constants for Edge AI multi-agent system.
# Agents MUST communicate over MQTT using these schemas (no in-process calls).

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json
import time
import uuid


TOPICS = {
    "sensor_readings": "edge/sensor/readings",
    "analysis_results": "edge/analysis/results",
    "decision_alerts": "edge/decision/alerts",
    "heartbeat": "edge/system/heartbeat",
    "control": "edge/system/control",
}


@dataclass
class SensorReading:
    agent_id: str
    temperature_c: float
    humidity_pct: float
    pm25_ugm3: float
    co2_ppm: float
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(payload: str | bytes) -> "SensorReading":
        data = json.loads(payload)
        required = {"agent_id", "temperature_c", "humidity_pct", "pm25_ugm3", "co2_ppm"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"malformed SensorReading, missing: {sorted(missing)}")
        return SensorReading(**{k: data[k] for k in (
            "agent_id", "temperature_c", "humidity_pct", "pm25_ugm3", "co2_ppm", "trace_id", "ts"
        ) if k in data})


@dataclass
class AnalysisResult:
    agent_id: str
    trace_id: str
    anomaly_score: float
    is_anomaly: bool
    label: str
    inference_ms: float
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(payload: str | bytes) -> "AnalysisResult":
        data = json.loads(payload)
        required = {"agent_id", "trace_id", "anomaly_score", "is_anomaly", "label", "inference_ms"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"malformed AnalysisResult, missing: {sorted(missing)}")
        return AnalysisResult(**{k: data[k] for k in (
            "agent_id", "trace_id", "anomaly_score", "is_anomaly", "label", "inference_ms", "ts"
        ) if k in data})


@dataclass
class DecisionAlert:
    agent_id: str
    trace_id: str
    severity: str  # info | warning | critical | degraded
    action: str
    reason: str
    e2e_latency_ms: float | None = None
    degraded: bool = False
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(payload: str | bytes) -> "DecisionAlert":
        data = json.loads(payload)
        required = {"agent_id", "trace_id", "severity", "action", "reason"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"malformed DecisionAlert, missing: {sorted(missing)}")
        return DecisionAlert(**{k: data[k] for k in (
            "agent_id", "trace_id", "severity", "action", "reason",
            "e2e_latency_ms", "degraded", "ts",
        ) if k in data})


@dataclass
class Heartbeat:
    agent_id: str
    status: str = "alive"
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


def parse_json(payload: str | bytes) -> dict[str, Any]:
    return json.loads(payload)
