# BÁO CÁO ĐỒ ÁN CUỐI KỲ

## TRIỂN KHAI HỆ THỐNG MULTI-AGENT TRÊN EDGE  
### Ứng dụng giám sát môi trường thông minh với suy luận AI cục bộ

---

| Mục | Nội dung |
|-----|----------|
| **Học phần** | Công nghệ điện đám mây và điện toán biên (CE2206) |
| **Mã lớp** | CE2206.CH201 |
| **Đề tài** | Triển khai hệ thống Multi-Agent trên Edge |
| **Miền ứng dụng** | Giám sát môi trường thông minh |
| **Sinh viên thực hiện** | *[Họ và tên]* |
| **Mã số sinh viên** | *[MSSV]* |
| **Giảng viên hướng dẫn** | *[Họ và tên giảng viên]* |
| **Cơ sở đào tạo** | *[Tên trường / Khoa]* |
| **Thời gian thực hiện** | 07/2026 – 08/2026 |
| **Ngày nộp** | *[dd/mm/yyyy]* |

> **Ghi chú biên tập:** Các mục đánh dấu `*[...]*` cần được sinh viên điền trước khi in/nộp. Số liệu thực nghiệm lấy từ `reports/metrics_run.json` (cửa sổ đo 40 giây, ngày 2026-07-27).
>
> **Bản LaTeX:** [`reports/latex/bao-cao.tex`](latex/bao-cao.tex) — một file duy nhất; biên dịch bằng pdfLaTeX (`latexmk -pdf bao-cao.tex`).

---

## LỜI CAM ĐOAN

Tôi xin cam đoan báo cáo này là công trình nghiên cứu và triển khai của cá nhân/nhóm dưới sự hướng dẫn của giảng viên phụ trách học phần. Các kết quả đo lường trình bày trong báo cáo được thu thập từ hệ thống đã triển khai; phần tham khảo đã được trích dẫn đầy đủ. Tôi xin chịu trách nhiệm về tính trung thực của nội dung báo cáo.

*[Chữ ký – Họ tên – Ngày]*

---

## LỜI CẢM ƠN

Em xin gửi lời cảm ơn chân thành tới Quý Thầy/Cô phụ trách học phần Công nghệ điện đám mây và điện toán biên đã định hướng đề tài, góp ý kỹ thuật và tạo điều kiện để em hoàn thành đồ án. Em cũng cảm ơn các nguồn tài liệu mã nguồn mở (Eclipse Mosquitto, ONNX Runtime, scikit-learn, Docker) đã hỗ trợ quá trình hiện thực hóa hệ thống.

---

## TÓM TẮT

Điện toán biên (edge computing) đặt suy luận và điều phối gần nguồn dữ liệu nhằm giảm độ trễ và phụ thuộc đường truyền lên đám mây. Đồ án này thiết kế, triển khai và đánh giá định lượng một hệ **multi-agent** trên môi trường edge tài nguyên hạn chế (**2 vCPU / 4 GB RAM / CPU-only** cho mỗi agent), phục vụ miền **giám sát môi trường thông minh**.

Hệ thống gồm ba agent vai trò tách biệt: (i) **Sensor Agent** thu thập và chuẩn hóa dữ liệu cảm biến giả lập (nhiệt độ, độ ẩm, PM2.5, CO₂); (ii) **Analysis Agent** thực hiện **suy luận AI cục bộ** bằng mô hình Isolation Forest xuất **ONNX**, chạy trên **ONNX Runtime**; (iii) **Decision Agent** đóng vai **orchestrator tập trung nhẹ**, phát cảnh báo và xử lý lỗi khi Analysis timeout bằng fallback ngưỡng cứng (`degraded`). Toàn bộ giao tiếp đi qua **MQTT** (Eclipse Mosquitto) với schema JSON thống nhất và `trace_id` để đo độ trễ end-to-end (E2E).

Kết quả đo trên Docker Compose cho thấy: E2E latency **p50 ≈ 9,48 ms**, **p95 ≈ 49,72 ms**; thời gian inference ONNX **p50 ≈ 4,98 ms**; RAM đỉnh quan sát của Analysis Agent khoảng **51,5 MiB** — còn rất nhiều dư địa so với trần 4 GB. Khi Analysis bị ngắt, Decision vẫn phát alert `degraded` sau khoảng thời gian timeout cấu hình (5 s) mà không làm sập toàn hệ. Hệ thống kèm dashboard giám sát realtime và bộ script đo lường/fault-injection phục vụ demo và tái lập thí nghiệm.

**Từ khóa:** điện toán biên, multi-agent, MQTT, ONNX, phát hiện bất thường, giám sát môi trường, fault tolerance, đo lường hiệu năng.

---

## ABSTRACT

Edge computing brings inference and coordination closer to data sources to reduce latency and cloud dependency. This project designs, implements, and quantitatively evaluates a multi-agent system on constrained edge nodes (2 vCPU / 4 GB RAM / CPU-only per agent) for smart environmental monitoring.

Three agents with distinct roles communicate exclusively over MQTT: a sensor agent publishes normalized readings; an analysis agent performs local ONNX-based Isolation Forest inference; and a decision agent acts as a lightweight centralized orchestrator with threshold-based fallback when analysis times out. End-to-end latency is traced via `trace_id`. Measured results show p50/p95 E2E latency of approximately 9.48 ms / 49.72 ms, ONNX inference p50 of 4.98 ms, and peak analysis memory near 51.5 MiB—well within the 4 GB budget. Fault injection confirms degraded-mode continuity without total system failure.

**Keywords:** edge computing, multi-agent, MQTT, ONNX, anomaly detection, environmental monitoring, fault tolerance, performance measurement.

---

## MỤC LỤC

1. [Chương 1. Mở đầu](#chương-1-mở-đầu)  
2. [Chương 2. Cơ sở lý thuyết và công nghệ liên quan](#chương-2-cơ-sở-lý-thuyết-và-công-nghệ-liên-quan)  
3. [Chương 3. Phân tích yêu cầu và lựa chọn giải pháp](#chương-3-phân-tích-yêu-cầu-và-lựa-chọn-giải-pháp)  
4. [Chương 4. Thiết kế hệ thống](#chương-4-thiết-kế-hệ-thống)  
5. [Chương 5. Hiện thực và triển khai](#chương-5-hiện-thực-và-triển-khai)  
6. [Chương 6. Thực nghiệm và đánh giá](#chương-6-thực-nghiệm-và-đánh-giá)  
7. [Chương 7. Kết luận và hướng phát triển](#chương-7-kết-luận-và-hướng-phát-triển)  
8. [Tài liệu tham khảo](#tài-liệu-tham-khảo)  
9. [Phụ lục](#phụ-lục)

**Danh mục bảng:** Bảng 3.1–6.4  
**Danh mục hình:** Hình 4.1–4.3 (sơ đồ ASCII trong báo cáo; có thể vẽ lại khi xuất Word/PDF)

---

## DANH MỤC TỪ VIẾT TẮT

| Viết tắt | Diễn giải |
|----------|-----------|
| AI | Artificial Intelligence — Trí tuệ nhân tạo |
| CPU | Central Processing Unit |
| E2E | End-to-End — Từ đầu đến cuối pipeline |
| IoT | Internet of Things |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| MQTT | Message Queuing Telemetry Transport |
| ONNX | Open Neural Network Exchange |
| p50 / p95 | Phân vị thứ 50 / 95 của phân phối độ trễ |
| QoS | Quality of Service |
| RAM | Random Access Memory |
| RSS | Resident Set Size |
| VM | Virtual Machine |
| WS | WebSocket |

---

# CHƯƠNG 1. MỞ ĐẦU

## 1.1. Đặt vấn đề

Sự phát triển của IoT và các ứng dụng giám sát liên tục đặt ra yêu cầu xử lý dữ liệu gần nguồn phát sinh. Việc đưa toàn bộ suy luận lên đám mây có thể làm tăng độ trễ, phụ thuộc băng thông và đặt ra rủi ro khi mất kết nối. **Điện toán biên** giải quyết một phần các hạn chế này bằng cách triển khai suy luận và điều phối trên các nút gần thiết bị cảm biến.

Đồng thời, nhiều hệ thống biên không còn là một tiến trình đơn lẻ mà được tổ chức thành các **agent** với vai trò chuyên biệt (thu thập, phân tích, quyết định). Việc phối hợp các agent trong ngân sách tài nguyên chặt (CPU, RAM hạn chế, không GPU) đòi hỏi lựa chọn giao thức nhẹ, mô hình AI đủ nhỏ, và cơ chế chịu lỗi để hệ thống không sụp đổ khi một nút mất phản hồi.

Đề tài học phần CE2206 yêu cầu hiện thực hóa các năng lực trên một cách **định lượng**: không chỉ “chạy được demo”, mà phải đo tài nguyên, độ trễ (p50/p95), throughput và chứng minh ít nhất một kịch bản lỗi được xử lý an toàn.

## 1.2. Mục tiêu đồ án

Đồ án hướng tới các mục tiêu cụ thể sau:

1. **Thiết kế và triển khai** hệ multi-agent (≥ 3 agent, vai trò khác nhau) trên môi trường edge mô phỏng bằng container/VM, mỗi agent giới hạn **2 vCPU / 4 GB RAM**, **CPU-only**.  
2. **Đảm bảo giao tiếp thật qua mạng** (MQTT), không giả lập bằng gọi hàm nội bộ hay shared memory giữa các agent.  
3. **Tích hợp suy luận AI cục bộ** trên ít nhất một agent (Analysis), với mô hình tối ưu cho biên (ONNX).  
4. **Xây dựng cơ chế điều phối tập trung nhẹ** tại Decision Agent, kèm xử lý timeout Analysis → fallback ngưỡng + trạng thái `degraded`.  
5. **Đánh giá định lượng** trade-off giữa độ trễ, tài nguyên và chất lượng vận hành; cung cấp số liệu có thể tái lập.  
6. **Bổ sung công cụ quan sát** (dashboard realtime) phục vụ demo và giám sát vận hành.

## 1.3. Phạm vi nghiên cứu

**Trong phạm vi:**

- Miền giám sát môi trường (nhiệt độ, độ ẩm, PM2.5, CO₂) với dữ liệu cảm biến **giả lập** có kiểm soát.  
- Ba agent + MQTT broker + (tuỳ chọn) dashboard quan sát.  
- Model anomaly detection cổ điển xuất ONNX; không bắt buộc LLM trong bản nộp chính.  
- Triển khai Docker Compose với resource limit tương đương đề bài.

**Ngoài phạm vi (ghi nhận là hạn chế / hướng mở rộng):**

- Cảm biến phần cứng thật và hiệu chuẩn môi trường thực địa.  
- So sánh đầy đủ nhiều mức lượng tử hóa LLM / pruning.  
- Đo năng lượng tiêu thụ và chi phí vận hành dài hạn.  
- Hybrid edge–cloud production (chỉ thảo luận định hướng).

## 1.4. Phương pháp thực hiện

Đồ án kết hợp:

- **Phân tích yêu cầu** từ đề bài và ràng buộc cứng về tài nguyên/giao tiếp/fault.  
- **Thiết kế kiến trúc** theo pipeline Sensor → Analysis → Decision, điều phối tập trung nhẹ.  
- **Hiện thực tăng dần** (sensor MQTT → analysis ONNX → decision + fallback → deploy + metrics → dashboard).  
- **Thực nghiệm có kiểm soát:** thu thập metrics trong cửa sổ thời gian cố định; inject lỗi Analysis; đối chiếu với mục tiêu đề.

## 1.5. Đóng góp chính

1. Một hệ multi-agent biên **tái lập được**, tuân thủ ngân sách 2c/4GB và giao tiếp MQTT thật.  
2. Pipeline AI cục bộ ONNX gọn (~1,16 MB model) với độ trễ inference mili-giây trên CPU.  
3. Cơ chế **fault tolerance** có thể demo: timeout Analysis → alert `degraded`, các agent còn lại tiếp tục sống.  
4. Bộ số liệu E2E/inference/tài nguyên và dashboard realtime hỗ trợ đánh giá và trình diễn.

## 1.6. Cấu trúc báo cáo

- **Chương 2** trình bày cơ sở lý thuyết liên quan.  
- **Chương 3** phân tích yêu cầu và lý do lựa chọn miền/giải pháp.  
- **Chương 4** mô tả thiết kế kiến trúc, giao thức và mô hình AI.  
- **Chương 5** trình bày hiện thực, cấu trúc mã nguồn và triển khai.  
- **Chương 6** báo cáo thực nghiệm, bảng số liệu và phân tích trade-off.  
- **Chương 7** kết luận và hướng phát triển.

---

# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ LIÊN QUAN

## 2.1. Điện toán biên và Edge AI

Điện toán biên đẩy một phần tính toán, lưu trữ và suy luận ra khỏi trung tâm dữ liệu truyền thống, tiến gần thiết bị đầu cuối. **Edge AI** nhấn mạnh việc chạy mô hình học máy ngay trên nút biên, nhằm:

- Giảm độ trễ phản hồi;  
- Giảm lưu lượng đẩy thô lên đám mây;  
- Tăng khả năng hoạt động khi liên kết đám mây không ổn định.

Tuy nhiên, nút biên thường bị ràng buộc mạnh về CPU, RAM, năng lượng và thiếu GPU. Do đó, lựa chọn mô hình nhỏ, runtime nhẹ và đo lường tài nguyên là **trọng tâm kỹ thuật**, không phải phần phụ.

## 2.2. Hệ multi-agent

Một **agent** được hiểu là thực thể phần mềm có mục tiêu, trạng thái và khả năng tương tác với môi trường/agent khác. Hệ multi-agent phân chia trách nhiệm (chuyên môn hóa), đồng thời đặt ra bài toán **phối hợp** (coordination) và **chịu lỗi** (fault tolerance).

Hai mô hình điều phối phổ biến:

| Mô hình | Đặc điểm | Phù hợp khi |
|---------|----------|-------------|
| **Tập trung** | Một orchestrator tổng hợp và ra quyết định | Pipeline rõ ràng, cần điểm kiểm soát thống nhất |
| **Phi tập trung** | Các agent đàm phán / đồng thuận ngang hàng | Hệ lớn, tránh single point of failure |

Trong đồ án, nhóm chọn **điều phối tập trung nhẹ**: Decision Agent là orchestrator, nhưng không kéo theo framework nặng (CrewAI, LangGraph, AutoGen) vì nguy cơ vượt ngân sách 4 GB RAM trên biên.

## 2.3. MQTT trong hệ IoT/Edge

MQTT là giao thức pub/sub nhẹ, phổ biến trong IoT. Broker trung gian (ở đây: Eclipse Mosquitto) nhận bản tin từ publisher và chuyển tới subscriber theo topic. Ưu điểm với biên:

- Overhead thấp hơn polling HTTP;  
- Tách rời producer/consumer theo không gian và thời gian;  
- Hỗ trợ QoS (đồ án dùng QoS 1 cho luồng nghiệp vụ để giảm mất tin).

## 2.4. Phát hiện bất thường và ONNX

**Isolation Forest** là thuật toán học không giám sát phù hợp phát hiện điểm bất thường trên dữ liệu số nhiều chiều, chi phí suy luận thấp. Pipeline thực tế thường gồm chuẩn hóa đặc trưng (`StandardScaler`) rồi phân loại bất thường.

**ONNX** là định dạng trung gian cho mô hình học máy. Xuất model từ scikit-learn sang ONNX và chạy bằng **ONNX Runtime** (CPU) giúp:

- Tách pha huấn luyện khỏi pha suy luận trên biên;  
- Giảm phụ thuộc stack huấn luyện nặng tại runtime;  
- Dễ đóng gói trong container nhỏ.

## 2.5. Đo lường hiệu năng trên biên

Các chỉ số then chốt theo yêu cầu đề:

- **Tài nguyên:** peak RAM (RSS), CPU trung bình/đỉnh;  
- **Độ trễ:** phân vị p50 và p95 (ổn định hơn so với chỉ dùng mean);  
- **Throughput:** số message/suy luận trên đơn vị thời gian;  
- **E2E latency:** từ sự kiện gốc (sensor publish / `ts` của reading) đến quyết định (decision alert), nối bằng `trace_id`.

Việc đo lường phải gắn với điều kiện chạy thật (container có limit), tránh đo trên máy mạnh rồi suy luận sai về khả năng biên.

## 2.6. Tóm tắt chương

Chương này thiết lập nền tảng: Edge AI đòi hỏi tối ưu tài nguyên; multi-agent cần giao thức và điều phối rõ; MQTT/ONNX phù hợp ràng buộc biên; metrics p50/p95 và E2E là chuẩn đánh giá bắt buộc của đề tài.

---

# CHƯƠNG 3. PHÂN TÍCH YÊU CẦU VÀ LỰA CHỌN GIẢI PHÁP

## 3.1. Yêu cầu từ đề bài

Bảng 3.1 tóm tắt ràng buộc cứng và cách đồ án đáp ứng.

**Bảng 3.1. Đối chiếu yêu cầu đề bài và giải pháp**

| Hạng mục | Yêu cầu | Giải pháp đồ án |
|----------|---------|-----------------|
| Số agent | ≥ 3, vai trò khác nhau | Sensor, Analysis, Decision |
| Phần cứng | 2 vCPU, 4 GB, CPU-only / agent | Docker `cpus: 2.0`, `mem_limit: 4g` |
| Giao tiếp | Qua mạng thật | MQTT Mosquitto + schema JSON |
| AI cục bộ | ≥ 1 agent inference trên edge | Analysis + ONNX Runtime |
| Điều phối | Mô tả rõ tập trung/phi tập trung | Tập trung nhẹ tại Decision |
| Fault | ≥ 1 scenario, hệ không sập toàn bộ | Analysis timeout → fallback `degraded` |
| Metrics | RAM/CPU, latency p50/p95, throughput, E2E | `collect_metrics.py` + `metrics_run.json` |
| Sản phẩm | Source, video demo, báo cáo | Repo + checklist demo + báo cáo này |

Ba năng lực được đề nhấn mạnh khi chấm điểm: **(1)** tối ưu tài nguyên, **(2)** phối hợp phân tán có xử lý lỗi, **(3)** đánh giá định lượng trade-off.

## 3.2. Lựa chọn miền ứng dụng

Đề gợi ý nhiều hướng (vision, RAG, predictive maintenance, giám sát môi trường…). Nhóm chọn **giám sát môi trường thông minh** vì:

1. Khớp ví dụ minh họa trong đề; pipeline ba vai trò tách bạch.  
2. Dữ liệu cảm biến dễ giả lập và **tái lập thí nghiệm**.  
3. Model anomaly detection vừa khung 4 GB; vẫn mở được hướng LLM nhỏ Q4 nếu cần điểm cộng.  
4. Dễ inject lỗi (ngắt Analysis) để demo fault handling.

Pipeline nghiệp vụ:

```text
Sensor Agent  →  Analysis Agent (AI local)  →  Decision Agent
   (thu thập)         (phát hiện bất thường)      (cảnh báo / hành động)
```

## 3.3. Yêu cầu chức năng

**RF-01.** Sensor định kỳ phát bản tin cảm biến chuẩn hóa lên MQTT.  
**RF-02.** Analysis nhận reading, chạy inference cục bộ, phát kết quả (score, label, `inference_ms`).  
**RF-03.** Decision nhận kết quả, áp chính sách cảnh báo, phát `DecisionAlert`.  
**RF-04.** Decision theo dõi timeout theo `trace_id`; hết hạn thì fallback threshold và đánh dấu `degraded=true`.  
**RF-05.** Mọi agent phát heartbeat; message nghiệp vụ mang `trace_id`.  
**RF-06.** Message JSON sai schema bị từ chối/ghi log, **không** làm crash process.  
**RF-07.** (Mở rộng) Dashboard subscribe MQTT và hiển thị trạng thái, latency, alert realtime.

## 3.4. Yêu cầu phi chức năng

**RNF-01. Tài nguyên:** mỗi agent ≤ 2 vCPU, ≤ 4 GB RAM, không GPU.  
**RNF-02. Độ trễ:** E2E ở mức mili-giây trong điều kiện ổn định (mục tiêu thực nghiệm: p50 < 100 ms).  
**RNF-03. Khả năng sống sót:** mất Analysis không làm dừng Sensor/Decision.  
**RNF-04. Tái lập:** có script deploy, đo metrics, inject fault.  
**RNF-05. Tách biệt tiến trình:** cấm gộp ba agent một process để “demo nhanh”.

## 3.5. Các phương án và quyết định thiết kế

**Bảng 3.2. Quyết định thiết kế chính**

| Hạng mục | Phương án chọn | Phương án loại / trì hoãn | Lý do |
|----------|----------------|---------------------------|-------|
| Giao tiếp | MQTT | gRPC/HTTP sync chặt | Phù hợp IoT, nhẹ, pub/sub |
| Điều phối | Tập trung nhẹ | Phi tập trung / framework nặng | Đủ rõ ràng, ít RAM |
| Model | Isolation Forest → ONNX | LLM 3B Q4 ngay từ đầu | An toàn trần 4 GB |
| Runtime | ONNX Runtime CPU | PyTorch full trên biên | Nhẹ, đủ cho inference |
| Deploy | Docker Compose limit | Nhiều process một container | Đúng tinh thần “1 agent / 1 VM” |
| Fallback | Threshold rules | Chỉ log rồi im lặng | Vẫn ra quyết định khi AI mất |

## 3.6. Tóm tắt chương

Yêu cầu đề bài được chuyển thành RF/RNF cụ thể; miền giám sát môi trường và stack MQTT + ONNX + orchestrator tập trung nhẹ được chọn có chủ đích để cân bằng **tính đúng đề**, **khả năng chạy trong 4 GB**, và **đo được số liệu**.

---

# CHƯƠNG 4. THIẾT KẾ HỆ THỐNG

## 4.1. Kiến trúc tổng thể

**Hình 4.1. Kiến trúc logic hệ multi-agent trên edge**

```text
┌─────────────────┐     MQTT      ┌──────────────────┐     MQTT      ┌──────────────────┐
│  Sensor Agent   │──────────────▶│  Analysis Agent  │──────────────▶│  Decision Agent  │
│  Edge VM #1     │  readings     │  Edge VM #2      │   results     │  Edge VM #3      │
│  2 vCPU / 4GB   │               │  + ONNX Runtime  │               │  orchestrator    │
└────────┬────────┘               └────────┬─────────┘               └────────┬─────────┘
         │                                 │                                  │
         │                 heartbeat / control                                │
         └─────────────────┬───────────────┴──────────────────┬───────────────┘
                           │                                  │
                    ┌──────▼──────────────────────────────────▼──────┐
                    │           Mosquitto MQTT Broker                │
                    └──────────────────────┬─────────────────────────┘
                                           │ (subscribe quan sát)
                                    ┌──────▼──────┐
                                    │  Dashboard  │
                                    │  (tuỳ chọn) │
                                    └─────────────┘
```

Mỗi agent là **một container/process riêng**. Thành phần `shared/` chỉ chứa schema, cấu hình và tiện ích đo lường — **không** chứa logic điều phối và **không** cho phép import chéo giữa các agent như thư viện gọi hàm.

## 4.2. Vai trò từng agent

**Bảng 4.1. Phân công trách nhiệm**

| Agent | Được phép | Không được phép |
|-------|-----------|-----------------|
| `sensor_agent` | Giả lập/chuẩn hóa cảm biến; publish reading + heartbeat | Chạy model AI; ra quyết định cảnh báo |
| `analysis_agent` | Subscribe reading; inference cục bộ; publish result | Điều phối toàn hệ; bỏ qua MQTT |
| `decision_agent` | Policy/alert; timeout fallback; heartbeat/control | Thay thế hoàn toàn AI chính (chỉ fallback khi degraded) |
| `dashboard` | Quan sát MQTT, hiển thị metrics/alert | Tham gia vòng quyết định nghiệp vụ |

## 4.3. Luồng xử lý end-to-end

**Hình 4.2. Luồng sự kiện bình thường**

1. Sensor tạo `SensorReading` (có `trace_id`, `ts`) → publish `edge/sensor/readings`.  
2. Analysis parse reading → ONNX infer → publish `AnalysisResult` (`anomaly_score`, `is_anomaly`, `inference_ms`, cùng `trace_id`).  
3. Decision map kết quả → `DecisionAlert` (`severity`, `action`, `reason`, `e2e_latency_ms`).  
4. Dashboard (nếu bật) nhận và hiển thị realtime.

**Hình 4.3. Luồng sự kiện khi Analysis không phản hồi**

1. Decision lưu `PendingTrace` khi thấy reading (hoặc theo dõi theo `trace_id`).  
2. Hết `analysis_timeout_sec` (mặc định **5 s**) mà chưa có result → gọi `threshold_fallback`.  
3. Publish alert với `severity=degraded`, `degraded=true`.  
4. Sensor và Decision tiếp tục chạy; Analysis có thể được khởi động lại sau.  
5. Result đến muộn sau khi đã fallback được **bỏ qua** để tránh double-alert.

## 4.4. Thiết kế giao thức MQTT và schema

**Bảng 4.2. Topics**

| Topic | Publisher | Subscriber |
|-------|-----------|------------|
| `edge/sensor/readings` | sensor | analysis, decision, dashboard |
| `edge/analysis/results` | analysis | decision, dashboard |
| `edge/decision/alerts` | decision | dashboard / log |
| `edge/system/heartbeat` | mọi agent | decision, dashboard |
| `edge/system/control` | decision | sensor, analysis |

**Nguyên tắc schema (`shared/schemas.py`):**

- Payload JSON UTF-8; dataclass tương ứng `SensorReading`, `AnalysisResult`, `DecisionAlert`, `Heartbeat`.  
- Field bắt buộc được kiểm tra trong `from_json`; thiếu field → `ValueError` / reject, không crash vòng lặp agent.  
- `trace_id` là khóa nối E2E.  
- QoS 1 cho luồng nghiệp vụ.

## 4.5. Thiết kế mô hình AI cục bộ

**Bảng 4.3. Thông số mô hình**

| Thuộc tính | Giá trị |
|------------|---------|
| Thuật toán | Isolation Forest + StandardScaler |
| Thư viện huấn luyện | scikit-learn |
| Xuất mô hình | skl2onnx → `models/anomaly.onnx` (~1,16 MB) |
| Runtime suy luận | ONNX Runtime, `CPUExecutionProvider` |
| Đặc trưng | `temperature_c`, `humidity_pct`, `pm25_ugm3`, `co2_ppm` |
| Huấn luyện | 2000 mẫu normal giả lập; `contamination=0.05`; `n_estimators=100` |
| Kiểm tra nhanh trên synthetic | Normal nhận diện đúng ≈ 96%; anomaly ≈ 100% |

Lựa chọn này ưu tiên **độ nhỏ và độ trễ thấp** hơn độ phức tạp biểu diễn. LLM nhỏ (ví dụ Qwen2.5-0.5B Q4) được xem là hướng điểm cộng, không phải đường chính của bản nộp.

## 4.6. Chính sách quyết định và ngưỡng fallback

Khi có kết quả AI:

- `is_anomaly = false` → `severity=info`, `action=continue_monitoring`.  
- `is_anomaly = true` → `raise_alert`; `critical` nếu score ≥ 0,05, ngược lại `warning`.

Khi timeout, ngưỡng cứng (cấu hình `configs/default.yaml`):

- Nhiệt độ ≥ 40 °C  
- PM2.5 ≥ 75 µg/m³  
- CO₂ ≥ 1500 ppm  

Vượt ngưỡng → alert degraded kèm lý do; không vượt → vẫn phát bản tin degraded ghi nhận timeout nhưng ngưỡng OK.

## 4.7. Thiết kế đo lường và quan sát

- Trong agent: `MetricsCollector` (`psutil`) ghi mẫu theo chu kỳ.  
- Ngoài agent: `scripts/collect_metrics.py` subscribe MQTT, tính p50/p95 E2E & inference, kết hợp `docker stats`.  
- Dashboard: Flask + Flask-SocketIO, subscribe toàn bộ topic, đẩy WebSocket tới trình duyệt (biểu đồ latency, feed alert, trạng thái heartbeat).

## 4.8. Tóm tắt chương

Kiến trúc ba agent + MQTT + orchestrator tập trung nhẹ bảo đảm đúng ràng buộc đề; schema/`trace_id` phục vụ E2E; ONNX phục vụ AI biên; timeout/fallback phục vụ fault tolerance; metrics/dashboard phục vụ đánh giá và demo.

---

# CHƯƠNG 5. HIỆN THỰC VÀ TRIỂN KHAI

## 5.1. Môi trường công nghệ

**Bảng 5.1. Stack công nghệ**

| Thành phần | Công nghệ |
|------------|-----------|
| Ngôn ngữ | Python 3.11 |
| Broker | Eclipse Mosquitto 2 |
| MQTT client | paho-mqtt |
| AI | scikit-learn, skl2onnx, onnxruntime |
| Đóng gói | Docker / Docker Compose |
| Quan sát | Flask, Flask-SocketIO, Chart.js (dashboard) |
| Đo tài nguyên | psutil, docker stats |

## 5.2. Cấu trúc mã nguồn

```text
edge-ai-multi-agent/
├── agents/
│   ├── sensor_agent/main.py
│   ├── analysis_agent/main.py
│   └── decision_agent/main.py
├── broker/mosquitto.conf
├── shared/          # schemas, config, metrics, onnx_model
├── configs/default.yaml
├── dashboard/       # app.py + templates
├── scripts/         # train, deploy, verify, collect, fault-inject
├── models/          # anomaly.onnx
├── metrics/         # log runtime
├── reports/         # số liệu & báo cáo
└── docs/            # quy ước, kiến trúc, checklist
```

Quy ước bắt buộc khi phát triển được ghi trong `docs/QUY-UOC-CODE.md` (không import chéo agent, không nới limit để “cho chạy được”, malformed không crash, v.v.).

## 5.3. Hiện thực các agent

### 5.3.1. Sensor Agent

- Đọc cấu hình `interval_sec` (mặc định 2 s), tỷ lệ anomaly giả lập.  
- Sinh vector cảm biến; gán `trace_id` UUID.  
- Publish QoS 1; định kỳ gửi `Heartbeat`.  
- Ghi metrics nội bộ.

### 5.3.2. Analysis Agent

- Load `OnnxAnomalyModel` từ `models/anomaly.onnx`.  
- Subscribe readings; parse bằng `SensorReading.from_json`.  
- Đo thời gian suy luận (`inference_ms`); publish `AnalysisResult`.  
- Đếm và bỏ qua bản tin malformed.

### 5.3.3. Decision Agent

- Subscribe readings, results, heartbeat.  
- Duy trì bảng `PendingTrace` theo `trace_id`.  
- Thread/timer kiểm tra timeout → `threshold_fallback`.  
- Tính `e2e_latency_ms` từ `ts` của reading đến thời điểm phát alert.

## 5.4. Huấn luyện và đóng gói model

Script `scripts/train_anomaly_model.py` sinh dữ liệu synthetic, huấn luyện scaler + Isolation Forest, xuất ONNX và metadata. Trong Dockerfile, bước train được chạy khi build image để Analysis Agent có model sẵn sàng trên mọi máy triển khai.

## 5.5. Triển khai Docker và giới hạn tài nguyên

Mỗi service agent trong `docker-compose.yml` khai báo:

```yaml
cpus: 2.0
mem_limit: 4g
memswap_limit: 4g
```

Không gắn GPU. Broker Mosquitto dùng image chính thức; các agent dùng image chung `edge-ai-agent:latest` với `command` khác nhau. Dashboard giới hạn nhẹ hơn (quan sát, không tính là agent đề bài): 0,5 CPU / 256 MB; trên macOS host port thường map **5001** vì cổng 5000 hay bị hệ điều hành chiếm.

## 5.6. Công cụ kiểm thử và fault injection

| Script | Mục đích |
|--------|----------|
| `verify_decision_mqtt.py` | Chứng minh pipeline E2E bình thường |
| `inject_fault_analysis.sh` | Dừng container Analysis |
| `verify_decision_mqtt.py --require-degraded` | Chứng minh fallback |
| `collect_metrics.py` | Thu thập và ghi `reports/metrics_run.json` |

## 5.7. Quy trình tái lập (tóm tắt)

```bash
docker compose up -d --build
python scripts/verify_decision_mqtt.py --count 3
python scripts/collect_metrics.py --duration 40 --out reports/metrics_run.json
./scripts/inject_fault_analysis.sh docker
python scripts/verify_decision_mqtt.py --count 2 --require-degraded --timeout 30
docker compose start analysis_agent
```

Chi tiết checklist quay video demo: `docs/checklist-demo.md`.

## 5.8. Tóm tắt chương

Hiện thực bám sát thiết kế: ba tiến trình tách biệt, MQTT + schema, ONNX cục bộ, timeout/fallback, resource limit đúng đề, kèm công cụ verify/metrics/fault và dashboard quan sát.

---

# CHƯƠNG 6. THỰC NGHIỆM VÀ ĐÁNH GIÁ

## 6.1. Mục tiêu và giả thuyết thực nghiệm

Thực nghiệm nhằm trả lời:

1. Hệ có chạy ổn định trong giới hạn 2c/4GB không?  
2. Độ trễ E2E và inference có ở mức chấp nhận được cho giám sát gần realtime không?  
3. Khi Analysis mất, hệ còn phát quyết định (degraded) và không sập toàn bộ không?  
4. Trade-off nào nổi bật giữa tài nguyên, độ trễ và độ phức tạp mô hình?

## 6.2. Môi trường và cấu hình đo

**Bảng 6.1. Cấu hình thí nghiệm (cửa sổ ổn định)**

| Tham số | Giá trị |
|---------|---------|
| Nền tảng | Docker Compose |
| Giới hạn mỗi agent | 2 vCPU, 4 GB RAM, CPU-only |
| Cửa sổ đo | 40 giây |
| Chu kỳ sensor | 2 giây |
| Timeout Analysis | 5 giây |
| Ngày đo (bản ghi chính) | 2026-07-27 |
| Nguồn số liệu | `reports/metrics_run.json` |

## 6.3. Kết quả tài nguyên

**Bảng 6.2. Mẫu `docker stats` cuối cửa sổ đo**

| Thành phần | CPU (mẫu) | RAM sử dụng | Giới hạn |
|------------|-----------|-------------|----------|
| sensor_agent | 0,08% | 20,89 MiB | 4 GiB |
| analysis_agent | 0,21% | 51,54 MiB | 4 GiB |
| decision_agent | 0,19% | 20,11 MiB | 4 GiB |
| mqtt-broker | 0,54% | 2,74 MiB | (host) |

**Nhận xét:** Toàn bộ agent sử dụng RAM **≪ 4 GB** (Analysis cao nhất ≈ 1,26% hạn mức). Headroom lớn cho phép mở rộng model phức tạp hơn trong tương lai, miễn là đo lại dưới cùng limit.

## 6.4. Kết quả độ trễ và throughput

**Bảng 6.3. Latency và throughput (40 s, 21 mẫu E2E)**

| Chỉ số | Giá trị |
|--------|---------|
| Số readings / results / alerts | 21 / 21 / 21 |
| Degraded trong cửa sổ ổn định | 0 |
| E2E latency p50 | **9,48 ms** |
| E2E latency p95 | **49,72 ms** |
| E2E mean / max | 16,7 ms / 52,3 ms |
| Inference ONNX p50 / p95 | **4,98 ms / 6,94 ms** |
| Throughput mỗi tầng | ≈ **0,525 msg/s** (khớp interval 2 s) |

E2E được định nghĩa từ thời điểm gắn với `SensorReading` đến lúc phát `DecisionAlert` cùng `trace_id`.

**Nhận xét:** Phân vị p50 rất thấp; p95 cao hơn mean cho thấy đuôi phân phối (jitter khởi động/GC/scheduling container) cần được theo dõi, nhưng vẫn dưới 100 ms trong thí nghiệm này — phù hợp giám sát môi trường không đòi hỏi điều khiển vòng kín cực nhanh.

## 6.5. Kết quả kịch bản lỗi

**Bảng 6.4. Fault path — dừng Analysis Agent**

| Quan sát | Kết quả |
|----------|---------|
| Hành vi Decision | Phát alert `degraded=true` sau ~timeout 5 s |
| E2E khi degraded (demo trước) | Khoảng 5010–5155 ms (bị chi phối bởi timeout) |
| Sensor Agent | Tiếp tục publish |
| Decision Agent | Tiếp tục sống và ra quyết định fallback |
| Phục hồi | `docker compose start analysis_agent` |

Kịch bản chứng minh yêu cầu “hệ không sập toàn bộ” và làm rõ **trade-off**: tăng độ bền limping-mode đổi lấy độ trễ E2E lớn hơn khi AI mất.

## 6.6. Phân tích trade-off

| Trục phân tích | Quan sát |
|----------------|----------|
| Độ trễ ↔ tài nguyên | E2E p50 ~10 ms với RAM agent < 55 MiB — dư địa lớn trong 4 GB |
| Chất lượng ↔ độ phức tạp model | Isolation Forest đủ cho dữ liệu synthetic; chưa phản ánh nhiễu cảm biến thực địa |
| Độ bền ↔ độ trễ khi lỗi | Timeout 5 s giữ hệ sống nhưng kéo E2E khi degraded; có thể chỉnh theo SLA |
| Framework orchestration | Tự viết vòng MQTT tránh overhead framework nặng trên biên |
| Quan sát vận hành | Dashboard tăng trải nghiệm demo nhưng không thay metrics file phục vụ báo cáo |

## 6.7. Đối chiếu với mục tiêu đề bài

| Mục tiêu | Mức đạt |
|----------|---------|
| ≥ 3 agent vai trò khác nhau, 2c/4GB | Đạt |
| MQTT thật, không shared memory giả lập | Đạt |
| AI cục bộ trên edge | Đạt (ONNX) |
| Điều phối tập trung được mô tả và hiện thực | Đạt |
| ≥ 1 fault scenario | Đạt (timeout → degraded) |
| Metrics p50/p95, throughput, E2E | Đạt |
| Video demo 5–10 phút | *[Cần hoàn thiện theo checklist]* |

## 6.8. Thảo luận hạn chế thực nghiệm

1. Cảm biến giả lập — chưa đánh giá drift, nhiễu, thiếu mẫu thực.  
2. Cửa sổ 40 s đủ để chứng minh pipeline và số liệu chính, nhưng chưa phải stress test dài hạn.  
3. Chưa so sánh hệ thống với phương án LLM Q4 hay hybrid cloud trên cùng metric.  
4. Chưa đo năng lượng / nhiệt độ thiết bị biên vật lý.

## 6.9. Tóm tắt chương

Thực nghiệm xác nhận hệ chạy gọn trong ngân sách biên, độ trễ ổn định ở mili-giây khi đầy đủ ba agent, và chế độ degraded hoạt động đúng khi mất Analysis. Các hạn chế được nêu rõ để định hướng phát triển.

---

# CHƯƠNG 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 7.1. Kết luận

Đồ án đã thiết kế và triển khai thành công hệ **multi-agent trên edge** cho miền giám sát môi trường thông minh, đáp ứng các ràng buộc cốt lõi của học phần CE2206:

1. Ba agent tách biệt về vai trò và tiến trình, giới hạn **2 vCPU / 4 GB**, CPU-only.  
2. Giao tiếp **MQTT** với schema thống nhất và `trace_id` phục vụ truy vết E2E.  
3. Suy luận AI cục bộ bằng **Isolation Forest xuất ONNX**, độ trễ inference p50 ≈ 5 ms.  
4. Điều phối **tập trung nhẹ** tại Decision Agent, kèm fallback khi Analysis timeout.  
5. Đánh giá định lượng cho thấy E2E p50/p95 ≈ 9,5/49,7 ms và RAM đỉnh Analysis ≈ 51,5 MiB — phù hợp môi trường biên hạn chế.

Kết quả khẳng định rằng, với lựa chọn giao thức và mô hình phù hợp, hệ multi-agent Edge AI có thể đồng thời đạt **độ trễ thấp**, **tiêu thụ tài nguyên nhỏ**, và **khả năng chịu lỗi limping-mode** — ba trụ cột mà đề bài nhấn mạnh.

## 7.2. Hướng phát triển

1. **Dữ liệu thật:** nối cảm biến vật lý hoặc tập dữ liệu môi trường công khai; đánh giá lại precision/recall.  
2. **Điểm cộng đề bài:** so sánh ONNX với LLM nhỏ Q4 (0,5B–1,5B); đo RAM/latency theo mức quantize.  
3. **Hybrid edge–cloud:** đẩy summary/alert lên cloud khi có mạng; giữ quyết định tối thiểu trên biên khi mất mạng.  
4. **Vận hành:** bổ sung xác thực MQTT, TLS, và chính sách lưu trữ alert dài hạn.  
5. **Đo năng lượng:** ước lượng joule/inference trên thiết bị biên thật nếu có phần cứng.

## 7.3. Bài học kinh nghiệm

- Đo metrics **từ sớm** giúp tránh tình trạng “chạy được nhưng không chứng minh được”.  
- Giữ agent tách process ngay từ đầu tránh nợ kỹ thuật khi nộp theo tiêu chí VM riêng.  
- Ưu tiên model nhỏ đủ đúng đề trước khi tối ưu điểm cộng bằng LLM.

---

# TÀI LIỆU THAM KHẢO

1. Tài liệu đề bài học phần: *Triển khai hệ thống Multi-Agent trên Edge* — CE2206 (`de-tai-cuoi-ky-edge-ai.PDF`).  
2. Eclipse Foundation, *Eclipse Mosquitto — An open source MQTT broker*. https://mosquitto.org/  
3. OASIS, *MQTT Version 3.1.1 / 5.0 Specification*.  
4. ONNX Runtime, *ONNX Runtime documentation*. https://onnxruntime.ai/  
5. Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *ICDM*.  
6. Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python. *JMLR*.  
7. Shi, W., Cao, J., Zhang, Q., Li, Y., & Xu, L. (2016). Edge Computing: Vision and Challenges. *IEEE Internet of Things Journal*.  
8. Docker Inc., *Docker Compose resource constraints documentation*.  
9. Paho MQTT Python Client documentation.  
10. Tài liệu nội bộ đồ án: `docs/phan-tich-de-bai.md`, `docs/kien-truc.md`, `docs/QUY-UOC-CODE.md`, `reports/metrics_run.json`.

> Khi xuất bản chính thức, sinh viên nên chuẩn hóa trích dẫn theo quy định Khoa/Trường (IEEE / APA / kiểu Việt Nam) và bổ sung số trang nếu trích từ giáo trình in.

---

# PHỤ LỤC

## Phụ lục A. Cấu hình mặc định (`configs/default.yaml`) — trích yếu

- MQTT port: 1883  
- Sensor interval: 2 s; `anomaly_chance`: 0,05  
- Analysis backend: `onnx`; model: `models/anomaly.onnx`  
- Decision `analysis_timeout_sec`: 5  
- Ngưỡng fallback: temp 40 °C; PM2.5 75; CO₂ 1500  
- Resource targets: 2 vCPU, 4 GB, `gpu: false`

## Phụ lục B. Ví dụ schema message

**SensorReading (rút gọn):** `agent_id`, `temperature_c`, `humidity_pct`, `pm25_ugm3`, `co2_ppm`, `trace_id`, `ts`.

**AnalysisResult (rút gọn):** `agent_id`, `trace_id`, `anomaly_score`, `is_anomaly`, `label`, `inference_ms`, `ts`.

**DecisionAlert (rút gọn):** `agent_id`, `trace_id`, `severity`, `action`, `reason`, `e2e_latency_ms`, `degraded`, `ts`.

## Phụ lục C. Lệnh demo nhanh

Xem `docs/checklist-demo.md` và mục 5.7.

## Phụ lục D. Liên kết số liệu thô

- `reports/metrics_run.json` — kết quả đo cửa sổ 40 s.  
- `reports/bao-cao-ky-thuat.md` — bản tóm tắt kỹ thuật ngắn (song song với báo cáo này).

## Phụ lục E. Nhật ký phiên bản báo cáo

| Phiên bản | Ngày | Nội dung |
|-----------|------|----------|
| 1.0 | 2026-08-06 | Dự thảo báo cáo đồ án đầy đủ theo cấu trúc khoá luận / đồ án tốt nghiệp học phần |

---

**HẾT BÁO CÁO**

*Sinh viên hoàn thiện phần thông tin bìa, chữ ký cam đoan, và (nếu có) chèn hình vẽ lại từ sơ đồ ASCII trước khi in nộp.*
