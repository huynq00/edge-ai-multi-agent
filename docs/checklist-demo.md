# Checklist demo video (5–10 phút)

1. `docker compose ps` — 4 container Up (broker + 3 agent), nêu giới hạn 2c/4GB.
2. `docker stats` — RAM mỗi agent ≪ 4GiB.
3. Log sensor → analysis → decision (theo `trace_id`).
4. `python scripts/verify_decision_mqtt.py --count 3` — pipeline bình thường, E2E thấp.
5. `./scripts/inject_fault_analysis.sh docker` — tắt analysis.
6. `python scripts/verify_decision_mqtt.py --count 2 --require-degraded` — alert `degraded=true`, sensor/decision vẫn chạy.
7. `docker compose start analysis_agent` — phục hồi.
8. (Tuỳ chọn) Mở `reports/metrics_run.json` / bảng trong báo cáo.
