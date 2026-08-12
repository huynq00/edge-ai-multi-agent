# Báo cáo kỹ thuật — Multi-Agent trên Edge (CE2206)

> Bản **tóm tắt kỹ thuật**. Báo cáo đồ án đầy đủ (văn phong khoá luận): [`bao-cao-do-an.md`](bao-cao-do-an.md).

**Đề tài:** Triển khai hệ thống Multi-Agent trên Edge  
**Miền ứng dụng:** Giám sát môi trường thông minh  
**Nhóm / sinh viên:** _(điền tên)_  
**Ngày đo:** 2026-07-27  

Nguồn số liệu: `reports/metrics_run.json` (cửa sổ đo 40 giây, Docker Compose, mỗi agent 2 vCPU / 4GB RAM, CPU-only).

---

## 1. Mục tiêu

Thiết kế, triển khai và đánh giá hệ multi-agent phân tán trên edge tài nguyên hạn chế, tập trung ba năng lực:

1. Đưa model/agent chạy trong ngân sách 2 vCPU / 4GB (tối ưu + đo lường).
2. Phối hợp qua giao thức nhẹ, có xử lý lỗi.
3. Đánh giá định lượng trade-off độ trễ ↔ tài nguyên ↔ chất lượng.

---

## 2. Kiến trúc và vai trò từng agent

```text
┌─────────────────┐     MQTT      ┌──────────────────┐     MQTT      ┌──────────────────┐
│  Sensor Agent   │──────────────▶│  Analysis Agent  │──────────────▶│  Decision Agent  │
│  (container)    │  readings     │  + ONNX Runtime  │   results     │  orchestrator    │
│  2 vCPU / 4GB   │               │  2 vCPU / 4GB    │               │  2 vCPU / 4GB    │
└────────┬────────┘               └────────┬─────────┘               └────────┬─────────┘
         │                                 │                                  │
         └─────────────────┬───────────────┴──────────────────┬───────────────┘
                           │                                  │
                    ┌──────▼──────────────────────────────────▼──────┐
                    │           Mosquitto MQTT Broker                │
                    └────────────────────────────────────────────────┘
```

| Agent | Vai trò | Trách nhiệm chính |
|-------|---------|-------------------|
| `sensor_agent` | Thu thập | Giả lập nhiệt độ, độ ẩm, PM2.5, CO₂; publish `SensorReading` + heartbeat |
| `analysis_agent` | Suy luận AI cục bộ | Subscribe readings → ONNX Isolation Forest → publish `AnalysisResult` |
| `decision_agent` | Quyết định / điều phối | Tổng hợp kết quả, phát `DecisionAlert`; fallback khi analysis timeout |

**Mô hình điều phối:** tập trung nhẹ — `decision_agent` là orchestrator. Không dùng framework multi-agent nặng (CrewAI/LangGraph) để giữ RAM trong 4GB.

Mỗi agent chạy **một container riêng**, giao tiếp **chỉ qua MQTT** (không shared memory / gọi hàm nội bộ).

---

## 3. Giao thức giao tiếp và lý do chọn

| Hạng mục | Lựa chọn | Lý do |
|----------|----------|-------|
| Giao thức | **MQTT** (Eclipse Mosquitto) | Nhẹ, pub/sub phù hợp edge IoT; overhead thấp hơn HTTP polling |
| Payload | JSON theo schema `shared/schemas.py` | Dễ debug; có `trace_id` nối E2E |
| QoS | 1 cho nghiệp vụ | Ít mất message hơn QoS 0, vẫn đủ nhẹ |
| Topics | `edge/sensor/readings`, `edge/analysis/results`, `edge/decision/alerts`, heartbeat/control | Tách rõ pipeline |

---

## 4. Mô hình AI và tối ưu

| Thuộc tính | Giá trị |
|------------|---------|
| Pipeline | `StandardScaler` + `IsolationForest` (scikit-learn) |
| Export | **ONNX** (`skl2onnx`, opset ML=3) |
| Runtime | **ONNX Runtime** — `CPUExecutionProvider` |
| File | `models/anomaly.onnx` (~1.16 MB) |
| Đặc trưng | `temperature_c`, `humidity_pct`, `pm25_ugm3`, `co2_ppm` |
| Train | 2000 mẫu normal giả lập; `contamination=0.05`, `n_estimators=100` |
| Kiểm tra nhanh | Normal≈96% đúng; anomaly≈100% trên tập synthetic |

Không dùng LLM trong bản nộp chính (để an toàn trần 4GB). Có thể mở rộng Qwen2.5-0.5B Q4 như điểm cộng.

---

## 5. Xử lý lỗi (fault tolerance)

**Scenario bắt buộc:** Analysis Agent ngắt / không phản hồi.

1. Decision lưu mỗi `trace_id` khi nhận reading.
2. Nếu không có `AnalysisResult` trong `analysis_timeout_sec` (mặc định **5s**):
   - Áp **threshold rules** (temp≥40°C, PM2.5≥75, CO₂≥1500).
   - Publish alert `severity=degraded`, `degraded=true`.
3. Sensor & decision **tiếp tục chạy**; hệ không sập toàn bộ.
4. Kết quả analysis đến muộn (sau khi đã fallback) bị **bỏ qua** để tránh double-alert.

Demo: `./scripts/inject_fault_analysis.sh docker` rồi  
`python scripts/verify_decision_mqtt.py --count 2 --require-degraded`.

---

## 6. Bảng đo lường

### 6.1 Cấu hình đo

- Nền tảng: Docker Compose, giới hạn `cpus=2`, `mem_limit=4g` mỗi agent.
- Cửa sổ: **40 giây**, sensor interval 2s.
- Công cụ: `scripts/collect_metrics.py` + `docker stats`.

### 6.2 Tài nguyên (docker stats, mẫu cuối cửa sổ)

| Thành phần | CPU (mẫu) | RAM sử dụng | Giới hạn |
|------------|-----------|-------------|----------|
| sensor_agent | 0.08% | **20.89 MiB** | 4 GiB |
| analysis_agent | 0.21% | **51.54 MiB** | 4 GiB |
| decision_agent | 0.19% | **20.11 MiB** | 4 GiB |
| mqtt-broker | 0.54% | 2.74 MiB | (host) |

→ Headroom RAM rất lớn so với trần 4GB; phù hợp mở rộng model lớn hơn nếu cần.

### 6.3 Latency & throughput

| Metric | Giá trị |
|--------|---------|
| E2E latency p50 | **9.48 ms** |
| E2E latency p95 | **49.72 ms** |
| E2E mean / max | 16.7 ms / 52.3 ms |
| Inference ONNX p50 / p95 | **4.98 ms / 6.94 ms** |
| Throughput (mỗi tầng) | **~0.525 msg/s** (khớp interval 2s) |
| Readings / results / alerts (40s) | 21 / 21 / 21 |
| Degraded trong cửa sổ ổn định | 0 |

E2E = thời điểm tạo `SensorReading` → lúc `DecisionAlert` (cùng `trace_id`).

### 6.4 Fault path (đo riêng)

Khi dừng `analysis_agent`: decision phát alert `degraded=true` sau ~timeout 5s (E2E ≈ 5010–5155 ms trong lần demo trước). Sensor + decision vẫn alive.

---

## 7. Phân tích trade-off và giới hạn

| Trục | Quan sát |
|------|----------|
| **Độ trễ ↔ tài nguyên** | E2E p50 ~10ms với RAM agent < 55MiB — dư địa lớn trong 4GB. |
| **Chất lượng ↔ độ phức tạp model** | Isolation Forest nhẹ, đủ demo anomaly trên dữ liệu giả lập; chưa phải production sensor noise. |
| **Độ bền ↔ độ trễ khi lỗi** | Timeout 5s giữ hệ sống nhưng tăng E2E khi degraded; có thể chỉnh theo SLA. |
| **Framework** | Tự viết vòng MQTT tránh overhead CrewAI/LangGraph trên edge. |
| **Giới hạn** | Cảm biến giả lập; chưa đo năng lượng; chưa so sánh quantize nhiều mức / edge–cloud hybrid (điểm cộng). |

---

## 8. Cách tái lập

```bash
./scripts/run_stack.sh
source .venv/bin/activate
python scripts/verify_decision_mqtt.py --count 3
python scripts/collect_metrics.py --duration 40 --out reports/metrics_run.json

# Fault
./scripts/inject_fault_analysis.sh docker
python scripts/verify_decision_mqtt.py --count 2 --require-degraded --timeout 30
docker compose start analysis_agent
```

Chi tiết quy ước code: `docs/QUY-UOC-CODE.md`.

---

## 9. Kết luận

Hệ thống đáp ứng yêu cầu bắt buộc của đề: ≥3 agent vai trò khác nhau trên edge 2c/4GB, MQTT thật, AI cục bộ (ONNX), điều phối tập trung, fault timeout→degraded, và bảng metrics latency/tài nguyên/throughput. Hướng mở rộng: LLM nhỏ Q4, so sánh quantize, hoặc hybrid edge–cloud kèm số liệu.
