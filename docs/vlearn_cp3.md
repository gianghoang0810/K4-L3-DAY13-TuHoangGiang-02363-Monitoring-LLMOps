---
title: "VLearn"
source: "https://vlearn.dev/course/k4p1/reader?day=D17&part=codelab-90738bac9ab34d199b86f7ff1092358a-s07-doc"
exported: "2026-09-29T09:44:24.540Z"
---

# VLearn

## CP3 — Điều tra challenge

Starter **không** chứa file challenge. Tại CP3, Lab Coach gửi riêng file challenge của K4-L3A:

-   Lưu file tại `config/challenge.json`.
-   Xác nhận `challenge_id` là `day13-k4-l3a-monitoring-llmops-v1`.
-   File đã nằm trong `.gitignore`; **không force-add, commit, push hoặc chia sẻ** file này.

Chỉ chạy sau khi Lab Coach thông báo mở challenge K4-L3A:

```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
```

Nếu chưa nhận được file, `inject_incident.py` sẽ báo lỗi. Hãy tiếp tục practice bằng tham số `--scenario`; không chạy challenge chính thức.

Làm theo đúng thứ tự:

-   **1.** **Metrics:** ghi panel, giá trị bất thường và khoảng thời gian.
-   **2.** **Logs:** lọc các event trong khoảng đó; chọn một request và ghi `correlation_id`.
-   **3.** **Traces:** tìm trace có cùng `correlation_id`; so sánh duration/status của các span.
-   **4.** **Kết luận:** ghi root cause, fix action và preventive measure.

Report phải có challenge ID, một metric cụ thể, log line/correlation ID và trace ID. Ba bằng chứng phải cùng chỉ về một nguyên nhân.

Không sửa, tự tạo hoặc thay `config/challenge.json`. Dùng file của lớp khác sẽ bị 0 điểm phần incident.

**Chưa mở bài nào**

Chọn một bài ở dàn bài để mở tab mới. Có thể mở nhiều bài cùng lúc và chuyển qua lại mà không mất tiến trình.
