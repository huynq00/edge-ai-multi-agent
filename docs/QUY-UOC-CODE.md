# Quy ước phát triển — Edge AI Multi-Agent

Tài liệu này là **chuẩn bắt buộc** khi viết/sửa code. Mọi thay đổi phải giữ đúng đề tài CE2206 và thiết kế đã chọn.

**Nguồn đề:** `de-tai-cuoi-ky-edge-ai.PDF` · Phân tích: [`phan-tich-de-bai.md`](phan-tich-de-bai.md) · Kiến trúc: [`kien-truc.md`](kien-truc.md)

---

## 1. Phạm vi đề tài (không được lệch)

| Đã chốt | Giá trị |
|---------|---------|
| Miền ứng dụng | **Giám sát môi trường thông minh** |
| Pipeline | `sensor_agent` → `analysis_agent` → `decision_agent` |
| Điều phối | **Tập trung nhẹ** — `decision_agent` là orchestrator |
| Giao tiếp | **MQTT** (Mosquitto), JSON theo schema trong `shared/schemas.py` |
| Ngân sách mỗi agent | **2 vCPU / 4GB RAM / CPU-only** |
| AI cục bộ | Chỉ trên `analysis_agent` (ONNX ưu tiên; LLM nhỏ Q4 tùy chọn) |

**Không làm:**

- Gộp nhiều agent vào một process/VM để “demo nhanh”.
- Gọi hàm trực tiếp giữa các agent (import chéo rồi gọi như thư viện).
- Shared memory / queue in-process thay cho MQTT.
- Dùng GPU hoặc vượt 4GB RAM khi deploy/demo chính thức.
- Framework multi-agent nặng (CrewAI / LangGraph / AutoGen) trừ khi đã đo RAM và chứng minh vừa 4GB.
- Đổi miền (vision / RAG / predictive maintenance) mà không cập nhật docs + báo cáo.

---

## 2. Ràng buộc cứng từ đề (checklist trước mỗi PR / lần nộp)

- [ ] ≥ 3 agent, **vai trò khác nhau**, mỗi agent deploy **1 VM/container riêng**
- [ ] Giới hạn runtime: `--cpus=2 --memory=4g --memory-swap=4g`, không GPU
- [ ] Giao tiếp **chỉ** qua mạng (MQTT), không giả lập in-process
- [ ] ≥ 1 agent chạy **suy luận AI cục bộ** trên edge
- [ ] Mô tả / giữ nguyên mô hình điều phối **tập trung**
- [ ] ≥ 1 fault scenario: disconnect / timeout / malformed — hệ không sập toàn bộ
- [ ] Metrics mỗi agent: peak RAM, CPU avg/peak, latency **p50 & p95**, throughput
- [ ] Đo **E2E latency** (sensor publish → decision alert) qua `trace_id`

---

## 3. Vai trò từng agent (đúng một trách nhiệm)

| Agent | Được phép | Không được phép |
|-------|-----------|-----------------|
| `sensor_agent` | Giả lập/đọc cảm biến, chuẩn hóa, publish readings + heartbeat | Không chạy model AI; không ra quyết định cảnh báo |
| `analysis_agent` | Subscribe readings, **inference cục bộ**, publish results + heartbeat | Không điều phối cả hệ; không bỏ qua MQTT |
| `decision_agent` | Subscribe results, policy/alert, timeout fallback, heartbeat/control | Không thay thế inference AI chính (chỉ fallback rule khi degraded) |

Cấu hình đọc từ `configs/default.yaml` (hoặc override theo VM). Không hard-code IP/topic rải rác — dùng `shared.schemas.TOPICS` và config.

---

## 4. Giao tiếp MQTT & schema

### Topics (cố định)

| Topic | Publisher | Subscriber |
|-------|-----------|------------|
| `edge/sensor/readings` | sensor | analysis |
| `edge/analysis/results` | analysis | decision |
| `edge/decision/alerts` | decision | log / dashboard |
| `edge/system/heartbeat` | mọi agent | decision |
| `edge/system/control` | decision | sensor, analysis |

### Message

- Dùng dataclass trong `shared/schemas.py`: `SensorReading`, `AnalysisResult`, `DecisionAlert`, `Heartbeat`.
- Mọi message nghiệp vụ phải có **`trace_id`** để nối E2E latency.
- Parse qua `from_json` / validate field bắt buộc; **malformed → reject, không crash process**.
- Payload: JSON UTF-8. Không đổi tên field public mà không cập nhật schema + docs.

```text
✅ GOOD: analysis subscribe MQTT → onnx.run → publish AnalysisResult
❌ BAD:  from agents.sensor_agent.main import read_sensors; read_sensors()
```

---

## 5. AI cục bộ & tài nguyên

**Mặc định an toàn 4GB:** Isolation Forest / Autoencoder nhỏ → **ONNX** + ONNX Runtime (CPU).

**Tùy chọn điểm cộng:** LLM ≤ ~1.5B, quantize **Q4** (Qwen2.5-0.5B / Llama-3.2-1B…). Tránh ~3B Q4 sát trần.

Khi dùng LLM phải ghi trong báo cáo/metrics: tên model, số tham số, mức quantize, kích thước file.

Mọi Dockerfile / compose / script deploy **phải** gắn resource limit 2c/4GB. Không “nới” limit để model chạy được rồi quên đo lại.

---

## 6. Fault tolerance (bắt buộc có trong code + demo)

Scenario chính:

1. **Analysis timeout:** `decision_agent` chờ `analysis_timeout_sec` (config).
2. Hết hạn → fallback `threshold_rules` trên dữ liệu cảm biến (nếu có) hoặc trạng thái degraded.
3. Publish `DecisionAlert` với `severity=degraded` / `degraded=true`.
4. Sensor & decision **vẫn sống**; không `sys.exit` cả cụm.

Scenario phụ (khuyến nghị): JSON sai schema → analysis log + bỏ qua / NACK, process không chết.

Script inject lỗi đặt trong `scripts/` (ví dụ ngắt analysis). Không xóa khả năng demo fault để “code sạch hơn”.

---

## 7. Metrics & đo lường

- Dùng `shared/metrics.py` (psutil) và/hoặc `docker stats`.
- Ghi vào `metrics/` theo agent, có timestamp.
- Bắt buộc tính được: `peak_rss_mb`, `cpu_avg_pct`, `cpu_peak_pct`, latency p50/p95, throughput, `e2e_latency_ms`.
- Đo từ sớm trong vòng đời agent — **không** chỉ đo tay cuối kỳ.
- Không commit file metrics nhiễu / bí mật; giữ format ổn định để đưa vào báo cáo.

---

## 8. Cấu trúc thư mục & thay đổi cho phép

```text
agents/{sensor,analysis,decision}_agent/   # entrypoint từng agent
broker/                                    # Mosquitto
shared/                                    # schema + metrics dùng chung (không chứa logic điều phối)
configs/                                   # YAML cấu hình
scripts/                                   # deploy, đo, fault-injection
metrics/  data/  reports/  docs/
```

- Logic agent ở đúng package của agent đó.
- `shared/` chỉ utilities/schema/metrics — **không** import agent A từ agent B.
- Docs kiến trúc / phân tích đề cập nhật khi đổi topic, role, model, hoặc mô hình điều phối.

---

## 9. Phong cách code

- Python 3.10+; type hints cho API public (schema, hàm metrics).
- Phụ thuộc khai báo trong `requirements.txt`; ưu tiên thư viện nhẹ.
- Không thêm dashboard/UI nặng trừ khi phục vụ demo metrics và không phá ngân sách RAM.
- Comment chỉ khi giải thích ràng buộc đề / fault / edge (tránh comment thừa).
- Log có `agent_id` + `trace_id` khi xử lý message.

---

## 10. Sản phẩm nộp (không quên khi “xong code”)

1. Source tái lập + hướng dẫn deploy từng agent đúng 2c/4GB.
2. Video 5–10 phút: chạy trên VM/container riêng + **một** tình huống agent lỗi.
3. Báo cáo: kiến trúc, giao thức + lý do, model + tối ưu, bảng metrics, trade-off.

---

## 11. Trước khi merge / coi là hoàn thành

```text
[ ] 3 process/container riêng, MQTT thật
[ ] analysis có inference cục bộ
[ ] decision có timeout + fallback degraded
[ ] schema/trace_id nhất quán
[ ] resource limit 2c/4GB trong deploy
[ ] metrics p50/p95 + E2E ghi được file
[ ] không import chéo agent / không shared memory giả lập
[ ] docs còn khớp hành vi code
```
