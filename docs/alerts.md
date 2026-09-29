# Alerts và runbook

Contract: [alert_rules.yaml](../config/alert_rules.yaml). Owner: **TuHoangGiang-02363**.
Kênh dự kiến: Slack **#day13-02363-alerts**. Chưa nối webhook/alert engine, chưa gửi thông báo thật.
Biểu thức là đặc tả để chuyển sang query của công cụ giám sát. Đánh giá mỗi 30 giây;
điều kiện phải đúng liên tục trong duration, reset khi hết vi phạm.
Không chia cho 0; thiếu dữ liệu không đồng nghĩa hệ thống khỏe. Dưới 20 requests/window chưa đủ mẫu.

## Alert 1

- **Tên / severity:** high_request_latency / warning.
- **Điều kiện:** P95 latency trong 5 phút > 3000 ms, ít nhất 20 responses; duy trì **5 phút**.
- **SLI/SLO:** latency của fast_successful_requests (99.5% / 28 ngày).
- **Ảnh hưởng:** người dùng chờ lâu, có nguy cơ timeout.
- **Ba bước kiểm tra:** (1) dashboard latency/TTFT và time range; (2) log response_sent chậm, lấy correlation ID; (3) trace cùng ID, so sánh retrieval/generation và prompt version.
- **Mitigation:** giảm tải, cache/fallback đã kiểm chứng; rollback prompt nếu thay đổi prompt gây chậm. Chỉ tắt incident practice bằng --scenario ... --disable khi đang practice.
- **Phục hồi:** P95 <= 3000 ms trong 5 phút; kiểm tra lại errors/quality trước khi khôi phục tải.

## Alert 2

- **Tên / severity:** high_request_error_rate / critical.
- **Điều kiện:** request_failed / request_received * 100 > 2% trong 5 phút, ít nhất 20 requests; duy trì **5 phút**.
- **SLI/SLO:** request lỗi tiêu hao budget 0.5%.
- **Ảnh hưởng:** người dùng không nhận được câu trả lời.
- **Ba bước kiểm tra:** (1) errors panel và breakdown; (2) request_failed/error_type/correlation ID; (3) trace cùng ID để tìm span lỗi và kiểm tra dependency.
- **Mitigation:** rollback thay đổi gây lỗi; circuit breaker/fallback và retry có giới hạn, tránh retry storm. Phân biệt lỗi API với retrieval success giảm.
- **Phục hồi:** error rate <= 2% trong 5 phút và request mẫu thành công; kiểm tra good-event ratio 28 ngày trước khi kết luận đạt SLO.

## Alert 3

- **Tên / severity:** low_answer_quality / warning.
- **Điều kiện:** mean quality_score < 0.75 trong 10 phút, ít nhất 20 responses; duy trì **10 phút**.
- **SLI/SLO:** quality guardrail bổ sung cho latency/availability.
- **Ảnh hưởng:** câu trả lời ít hữu ích dù request thành công.
- **Ba bước kiểm tra:** (1) quality cùng traffic/retrieval success; (2) log quality thấp/correlation ID; (3) trace/prompt version và context retrieval; đánh giá thủ công input đã che PII.
- **Mitigation:** production về version tốt đã kiểm chứng; kiểm tra nguồn retrieval. Không đổi proxy chỉ để hết alert.
- **Phục hồi:** quality >= 0.75 trong 10 phút và đánh giá thủ công đạt; proxy không thay thế chất lượng thực tế.

## SLO và error budget

Good event: request thành công trong <= 3000 ms. Target 99.5% / 28 ngày.
Budget = tổng request * 0.005; ví dụ 10,000 requests cho phép 50 bad requests (lỗi hoặc chậm).
Remaining budget = allowed bad - observed bad; âm nghĩa đã vượt budget.
Không suy ra uptime theo phút từ SLO theo request. Alert 2% là tín hiệu ngắn hạn, không thay target 0.5% bad requests của 28 ngày.
