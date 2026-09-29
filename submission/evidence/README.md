# Evidence cá nhân — K4-L3A Day 13 Monitoring & LLMOps

Toàn bộ 14 minh chứng theo quy định của [docs/SUBMISSION.md](../../docs/SUBMISSION.md) đã được thu thập. Có thêm ảnh `10a` cho trạng thái trước rollback và file `15` cho lần xác minh sau khắc phục.

## Danh mục minh chứng chính thức (01 đến 14)

| STT | File evidence | Định dạng | Nội dung kiểm chứng |
|:---:|---|:---:|---|
| 01 | [01-pytest.txt](01-pytest.txt) | Output text | Kết quả `pytest -q`: 36 passed |
| 02 | [02-log-validator.txt](02-log-validator.txt) | Output text | Kết quả `validate_logs.py`: 100/100, 0 PII leak |
| 03 | [03-dashboard-validator.txt](03-dashboard-validator.txt) | Output text | Kết quả `validate_dashboard.py`: 6/6 panel hợp lệ |
| 04 | [04-structured-log.png](04-structured-log.png) | Ảnh terminal | Dòng log JSON chuẩn (correlation_id, latency, model, env) |
| 05 | [05-pii-redaction.png](05-pii-redaction.png) | Ảnh terminal | Log đầu ra đã che thông tin nhạy cảm [REDACTED_*] |
| 05a | [05a-pii-runtime.json](05a-pii-runtime.json) | JSON runtime | Bốn request `/chat`, đầy đủ marker email/phone/CCCD/card; input giả tại [script tái hiện](../../scripts/capture_pii_evidence.py) |
| 06 | [06-trace-list.png](06-trace-list.png) | Ảnh Langfuse | Danh sách ≥10 traces trong project cá nhân |
| 07 | [07-trace-waterfall.png](07-trace-waterfall.png) | Ảnh Langfuse | Cây span cha-con (lab-agent-run → retrieval + generation) |
| 08 | [08-trace-metadata.png](08-trace-metadata.png) | Ảnh Langfuse | Trace metadata (correlation_id, prompt version, tokens, cost) |
| 09 | [09-prompt-versions.png](09-prompt-versions.png) | Ảnh Langfuse | Quản lý prompt `day13-chat` có cả Version 1 và Version 2 |
| 10a | [10a-prompt-production-v2.png](10a-prompt-production-v2.png) | Ảnh Langfuse | Trace trước rollback có `prompt_version=2`, `prompt_label=production` |
| 10 | [10-prompt-rollback.png](10-prompt-rollback.png) | Ảnh Langfuse | Trạng thái cuối: nhãn `production` đã rollback về v1 |
| 11 | [11-dashboard-overview.png](11-dashboard-overview.png) | Ảnh Dashboard | Dashboard CP2 có 6 panel và 64 requests |
| 12 | [12-incident-metric.png](12-incident-metric.png) | Ảnh Dashboard | Metric độ trễ P95 tăng vọt khi xảy ra sự cố challenge |
| 13 | [13-incident-log.png](13-incident-log.png) | Ảnh terminal | Dòng log của request bị chậm `req-6cd2ab26` (latency 4213 ms) |
| 14 | [14-incident-trace.png](14-incident-trace.png) | Ảnh Langfuse | Trace `e596d0901341c7a7f7767db8eb6d943d` thấy span retrieval 2.5s |
| 14a | [14a-incident-correlation.png](14a-incident-correlation.png) | Ảnh Langfuse | Cùng trace, hiện `req-6cd2ab26`, timestamp root, project và cây span |
| 15 | [15-post-fix-verification.json](15-post-fix-verification.json) | JSON runtime | Incident đã tắt; 5 request challenge mới đều dưới 400 ms theo server log |

## Dữ liệu bổ trợ & API Snapshot
- [05-pii-redaction.json](05-pii-redaction.json): Log runtime trích xuất đã redact PII.
- [cp2-cloud-observations.json](cp2-cloud-observations.json): 20 traces / 60 observations đọc từ Langfuse Cloud API.
- [prompt-workflow.json](prompt-workflow.json): Quy trình kiểm chứng prompt v1/v2, promote và rollback.
- [dashboard-metrics.json](dashboard-metrics.json), [11-dashboard-overview.html](11-dashboard-overview.html): CP2, cửa sổ 07:25:28–08:25:28 UTC; ảnh `11` là 07:32:07–08:32:07 UTC. Cùng 64 requests và số liệu tổng hợp, khác thời điểm snapshot.
- [12-incident-dashboard-metrics.json](12-incident-dashboard-metrics.json), [12-incident-dashboard.html](12-incident-dashboard.html): CP3, cửa sổ 08:50:17–09:50:17 UTC; ảnh `12` là 08:55:29–09:55:29 UTC. Cùng 5 requests incident; TTFT P95 51 ms.
- [practice-investigation.json](practice-investigation.json): Dữ liệu kịch bản luyện tập trước đó.
- Các file baseline CP1: [cp1-health.txt](cp1-health.txt), [cp1-workload.txt](cp1-workload.txt), [cp1-pytest.txt](cp1-pytest.txt), [cp1-log-validator.txt](cp1-log-validator.txt), [cp1-dashboard-validator.txt](cp1-dashboard-validator.txt).

Tất cả các file đều được trích xuất từ môi trường chạy thật, không chứa bí mật/API keys, không chứa PII nguyên văn và thuộc quyền sở hữu của học viên Từ Hoàng Giang (MSSV: 2A202602363).
