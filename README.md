# Edge AI Multi-Agent — Giám sát môi trường thông minh

Đồ án cuối kỳ: **Triển khai hệ thống Multi-Agent trên Edge** (CE2206).

## Miền ứng dụng đã chọn

**Giám sát môi trường thông minh** trên 3 thiết bị edge (mỗi VM: 2 vCPU / 4GB RAM, CPU-only):

| Agent | Vai trò | Thiết bị |
|-------|---------|----------|
| `sensor_agent` | Thu thập & tiền xử lý dữ liệu cảm biến (nhiệt độ, độ ẩm, PM2.5, CO₂) | Edge VM #1 |
| `analysis_agent` | Suy luận AI cục bộ: phát hiện bất thường / dự báo (ONNX hoặc LLM nhỏ Q4) | Edge VM #2 |
| `decision_agent` | Ra quyết định & cảnh báo; xử lý lỗi khi node khác timeout/disconnect | Edge VM #3 |

**Mô hình điều phối:** tập trung nhẹ — `decision_agent` đóng vai orchestrator nhận kết quả phân tích và phát hành cảnh báo. Giao tiếp qua **MQTT** (Mosquitto), không dùng bộ nhớ chung.

## Cấu trúc thư mục

```
edge-ai-multi-agent/
├── agents/
│   ├── sensor_agent/      # Agent thu thập cảm biến
│   ├── analysis_agent/    # Agent suy luận AI cục bộ
│   └── decision_agent/    # Agent quyết định & cảnh báo
├── broker/                # Cấu hình Mosquitto MQTT
├── shared/                # Schema message, util chung
├── configs/               # Cấu hình từng agent / VM
├── dashboard/             # Web dashboard hiệu suất realtime (Flask + SocketIO)
├── scripts/               # Deploy, đo lường, fault-injection
├── metrics/               # Log RAM/CPU/latency thu thập được
├── data/samples/          # Dữ liệu cảm biến mẫu
├── docs/                  # Phân tích đề, kiến trúc, checklist
└── reports/               # Báo cáo kỹ thuật & bảng số liệu
```

## Yêu cầu bắt buộc (checklist)

- [x] Sensor Agent publish MQTT thật (`edge/sensor/readings`) — bước 1
- [x] Analysis Agent suy luận ONNX cục bộ (`edge/analysis/results`) — bước 2
- [x] Decision Agent cảnh báo + timeout fallback degraded — bước 3
- [x] Xử lý ≥ 1 tình huống lỗi (analysis timeout → degraded)
- [x] Docker Compose: 3 agent riêng + giới hạn 2 vCPU / 4GB — bước deploy
- [x] Đo metrics + E2E (`reports/metrics_run.json`, `reports/bao-cao-ky-thuat.md`)
- [x] Web dashboard realtime (`dashboard/`) — hiển thị trạng thái agent, latency, alert feed
- [ ] Video demo 5–10 phút (xem `docs/checklist-demo.md`)
- [x] Báo cáo đồ án đầy đủ (`reports/bao-cao-do-an.md`) — cần điền tên SV / GV trước khi nộp
- [ ] Điền tên SV / xuất Word–PDF nộp

## Công nghệ dự kiến

- **Giao tiếp:** MQTT (Eclipse Mosquitto)
- **AI cục bộ:** ONNX Runtime + mô hình anomaly detection nhẹ *(hoặc)* llama.cpp / Ollama với Qwen2.5-0.5B Q4
- **Đo tài nguyên:** `psutil` + script `docker stats`
- **Dashboard:** Flask + Flask-SocketIO (WebSocket) + Chart.js — subscribe MQTT, push realtime ra browser
- **Đóng gói:** Docker (giới hạn `--cpus=2 --memory=4g` mô phỏng VM)

## Web Dashboard

Subscribe tất cả MQTT topics, đẩy realtime qua WebSocket ra trình duyệt.

| Widget | Nội dung |
|--------|----------|
| Agent cards | Status badge (alive / degraded / down) + thời gian heartbeat gần nhất |
| Sensor readings | Nhiệt độ, độ ẩm, PM2.5, CO₂ — cập nhật mỗi lần sensor publish |
| E2E Latency chart | Line chart 60 điểm, stats p50 / p95 / last |
| ONNX Inference chart | Tương tự cho inference time |
| Alert feed | 30 alert gần nhất, màu theo severity + badge `degraded` |

**Chạy local** (cần broker + agents đã up):
```bash
pip install flask flask-socketio simple-websocket
python dashboard/app.py
# mở http://localhost:5000
```

**Chạy Docker** (tích hợp sẵn trong Compose, host port **5001** → container 5000; macOS thường chiếm 5000, giới hạn 0.5 CPU / 256 MB):
```bash
docker compose up -d --build
# mở http://localhost:5001
```

## Triển khai Docker (bước deploy — đúng ngân sách 2c/4GB)

```bash
./scripts/run_stack.sh
# hoặc:
docker compose up -d --build

# Kiểm tra từ máy host (broker publish ra port 1883)
source .venv/bin/activate
python scripts/verify_decision_mqtt.py --count 3

# Fault: dừng container analysis → decision vẫn ra degraded
./scripts/inject_fault_analysis.sh docker
python scripts/verify_decision_mqtt.py --count 2 --require-degraded --timeout 30

# Xem giới hạn tài nguyên
docker stats --no-stream sensor_agent analysis_agent decision_agent dashboard
```

Mỗi agent service trong Compose: `cpus: 2.0`, `mem_limit: 4g`, `memswap_limit: 4g`, không GPU.

## Triển khai local (dev không Docker)

```bash
./scripts/run_broker.sh
python scripts/train_anomaly_model.py
./scripts/run_decision.sh   # terminal 1
./scripts/run_analysis.sh   # terminal 2
./scripts/run_sensor.sh     # terminal 3
python dashboard/app.py     # terminal 4 (tuỳ chọn) → http://localhost:5000
python scripts/verify_decision_mqtt.py --count 3
```

`MQTT_HOST` mặc định `localhost` (local) hoặc `mqtt-broker` (trong Compose).

## Sản phẩm nộp

1. Mã nguồn + hướng dẫn deploy từng agent lên VM 2c/4GB
2. Video demo 5–10 phút (gồm tình huống 1 agent lỗi) — checklist: [`docs/checklist-demo.md`](docs/checklist-demo.md)
3. Báo cáo đồ án: Markdown [`reports/bao-cao-do-an.md`](reports/bao-cao-do-an.md) · **LaTeX** [`reports/latex/bao-cao.tex`](reports/latex/bao-cao.tex) · tóm tắt kỹ thuật [`reports/bao-cao-ky-thuat.md`](reports/bao-cao-ky-thuat.md) · số liệu [`reports/metrics_run.json`](reports/metrics_run.json)

**Quy ước code (bắt buộc khi phát triển):** [`docs/QUY-UOC-CODE.md`](docs/QUY-UOC-CODE.md).
