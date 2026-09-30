# Alert runbooks

Ba alert theo dõi triệu chứng mà người dùng thấy. Mỗi điều kiện được đánh giá trên cửa sổ 5 phút, duy trì 5 phút và cần ít nhất 5 mẫu để tránh báo động từ một request lẻ. Các quy tắc nằm trong `config/alert_rules.yaml`; người trực là `student-2A202602489`, kênh Slack là `#k4-l3b-alerts`.

## Alert 1

- **Tên:** `HighLatencyP95` · **Severity:** warning · **Duration:** 5m.
- **Điều kiện:** P95 `response_sent.latency_ms` > 3000 ms trong cửa sổ 5 phút, tối thiểu 5 response.
- **Ảnh hưởng:** Người dùng chờ lâu hơn để nhận câu trả lời; request chậm hơn 3000 ms tiêu tốn error budget của SLO.
- **Metrics:** Mở panel Latency, xác nhận P95/P99 vượt đường 3000 ms và ghi lại khoảng UTC bắt đầu tăng. So sánh TTFT để phân biệt chậm trước token đầu với chậm trong toàn request.
- **Logs:** Lọc `response_sent` trong khoảng đó theo `latency_ms > 3000`; lấy `correlation_id`, `feature`, `model`, `ts` và độ trễ. Kiểm tra log có lỗi tải prompt hoặc lỗi mạng liên quan.
- **Traces:** Mở trace có cùng `correlation_id`, so sánh thời gian `retrieval`, `generation` và `lab-agent-run` để xác định bước chậm; kiểm tra prompt version trong metadata.
- **Mitigation:** Nếu do prompt vừa promote, rollback `production` về version ổn định; nếu do retrieval hoặc mạng ngoài, khôi phục dependency hoặc tạm giảm tải. Chạy lại một request và kiểm tra P95 giảm.
- **Owner / channel:** `student-2A202602489` · Slack `#k4-l3b-alerts`.

## Alert 2

- **Tên:** `HighRequestErrorRate` · **Severity:** critical · **Duration:** 5m.
- **Điều kiện:** `count(request_failed) / count(request_received) * 100 > 2%` trong cửa sổ 5 phút, tối thiểu 5 request.
- **Ảnh hưởng:** Người dùng không nhận được câu trả lời; mỗi request lỗi tiêu tốn error budget.
- **Metrics:** Mở panel Errors, xác nhận error rate vượt 2%, xem breakdown `error_type` và thời điểm bắt đầu.
- **Logs:** Lọc `request_failed` trong khoảng UTC đó, nhóm theo `error_type`, lấy một `correlation_id`; đối chiếu `request_received` cùng ID và mã lỗi nếu có.
- **Traces:** Mở trace cùng `correlation_id`, tìm observation lỗi hoặc kết thúc bất thường, kiểm tra metadata và prompt version.
- **Mitigation:** Khôi phục dependency gây lỗi; nếu lỗi xuất hiện sau thay đổi prompt/config, rollback thay đổi đó. Gửi request kiểm tra và xác nhận error rate trở về dưới 2%.
- **Owner / channel:** `student-2A202602489` · Slack `#k4-l3b-alerts`.

## Alert 3

- **Tên:** `LowRetrievalSuccess` · **Severity:** warning · **Duration:** 5m.
- **Điều kiện:** `count(tool_success == true) / count(tool_success != null) * 100 < 90%` trong cửa sổ 5 phút, tối thiểu 5 lần gọi tool. Mẫu gồm cả `response_sent` và `request_failed` có `tool_success`.
- **Ảnh hưởng:** Câu trả lời có thể thiếu tài liệu hoặc thất bại dù API còn trả HTTP 200.
- **Metrics:** Mở panel Errors, xác nhận retrieval success thấp hơn 90% và xem error rate có tăng theo không.
- **Logs:** Lọc các event có `tool_success=false`, xem `tool_name`, `error_type`, `ts` và chọn một `correlation_id`.
- **Traces:** Mở trace cùng `correlation_id`, kiểm tra observation `retrieval` và các bước tiếp theo để xác định lỗi tìm tài liệu hay lỗi phụ thuộc.
- **Mitigation:** Khôi phục nguồn tài liệu hoặc tool retrieval; nếu sự cố do cấu hình mới, rollback cấu hình. Chạy lại workload và xác nhận tỉ lệ thành công vượt 90%.
- **Owner / channel:** `student-2A202602489` · Slack `#k4-l3b-alerts`.
