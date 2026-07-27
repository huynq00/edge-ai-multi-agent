# Kiến trúc hệ thống (draft)

```text
┌─────────────────┐     MQTT      ┌──────────────────┐     MQTT      ┌──────────────────┐
│  Sensor Agent   │──────────────▶│  Analysis Agent  │──────────────▶│  Decision Agent  │
│  Edge VM #1     │  readings     │  Edge VM #2      │   results     │  Edge VM #3      │
│  2 vCPU / 4GB   │               │  2 vCPU / 4GB    │               │  2 vCPU / 4GB    │
│                 │               │  + ONNX / LLM    │               │  orchestrator    │
└────────┬────────┘               └────────┬─────────┘               └────────┬─────────┘
         │                                 │                                  │
         │            heartbeat / control  │                                  │
         └─────────────────┬───────────────┴──────────────────┬───────────────┘
                           │                                  │
                    ┌──────▼──────────────────────────────────▼──────┐
                    │           Mosquitto MQTT Broker                │
                    └────────────────────────────────────────────────┘
```

## Luồng tác vụ end-to-end

1. Sensor đọc/giả lập mẫu cảm biến → chuẩn hóa → publish `edge/sensor/readings`
2. Analysis subscribe → inference cục bộ → publish `edge/analysis/results`
3. Decision subscribe → áp rule/policy → publish `edge/decision/alerts`
4. Nếu analysis không phản hồi trong timeout → Decision dùng fallback + alert `degraded`

## Ràng buộc runtime

Mỗi agent process/container:

```bash
--cpus=2 --memory=4g --memory-swap=4g
```

Không gắn GPU. Đo metrics ngay trong agent và/hoặc `docker stats`.
