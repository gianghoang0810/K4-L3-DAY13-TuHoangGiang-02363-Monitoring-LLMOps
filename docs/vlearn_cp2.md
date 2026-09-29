---
title: "VLearn"
source: "https://vlearn.dev/course/k4p1/reader?day=D17&part=codelab-90738bac9ab34d199b86f7ff1092358a-s06-doc"
exported: "2026-09-29T08:58:49.529Z"
---

# VLearn

## CP2 — Traces, prompt, dashboard và alert

### 6.1. Trace trên Langfuse

Starter đã có root observation cho `LabAgent.run` và dùng Langfuse Python SDK v4. Bạn cần tạo thêm:

-   observation `retriever` hoặc `span` cho bước retrieval;
-   observation `generation` cho fake LLM, có model, prompt, usage và cost.

Mục tiêu là tạo ít nhất 10 traces có:

-   child observations nằm đúng quan hệ cha–con;
-   `user_id` đã hash, `session_id`, feature, model, env và `correlation_id`;
-   không capture raw input/output chứa PII;
-   waterfall đủ rõ để biết retrieval hay LLM là bước chậm.

### 6.2. Prompt versioning

Làm theo `docs/PROMPT_VERSIONING.md`:

-   **1.** Tạo text prompt `day13-chat` version 1; gắn labels `baseline` và `production`.
-   **2.** Tạo version 2 với một thay đổi nhỏ; gắn label `candidate`.
-   **3.** Chạy cùng input với hai label.
-   **4.** Kiểm tra trace có đúng prompt name, label và version.
-   **5.** Chuyển `production` sang v2, sau đó rollback về v1 và lưu evidence.

Nếu metadata hiện `local-v1`, xem `prompt_source`: `local` nghĩa là chưa bật Langfuse; `local-fallback` nghĩa là fetch prompt bị lỗi. Kiểm tra key, `LANGFUSE_BASE_URL`, prompt name/label rồi khởi động lại API.

### 6.3. Dashboard, SLO và alerts

Dựng đúng 6 panel từ `data/logs.jsonl` theo `config/dashboard.yaml`:

-   **1.** latency P50/P95/P99 và TTFT;
-   **2.** traffic;
-   **3.** error rate, breakdown và retrieval success;
-   **4.** cost;
-   **5.** input/output tokens;
-   **6.** quality proxy.

Mỗi panel cần tên, đơn vị, time range 60 phút và threshold/SLO line. Công cụ có thể là Streamlit, notebook, Grafana hoặc công cụ tương đương.

Tiếp theo:

-   giải thích hoặc điều chỉnh SLO trong `config/slo.yaml` và tính error budget;
-   hoàn thiện ba alert symptom-based trong `config/alert_rules.yaml`;
-   mỗi alert phải có condition, duration, severity, owner, Slack channel và runbook;
-   hoàn thiện `docs/alerts.md`.

Kiểm tra contract:

```bash
python scripts/validate_dashboard.py
```

Validator chỉ kiểm tra cấu trúc YAML. Ảnh dashboard runtime có dữ liệu vẫn là evidence bắt buộc.

**Chưa mở bài nào**

Chọn một bài ở dàn bài để mở tab mới. Có thể mở nhiều bài cùng lúc và chuyển qua lại mà không mất tiến trình.
