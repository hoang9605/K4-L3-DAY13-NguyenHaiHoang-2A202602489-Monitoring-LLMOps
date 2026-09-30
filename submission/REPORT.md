# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Hải Hoàng
- **MSSV:** 2A202602489
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/hoang9605/K4-L3-DAY13-NguyenHaiHoang-2A202602489-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602489`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | [03](evidence/03-dashboard-validator.txt) |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | [08a](evidence/08a-trace-metadata.png), [08b](evidence/08b-generation.png) |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt promote và rollback | [10a](evidence/10a-production-v2.png), [10b](evidence/10b-production-v1.png) |
| Dashboard runtime | [11a](evidence/11a-dashboard-overview.png), [11b](evidence/11b-dashboard-overview.png), [11c](evidence/11c-dashboard-overview.png) |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; 21 log records; 20 thiếu trường bắt buộc; 20 thiếu metadata; 0 correlation ID duy nhất | Sau CP3: 100/100; 153 log records; 0 thiếu trường; 58 correlation ID duy nhất; 0 PII leak | Ảnh 02 là lần chạy CP1 đạt 100/100; đã kiểm tra lại sau challenge và recovery. |
| `validate_dashboard.py` | Hợp lệ 6/6 panel trong dashboard contract | Hợp lệ 6/6; dashboard runtime có dữ liệu trong ảnh 11a–11c | Validator chỉ kiểm tra cấu trúc YAML; ảnh 11 cho thấy biểu đồ chạy thực tế. |
| `pytest` | 22 passed (5.04s) | Trước commit cuối: 25 passed (2.95s) | Test `session_id` chứa email fail trước khi sửa processor và pass sau khi sửa; chạy lại toàn bộ trên commit cuối. |
| Số traces hợp lệ | Lần đầu chưa xác minh; sau khi khởi động lại đã thấy trace trên Langfuse (chưa đếm số lượng) | CP2: ít nhất 11 trace mới có đúng cây ba observation trong một khoảng kiểm tra 30 phút | Xác minh qua Langfuse Observations API v2: `lab-agent-run` là cha của `retrieval` và `generation`; trace gắn prompt v1/v2. |
| Số PII leak | Validator phát hiện 0/21 log records | CP1: validator phát hiện 0/27 log records mới | Request PII giả cho thấy `session_id` và `message_preview` được che trong log thực tế. |
| Latency P95 / TTFT P95 | CP3 baseline mới: 1110 ms / 50 ms (10 request; một request 1889 ms kéo P95 lên) | Sau khi tắt incident: 166 ms / 50 ms (10 request) | Trong incident: P95 khoảng 2654 ms / 50 ms (5 request). Các giá trị P95 tính theo phép nội suy percentile của dashboard. |
| Retrieval success rate | CP3 baseline: 100% | Sau recovery: 100% | Incident vẫn 100%; tool chậm nhưng không thất bại. |

**Ghi nhận CP0:** `python scripts/load_test.py` gửi 10 request; cả 10 trả HTTP 200 nhưng đều có `correlation_id=MISSING`. Mỗi request tạo log JSON `request_received` và `response_sent`; các preview chứa email, số điện thoại và thẻ mẫu đã được `summarize_text()` che thành `[REDACTED_...]`. Đây chưa phải bằng chứng bộ lọc PII ở bước ghi log đã hoạt động. Server báo `tracing_enabled=false` và `Failed to export spans batch code: 401, reason: Unauthorized`; cần kiểm tra cấu hình Langfuse trước khi lấy trace evidence ở CP2. Kết quả baseline ở trên được ghi từ output terminal trước khi sửa các TODO của CP1. Sau khi hoàn thiện logging, cần tạo log mới và chạy lại validator vì script đọc toàn bộ `data/logs.jsonl`.

**Sau khi khởi động lại ở CP0:** `/health` trả `tracing_enabled=true`; học viên xác nhận đã thấy trace trên web Langfuse của mình, nhưng chưa ghi số lượng/trace ID hoặc ảnh evidence. Workload vẫn trả HTTP 200. Langfuse báo HTTP 404 cho prompt `day13-chat` với label `production`, nên ứng dụng dùng prompt local fallback; cần tạo prompt version 1 và gắn label `production` trước khi lấy evidence về prompt version.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, nhận header `x-request-id` đúng dạng `req-<8-hex>` hoặc sinh ID mới, rồi bind vào structlog trước khi xử lý request. ID được trả trong body và header response. Log `request_received` và `response_sent` của request `req-e100a004` có cùng ID, khớp metadata của trace trong ảnh 08a.
- **Các metadata được ghi vào structured log:** Trước `request_received`, API bind `user_id_hash` (SHA-256 rút gọn), `session_id`, `feature`, `model` và `env`. Hai event cùng mang các trường này; `response_sent` ghi thêm latency, TTFT, token, cost và quality proxy.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` che các giá trị chuỗi cấp cao nhất và trong `payload`, rồi mới tới `JsonlFileProcessor`/JSON renderer. Test với dữ liệu giả cho thấy email trong `session_id` và email, điện thoại Việt Nam, CCCD, thẻ trong `message_preview` đều được thay bằng nhãn `[REDACTED_...]`.
- **Cách kiểm chứng kết quả:** `python -m pytest -q` đạt 25 passed ở CP1; `python scripts/validate_logs.py` đạt 100/100 trên 27 bản ghi, 12 correlation ID duy nhất, 0 PII leak. Xem [structured log](evidence/04-structured-log.png), [PII redaction](evidence/05-pii-redaction.png) và [log validator](evidence/02-log-validator.png). Chạy lại tests và validator trên commit cuối trước khi nộp.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** project `day13-k4-l3b-2A202602489` dùng key cá nhân trong `.env` (không commit). Sau `load_test.py`, Langfuse Observations API v2 cho thấy 11 trace ID mới trong khung 07:40–08:10 UTC, cả 11 có đủ ba observation theo đúng quan hệ cha-con. Ảnh danh sách: [06](evidence/06-trace-list.png).
- **Cấu trúc root/retrieval/generation observations:** trace `day13-agent-request` chứa `lab-agent-run` loại AGENT; hai child là `retrieval` loại RETRIEVER và `generation` loại GENERATION. Child generation ghi model `claude-sonnet-4-5`, input/output tokens, cost và liên kết đối tượng prompt Langfuse. Decorator tắt capture raw input/output để tránh đưa PII vào trace. Xem [waterfall 07](evidence/07-trace-waterfall.png) và [generation 08b](evidence/08b-generation.png).
- **Cách nối trace với log:** request `req-e100a004` trong log khớp metadata `correlation_id` của trace `17058d6b50b5c35d8ef85ba8a2515572`; root metadata ghi `prompt_source=langfuse`, `prompt_label=production`, `prompt_version=1`. Xem [log 04](evidence/04-structured-log.png) và [metadata 08a](evidence/08a-trace-metadata.png).
- **Prompt name:** `day13-chat`, loại Text, giữ đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}`. Xem [prompt versions 09](evidence/09-prompt-versions.png).
- **Version/label baseline:** v1 có `baseline` và, sau rollback, `production`.
- **Version/label candidate:** v2 thêm dòng hướng dẫn trả lời ngắn, có `candidate` và `latest` sau rollback. Fake LLM không đổi câu trả lời theo prompt; version và token đầu vào mới là tín hiệu cần đối chiếu.
- **Trace ID của mỗi version trên cùng input `Explain observability`:** baseline v1 `6427b3d7043ce515f0d0364ebeaa6eb4` (`req-b100a005`); candidate v2 `3ce0ff12f8254a3955f61691e637971c` (`req-c200a002`). Generation của cả hai liên kết `day13-chat` với version tương ứng.
- **Cách promote và rollback `production`:** dời `production` từ v1 sang v2; request `req-d200a003` tạo trace `77b284c3f019a791658a73292a8d3382` với `production`/v2. Sau đó dời `production` về v1 và restart API để xóa cache; request `req-e100a004` tạo trace `17058d6b50b5c35d8ef85ba8a2515572` với `production`/v1. Ảnh [sau promote 10a](evidence/10a-production-v2.png) và [sau rollback 10b](evidence/10b-production-v1.png).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `dashboard.py` đọc `data/logs.jsonl`, lọc 60 phút UTC và tự cập nhật mỗi 30 giây. Latency hiển thị P50/P95/P99 và TTFT P95; Traffic đếm request theo phút; Errors hiển thị error rate, error type và retrieval success trên mọi event có `tool_success`; Cost hiển thị tổng và diễn biến cộng dồn; Tokens hiển thị input/output và tổng cộng dồn; Quality hiển thị điểm trung bình. Mỗi panel lấy tên, đơn vị và ngưỡng từ `config/dashboard.yaml`, với đường ngưỡng nét đứt. Dashboard runtime có dữ liệu trong ba ảnh [11a](evidence/11a-dashboard-overview.png), [11b](evidence/11b-dashboard-overview.png), [11c](evidence/11c-dashboard-overview.png). Validator 6/6 chỉ kiểm tra YAML.
- **SLO và lý do chọn:** `config/slo.yaml` đặt mục tiêu 99,5% trong 28 ngày: request tốt phải có `response_sent` và `latency_ms <= 3000`. Baseline CP0/CP1 chủ yếu vài trăm mili giây, nên 3000 ms bắt được request chậm rõ rệt; các request 6–12 giây khi Langfuse DNS/timeout minh họa tail latency. Mẫu lab nhỏ không chứng minh được SLO dài hạn.
- **Cách tính error budget:** `100% - 99,5% = 0,5%`. Với 10.000 request trong 28 ngày, tối đa `10.000 × 0,005 = 50` request lỗi hoặc chậm trên 3000 ms. Với 1.000 request là 5. Request có `request_received` nhưng không có response tốt cũng tiêu tốn budget.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` cảnh báo P95 > 3000 ms trong 5 phút; `HighRequestErrorRate` báo động khi lỗi > 2% trong 5 phút; `LowRetrievalSuccess` cảnh báo khi tỉ lệ retrieval thành công < 90% trong 5 phút. Mỗi alert cần ít nhất 5 mẫu, có severity, owner `student-2A202602489`, Slack `#k4-l3b-alerts` và runbook trong `docs/alerts.md`. Mỗi runbook đi theo Metrics → Logs → Traces rồi nêu cách giảm tác động.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (cohort K4, feature `monitoring`). File gốc `config/challenge.json` được giữ ngoài Git.
- **Khoảng thời gian điều tra:** baseline 2026-09-30 08:52 UTC; incident 08:54:33–08:54:46 UTC (15:54:33–15:54:46 giờ Việt Nam); kiểm tra hồi phục 09:06 UTC.
- **Triệu chứng từ metrics:** median latency của 10 request baseline là 155 ms (9/10 trong khoảng 154–157 ms, một request 1889 ms). Năm request challenge có latency server 2652–2654 ms, median 2653 ms; cả năm vượt ngưỡng 2000 ms trong đề, nhưng chưa vượt ngưỡng SLO 3000 ms của dashboard. Sau khi tắt incident, 10 request mới có median 153 ms (152–176 ms). TTFT vẫn 50 ms, retrieval success vẫn 100%; đây là triệu chứng chậm, không phải lỗi tool. Xem [metric 12](evidence/12-incident-metric.png).
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-30T08:54:36.146611Z`, `correlation_id=req-cc24ea9c`, `session_id=k4-l3b-challenge-s02`, `feature=monitoring`, `latency_ms=2654`, `ttft_ms=50`, `tool_success=true`. Xem [log 13](evidence/13-incident-log.png).
- **Trace ID và span gây ảnh hưởng:** trace `f53de334e644e409a2c1c68e7b2ffbfc` có cùng `correlation_id=req-cc24ea9c`. `lab-agent-run` mất 2656 ms; child `retrieval` mất 2503 ms, còn `generation` mất 152 ms. Root metadata cho thấy `prompt_source=langfuse`, `prompt_label=production`, `prompt_version=1`. Xem [trace 14](evidence/14-incident-trace.png).
- **Root cause:** challenge kích hoạt tình huống `rag_slow`, khiến bước retrieval chờ khoảng 2,5 giây mỗi request. Độ trễ tăng nằm tại retriever, không có bằng chứng prompt v2 hoặc generation gây chậm. Workload chạy đồng thời còn làm latency phía client 8–13 giây vì các thao tác chờ đồng bộ xếp hàng; log và span đo thời gian từng request khoảng 2,65 giây.
- **Fix action:** tắt incident bằng `python scripts/inject_incident.py --disable`; chạy lại `load_test.py` và xác nhận median latency về 153 ms. Trong hệ thống thật, kiểm tra và khôi phục vector store/retrieval backend, thêm timeout hoặc fallback có kiểm soát.
- **Preventive measure:** dùng alert latency P95 và runbook Metrics → Logs → Traces; đo riêng latency của span retrieval, đặt timeout và theo dõi P95 theo feature `monitoring` để nhận biết tái diễn.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dùng cùng `correlation_id` cho response header, structured log và metadata trace; không capture raw input/output của observation. Nhờ vậy có thể tìm chính xác request chậm mà vẫn tránh đưa câu hỏi chứa PII lên Langfuse.
- **Một lỗi/blocker đã gặp:** Prompt `day13-chat` ban đầu trả 404 nên app dùng `local-fallback`; có lúc DNS tới Langfuse không ổn định khiến fetch/export timeout. Việc chỉ thấy HTTP 200 từ `/chat` không chứng minh prompt và trace đã hoạt động đúng.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra `prompt_source`, `prompt_fetch_error`, version trong root metadata; tạo Text prompt đủ ba biến và gắn nhãn `production`; kiểm tra kết nối và restart API để xóa cache. Sau đó trace hiện `prompt_source=langfuse`, generation gắn prompt version và có token/cost.
- **Cách hiểu luồng Metrics → Logs → Traces:** Dashboard cho biết lúc nào latency tăng (08:54 UTC); log lọc request `req-cc24ea9c` với `latency_ms=2654`; trace cùng ID khoanh vùng `retrieval=2503 ms` trong tổng 2656 ms. Mỗi bước thu hẹp phạm vi điều tra.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Label `production` là con trỏ có thể chuyển v1→v2→v1 mà không sửa code. Trace ghi version giúp phân biệt thay đổi prompt với sự cố retrieval; token/cost phát hiện chi phí tăng; SLO và error budget lượng hóa số request chậm/lỗi được phép.
- **Điều quan trọng nhất đã học:** Một biểu đồ latency cao chỉ là triệu chứng. Cần nối metric với một log có ID và một trace cùng ID trước khi kết luận root cause và chọn biện pháp khắc phục.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Fake LLM và retrieval mô phỏng không phản ánh đầy đủ chất lượng hoặc hành vi mạng của hệ thống thật. SLO 28 ngày mới là cấu hình đề xuất, chưa có đủ dữ liệu dài hạn để chứng minh đạt mục tiêu.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
