# Phân tích đề bài — Multi-Agent trên Edge

Nguồn: `de-tai-cuoi-ky-edge-ai.PDF`

## 1. Mục tiêu cốt lõi (trọng tâm chấm điểm)

Không phải đồ án hệ phân tán thuần túy. Ba năng lực Edge AI được chấm trọng tâm:

1. **Tối ưu tài nguyên:** đưa model/agent chạy trong ngân sách chặt (quantize, đo lường).
2. **Phối hợp phân tán:** giao thức nhẹ + xử lý lỗi giữa các agent.
3. **Đánh giá định lượng:** trade-off độ trễ ↔ tài nguyên ↔ chất lượng.

> Phần đo lường tài nguyên và tối ưu edge là **trọng tâm**, không phải phần phụ.

## 2. Ràng buộc cứng

| Hạng mục | Yêu cầu |
|----------|---------|
| Số agent | ≥ 3, vai trò **khác nhau** |
| Phần cứng | Mỗi agent = 1 VM: **2 vCPU, 4GB RAM, CPU-only** |
| Giao tiếp | Qua mạng thật — **cấm** shared memory / gọi hàm nội bộ giả lập |
| AI cục bộ | ≥ 1 agent chạy inference trên edge |
| Điều phối | Mô tả rõ: tập trung **hoặc** phi tập trung |
| Fault tolerance | ≥ 1 scenario: disconnect / timeout / malformed — hệ không sập toàn bộ |
| Metrics | Per-agent: peak RAM, CPU avg/peak, latency p50 & p95, throughput; + E2E latency |

## 3. Lựa chọn miền ứng dụng

Đề gợi ý 4 hướng. Nhóm chọn:

**Giám sát môi trường thông minh**

```
Sensor Agent  →  Analysis Agent (AI local)  →  Decision Agent
   (thu thập)        (bất thường/dự báo)         (cảnh báo/hành động)
```

**Lý do chọn:**

- Khớp ví dụ trong đề; pipeline rõ 3 vai trò khác nhau.
- Dữ liệu cảm biến dễ giả lập, thí nghiệm lặp lại được.
- Model anomaly detection (ONNX/sklearn) vừa khung 4GB; vẫn có đường nâng cấp sang LLM nhỏ Q4 nếu muốn điểm cộng.
- Dễ inject lỗi (ngắt sensor hoặc analysis) để demo fault handling.

Các hướng khác vẫn khả thi (vision, RAG, predictive maintenance) nếu đổi miền sau.

## 4. Thiết kế đáp ứng yêu cầu

### 4.1 Kiến trúc

- **3 agent / 3 VM**, mỗi container/process giới hạn `cpus=2`, `memory=4g`.
- **MQTT broker** (Mosquitto): pub/sub nhẹ, phù hợp edge.
- **Orchestration tập trung nhẹ:** `decision_agent` tổng hợp kết quả và ra quyết định; không phụ thuộc framework nặng (LangGraph/CrewAI) để tránh vượt 4GB.

### 4.2 Topics MQTT (dự kiến)

| Topic | Publisher | Subscriber |
|-------|-----------|------------|
| `edge/sensor/readings` | sensor | analysis |
| `edge/analysis/results` | analysis | decision |
| `edge/decision/alerts` | decision | (dashboard / log) |
| `edge/system/heartbeat` | mọi agent | decision |
| `edge/system/control` | decision | sensor, analysis |

### 4.3 Suy luận AI cục bộ

Phương án chính (an toàn trong 4GB):

- Model: Isolation Forest / Autoencoder nhỏ → export **ONNX**
- Runtime: **ONNX Runtime** (CPU)
- Input: vector cảm biến đã chuẩn hóa; Output: anomaly score + label

Phương án thay thế / điểm cộng:

- LLM: Qwen2.5-0.5B hoặc Llama-3.2-1B **Q4** qua llama.cpp/Ollama
- So sánh nhiều mức quantize (Q4 vs Q8) — mục điểm cộng trong đề

### 4.4 Xử lý lỗi (bắt buộc demo)

Tình huống đề xuất:

1. **Timeout Analysis Agent:** decision chờ N giây, fallback rule-based (ngưỡng cứng), ghi alert `degraded`.
2. (Tuỳ chọn) Sensor gửi JSON sai schema → analysis reject + NACK, không crash.

### 4.5 Đo lường

Mỗi agent ghi metrics bằng `psutil` + timestamp:

- `peak_rss_mb`, `cpu_avg_pct`, `cpu_peak_pct`
- `latency_ms` (p50, p95 trên batch request)
- `throughput` (msg/s hoặc inference/s)
- Pipeline: `e2e_latency_ms` = từ lúc sensor publish → decision alert

## 5. Sản phẩm nộp

1. **Source** tái lập + Docker/script deploy đúng 2c/4GB
2. **Video 5–10 phút:** chạy thật trên VM riêng + fault scenario
3. **Báo cáo:** sơ đồ, giao thức + lý do, model + quantize, bảng metrics, phân tích trade-off

## 6. Điểm cộng (nếu còn thời gian)

- So sánh nhiều mức quantize / pruning
- Edge-only vs edge–cloud hybrid kèm số liệu
- Đo năng lượng hoặc ước lượng chi phí

## 7. Rủi ro & lưu ý

| Rủi ro | Cách giảm |
|--------|-----------|
| Model LLM ~3B Q4 sát trần 4GB | Ưu tiên 0.5B–1.5B hoặc ONNX nhỏ |
| Framework multi-agent nặng | Tự viết vòng MQTT; tránh CrewAI nếu chưa đo RAM |
| Demo “giả lập 3 agent 1 process” | Bắt buộc 3 container/VM riêng + network |
| Thiếu số liệu p50/p95 | Script đo từ đầu, không đo tay cuối kỳ |
