---
marp: true
theme: default
paginate: true
size: 16:9
header: 'CE2206.CH201 — Edge AI Multi-Agent'
footer: 'Giám sát môi trường thông minh'
style: |
  section {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 28px;
  }
  section.lead h1 {
    font-size: 2.2em;
  }
  section.lead h2 {
    font-size: 1.3em;
    font-weight: 400;
    color: #444;
  }
  h1 { color: #1a5276; }
  h2 { color: #2471a3; font-size: 1.4em; }
  table { font-size: 0.75em; margin: 0 auto; }
  th { background: #1a5276; color: white; }
  tr:nth-child(even) { background: #f4f6f7; }
  blockquote { border-left: 4px solid #2471a3; padding-left: 1em; color: #555; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# TRIỂN KHAI HỆ THỐNG MULTI-AGENT TRÊN EDGE

## Ứng dụng giám sát môi trường thông minh với suy luận AI cục bộ

**Học phần:** Công nghệ điện đám mây và điện toán biên (CE2206)

*[Họ và tên sinh viên]* · *[MSSV]*

*[Giảng viên hướng dẫn]* · 08/2026

---

## Nội dung trình bày

1. Bối cảnh & mục tiêu
2. Kiến trúc hệ thống
3. Ba agent & giao tiếp MQTT
4. Suy luận AI cục bộ (ONNX)
5. Xử lý lỗi & chế độ degraded
6. Hiện thực & triển khai
7. Kết quả thực nghiệm
8. Demo & dashboard
9. Kết luận & hướng phát triển

---

## Bối cảnh

- **IoT / giám sát môi trường** cần xử lý liên tục gần nguồn dữ liệu
- Đưa toàn bộ suy luận lên **cloud** → độ trễ cao, phụ thuộc băng thông, rủi ro mất kết nối
- **Điện toán biên (Edge Computing):** suy luận & điều phối trên nút gần cảm biến
- **Multi-agent:** tách vai trò thu thập → phân tích → quyết định trên các nút biên độc lập

> Đề tài CE2206: triển khai **≥ 3 agent**, giao tiếp **thật qua mạng**, ngân sách **2 vCPU / 4 GB / CPU-only**, đo lường **định lượng**

---

## Mục tiêu đồ án

| # | Mục tiêu |
|---|----------|
| 1 | Thiết kế & triển khai **3 agent** trên edge (2c/4GB, CPU-only) |
| 2 | Giao tiếp **chỉ qua MQTT** — không shared memory / gọi hàm nội bộ |
| 3 | **Suy luận AI cục bộ** trên Analysis Agent (ONNX Runtime) |
| 4 | **Orchestrator tập trung nhẹ** + fallback khi Analysis timeout |
| 5 | **Đo lường** E2E latency, RAM, throughput — số liệu tái lập được |
| 6 | Dashboard realtime phục vụ demo & quan sát vận hành |

---

## Miền ứng dụng

**Giám sát môi trường thông minh**

| Thông số | Mô tả |
|----------|-------|
| Nhiệt độ | °C |
| Độ ẩm | % |
| PM2.5 | µg/m³ |
| CO₂ | ppm |

- Dữ liệu cảm biến **giả lập có kiểm soát** (tỷ lệ anomaly cấu hình được)
- Pipeline: phát hiện bất thường → cảnh báo theo mức độ nghiêm trọng
- Phù hợp demo edge AI trên tài nguyên hạn chế

---

## Kiến trúc tổng thể

| Thành phần | Vị trí | Vai trò |
|------------|--------|---------|
| **Sensor Agent** | Edge VM #1 (2 vCPU / 4 GB) | Thu thập dữ liệu cảm biến |
| **Analysis Agent** | Edge VM #2 (2 vCPU / 4 GB) | Suy luận AI cục bộ (ONNX) |
| **Decision Agent** | Edge VM #3 (2 vCPU / 4 GB) | Điều phối & phát cảnh báo |
| **MQTT Broker** | Mosquitto | Trung gian pub/sub |

**Luồng chính:** Sensor → Analysis → Decision, tất cả qua MQTT

Mỗi agent = **container riêng** · Giao tiếp **100% MQTT** · Không GPU

---

## Ba agent — vai trò

| Agent | Vai trò | Trách nhiệm chính |
|-------|---------|-------------------|
| **Sensor** | Thu thập | Giả lập cảm biến, chuẩn hóa, gán mã truy vết, gửi readings + heartbeat |
| **Analysis** | Suy luận AI | Nhận readings → ONNX Isolation Forest → trả kết quả + thời gian suy luận |
| **Decision** | Quyết định | Orchestrator tập trung nhẹ: tổng hợp, phát alert, xử lý timeout |

**Điều phối tập trung nhẹ:** Decision là điểm kiểm soát thống nhất, không dùng framework nặng (CrewAI, LangGraph) để giữ RAM trong 4 GB

---

## Luồng end-to-end (E2E)

| Bước | Agent | Hành động |
|------|-------|-----------|
| 1 | Sensor | Gửi bản tin đọc cảm biến kèm mã truy vết (trace ID) |
| 2 | Analysis | Suy luận ONNX → gửi kết quả (điểm bất thường, nhãn) |
| 3 | Decision | Tổng hợp → phát cảnh báo kèm độ trễ E2E |

- **Mã truy vết (trace ID):** nối toàn pipeline, đo E2E từ lúc thu thập đến lúc cảnh báo
- **QoS 1** cho luồng nghiệp vụ — giảm mất tin, overhead vẫn thấp
- Payload **JSON** theo schema thống nhất giữa các agent

---

## Giao tiếp MQTT

| Topic | Người gửi | Người nhận | Nội dung |
|-------|-----------|------------|----------|
| edge/sensor/readings | Sensor | Analysis, Decision | Dữ liệu cảm biến |
| edge/analysis/results | Analysis | Decision | Kết quả suy luận |
| edge/decision/alerts | Decision | Dashboard | Cảnh báo quyết định |
| edge/system/heartbeat | Mọi agent | Dashboard | Tín hiệu sống |

**Lý do chọn MQTT:** pub/sub nhẹ, phù hợp IoT/edge; tách rời producer/consumer; overhead thấp hơn HTTP polling

---

## Suy luận AI cục bộ

| Thuộc tính | Giá trị |
|------------|---------|
| Thuật toán | **Isolation Forest** + StandardScaler |
| Định dạng model | **ONNX** (~1,16 MB) |
| Runtime | **ONNX Runtime** trên CPU |
| Đặc trưng đầu vào | Nhiệt độ, độ ẩm, PM2.5, CO₂ |
| Huấn luyện | 2000 mẫu normal synthetic; contamination 5% |

Chỉ **Analysis Agent** chạy AI — đúng mô hình edge: suy luận gần dữ liệu, không phụ thuộc cloud

---

## Xử lý lỗi — Analysis timeout

**Kịch bản bắt buộc:** Analysis Agent ngắt / không phản hồi

1. Decision lưu mã truy vết khi nhận reading
2. Không có kết quả Analysis trong **5 giây** (cấu hình được)
3. → Áp **ngưỡng cứng** (nhiệt độ ≥ 40°C, PM2.5 ≥ 75, CO₂ ≥ 1500)
4. → Phát cảnh báo **degraded** (mức độ suy giảm)
5. Sensor & Decision **tiếp tục chạy** — hệ **không sập toàn bộ**

Kết quả analysis đến muộn (sau fallback) bị **bỏ qua** — tránh cảnh báo trùng lặp

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| Ngôn ngữ | Python 3.11 |
| Broker | Eclipse Mosquitto 2 |
| MQTT client | Paho MQTT |
| AI | scikit-learn → ONNX → ONNX Runtime |
| Đóng gói | Docker Compose (2 vCPU, 4 GB mỗi agent) |
| Quan sát | Flask + WebSocket + Chart.js (dashboard) |
| Đo lường | psutil, script thu thập metrics, docker stats |

---

## Cấu trúc dự án

| Thư mục / module | Chức năng |
|------------------|-----------|
| agents/ | Ba agent: sensor, analysis, decision |
| shared/ | Schema message, cấu hình, model ONNX, metrics |
| broker/ | Cấu hình MQTT broker |
| dashboard/ | Giao diện web giám sát realtime |
| scripts/ | Huấn luyện, kiểm thử, đo lường, mô phỏng lỗi |
| models/ | Model ONNX phát hiện bất thường |
| reports/ | Số liệu thực nghiệm & báo cáo |

**Quy ước:** không import chéo agent, bản tin lỗi không làm crash, mọi message có mã truy vết

---

## Triển khai & tái lập

| Bước | Mô tả |
|------|-------|
| 1 | Khởi động stack Docker (3 agent + broker + dashboard) |
| 2 | Kiểm tra pipeline bình thường (3 chu kỳ E2E) |
| 3 | Thu thập metrics trong cửa sổ 40 giây |
| 4 | Mô phỏng lỗi: dừng Analysis Agent |
| 5 | Xác nhận cảnh báo degraded, hệ vẫn hoạt động |

- Dashboard truy cập tại **cổng 5001** (host)
- Mỗi agent giới hạn **2 vCPU / 4 GB** — mô phỏng VM edge

---

## Thiết lập thí nghiệm

| Tham số | Giá trị |
|---------|---------|
| Nền tảng | Docker Compose |
| Giới hạn agent | 2 vCPU, 4 GB RAM, CPU-only |
| Cửa sổ đo | **40 giây** |
| Chu kỳ sensor | 2 giây |
| Timeout Analysis | 5 giây |
| Ngày đo | 2026-07-27 |

---

## Kết quả — tài nguyên (RAM)

| Thành phần | CPU (mẫu) | RAM sử dụng | Giới hạn |
|------------|-----------|-------------|----------|
| sensor_agent | 0,08% | **20,89 MiB** | 4 GiB |
| analysis_agent | 0,21% | **51,54 MiB** | 4 GiB |
| decision_agent | 0,19% | **20,11 MiB** | 4 GiB |
| mqtt-broker | 0,54% | 2,74 MiB | — |

→ Analysis cao nhất ≈ **1,26%** trần 4 GB — **dư địa rất lớn** cho model phức tạp hơn

---

## Kết quả — độ trễ & throughput

| Chỉ số | Giá trị |
|--------|---------|
| Readings / results / alerts (40s) | **21 / 21 / 21** |
| E2E latency **p50** | **9,48 ms** |
| E2E latency **p95** | **49,72 ms** |
| Inference ONNX p50 / p95 | **4,98 ms / 6,94 ms** |
| Throughput | ≈ **0,525 msg/s** (khớp interval 2s) |
| Degraded (cửa sổ ổn định) | 0 |

E2E p50 ~10 ms — phù hợp giám sát môi trường gần realtime trên CPU biên

---

## Phân tích trade-off

| Trục | Quan sát |
|------|----------|
| **Độ trễ ↔ tài nguyên** | E2E p50 ~10 ms với RAM < 55 MiB/agent |
| **Chất lượng ↔ model** | Isolation Forest đủ demo synthetic; chưa phản ánh nhiễu cảm biến thực |
| **Độ bền ↔ độ trễ lỗi** | Timeout 5s giữ hệ sống; E2E degraded ~5s |
| **Framework** | Vòng MQTT tự viết — tránh overhead CrewAI/LangGraph |

---

## Kịch bản lỗi (fault injection)

| Quan sát | Kết quả |
|----------|---------|
| Dừng Analysis Agent | Decision phát cảnh báo degraded sau ~5s |
| E2E khi degraded | ~5010–5155 ms (chi phối bởi timeout) |
| Sensor Agent | Tiếp tục gửi dữ liệu |
| Decision Agent | Fallback ngưỡng, không crash |
| Phục hồi | Khởi động lại Analysis Agent |

→ Chứng minh **fault tolerance** — yêu cầu bắt buộc của đề tài

---

## Dashboard giám sát realtime

| Widget | Nội dung |
|--------|----------|
| Agent cards | Trạng thái alive / degraded / down + heartbeat |
| Sensor readings | 4 thông số cập nhật mỗi lần publish |
| E2E Latency chart | Biểu đồ 60 điểm, thống kê p50 / p95 / last |
| ONNX Inference chart | Thời gian suy luận theo thời gian |
| Alert feed | 30 cảnh báo gần nhất, màu theo mức độ |

Dữ liệu MQTT → WebSocket → trình duyệt (Flask-SocketIO + Chart.js)

---

## Kịch bản demo (5–10 phút)

1. Kiểm tra 4 container đang chạy, nêu giới hạn 2c/4GB
2. Xem mức sử dụng RAM — thấp hơn nhiều so với trần 4 GB
3. Theo dõi log pipeline theo mã truy vết
4. Chạy kiểm thử E2E bình thường
5. Mô phỏng lỗi: tắt Analysis Agent
6. Xác nhận cảnh báo degraded, sensor/decision vẫn sống
7. Phục hồi Analysis + mở dashboard

---

## Đóng góp chính

1. Hệ multi-agent biên **tái lập được**, tuân thủ ngân sách 2c/4GB & MQTT thật
2. Pipeline AI ONNX gọn (~1,16 MB), inference **~5 ms** trên CPU
3. Cơ chế **degraded mode** demo được — hệ không sập khi 1 agent lỗi
4. Bộ số liệu E2E/inference/RAM + dashboard + công cụ mô phỏng lỗi

---

## Hạn chế & hướng phát triển

**Hạn chế hiện tại:**
- Cảm biến giả lập, chưa triển khai phần cứng thật
- Chưa so sánh LLM nhỏ (Qwen2.5-0.5B Q4) vs ONNX
- Chưa đo năng lượng tiêu thụ / hybrid edge–cloud

**Hướng mở rộng:**
- Tích hợp cảm biến IoT thực (Modbus, Zigbee)
- Thử nghiệm LLM Q4 trên Analysis Agent (≤ 1,5B)
- Điều phối phi tập trung / replica Decision
- Triển khai lên 3 VM edge thật thay Docker Compose

---

<!-- _class: lead -->

## Kết luận

Hệ **multi-agent trên edge** cho giám sát môi trường đã được triển khai đầy đủ:

- 3 agent độc lập, giao tiếp **MQTT**, AI cục bộ **ONNX**
- E2E **p50 ≈ 9,5 ms**, RAM Analysis **≈ 52 MiB** — trong ngân sách 4 GB
- **Fault tolerance** qua chế độ degraded khi Analysis timeout
- Sẵn sàng demo, đo lường và mở rộng

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Cảm ơn!

## Q & A

**Mã nguồn & báo cáo đồ án** — repository edge-ai-multi-agent
