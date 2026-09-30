# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Hải Hoàng
- **MSSV:** 2A202602489
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/hoang9605/K4-L3-DAY13-NguyenHaiHoang-2A202602489-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602489`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; 21 log records; 20 thiếu trường bắt buộc; 20 thiếu metadata; 0 correlation ID duy nhất | CP1: 100/100; 27 log records; 0 thiếu trường; 12 correlation ID duy nhất | Đã kiểm tra lại sau request PII giả; chạy lại validator trên commit cuối. |
| `validate_dashboard.py` | Hợp lệ 6/6 panel trong dashboard contract | | Chưa xác nhận dashboard runtime có dữ liệu. |
| `pytest` | 22 passed (5.04s) | CP1: 25 passed (2.14s) | Test `session_id` chứa email fail trước khi sửa processor và pass sau khi sửa; chạy lại toàn bộ trên commit cuối. |
| Số traces hợp lệ | Lần đầu chưa xác minh; sau khi khởi động lại đã thấy trace trên Langfuse (chưa đếm số lượng) | | Lần đầu startup báo `tracing_enabled=false` và export HTTP 401; lần chạy lại `/health` báo `tracing_enabled=true`. Chưa xác minh cấu trúc span. |
| Số PII leak | Validator phát hiện 0/21 log records | CP1: validator phát hiện 0/27 log records mới | Request PII giả cho thấy `session_id` và `message_preview` được che trong log thực tế. |
| Latency P95 / TTFT P95 | | | |
| Retrieval success rate | | | |

**Ghi nhận CP0:** `python scripts/load_test.py` gửi 10 request; cả 10 trả HTTP 200 nhưng đều có `correlation_id=MISSING`. Mỗi request tạo log JSON `request_received` và `response_sent`; các preview chứa email, số điện thoại và thẻ mẫu đã được `summarize_text()` che thành `[REDACTED_...]`. Đây chưa phải bằng chứng bộ lọc PII ở bước ghi log đã hoạt động. Server báo `tracing_enabled=false` và `Failed to export spans batch code: 401, reason: Unauthorized`; cần kiểm tra cấu hình Langfuse trước khi lấy trace evidence ở CP2. Kết quả baseline ở trên được ghi từ output terminal trước khi sửa các TODO của CP1. Sau khi hoàn thiện logging, cần tạo log mới và chạy lại validator vì script đọc toàn bộ `data/logs.jsonl`.

**Sau khi khởi động lại ở CP0:** `/health` trả `tracing_enabled=true`; học viên xác nhận đã thấy trace trên web Langfuse của mình, nhưng chưa ghi số lượng/trace ID hoặc ảnh evidence. Workload vẫn trả HTTP 200. Langfuse báo HTTP 404 cho prompt `day13-chat` với label `production`, nên ứng dụng dùng prompt local fallback; cần tạo prompt version 1 và gắn label `production` trước khi lấy evidence về prompt version.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, nhận header `x-request-id` đúng dạng `req-<8-hex>` hoặc sinh ID mới, rồi bind vào structlog trước khi xử lý request. ID được trả trong body và header response. Log `request_received` và `response_sent` của request `req-04a1b2c3` có cùng ID.
- **Các metadata được ghi vào structured log:** Trước `request_received`, API bind `user_id_hash` (SHA-256 rút gọn), `session_id`, `feature`, `model` và `env`. Hai event cùng mang các trường này; `response_sent` ghi thêm latency, TTFT, token, cost và quality proxy.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` che các giá trị chuỗi cấp cao nhất và trong `payload`, rồi mới tới `JsonlFileProcessor`/JSON renderer. Test với dữ liệu giả cho thấy email trong `session_id` và email, điện thoại Việt Nam, CCCD, thẻ trong `message_preview` đều được thay bằng nhãn `[REDACTED_...]`.
- **Cách kiểm chứng kết quả:** `python -m pytest -q` đạt 25 passed ở CP1; `python scripts/validate_logs.py` đạt 100/100 trên 27 bản ghi, 12 correlation ID duy nhất, 0 PII leak. Xem [structured log](evidence/04-structured-log.png), [PII redaction](evidence/05-pii-redaction.png) và [log validator](evidence/02-log-validator.png). Chạy lại tests và validator trên commit cuối trước khi nộp.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
