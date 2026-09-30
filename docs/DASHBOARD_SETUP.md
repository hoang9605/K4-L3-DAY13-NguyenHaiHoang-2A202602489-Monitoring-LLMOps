# Dựng và kiểm tra dashboard

[`../config/dashboard.yaml`](../config/dashboard.yaml) là contract chấm điểm, không phụ thuộc việc bạn dựng dashboard trong Langfuse hay một công cụ local. File này quy định đúng nguồn dữ liệu, phép tổng hợp, đơn vị và threshold cho sáu panel.

Trường `query` trong YAML là pseudocode mô tả phép tính, không phải câu lệnh để copy nguyên vào mọi công cụ. Bạn chuyển cùng logic đó sang cú pháp của công cụ đã chọn.

Lab không bắt buộc một công cụ dashboard cụ thể. Bạn có thể dùng Streamlit, notebook, Grafana, script local tạo biểu đồ hoặc công cụ tương đương. Điều quan trọng khi chấm là dashboard runtime có dữ liệu thật từ `data/logs.jsonl`, đủ sáu panel, đọc được time range/đơn vị/threshold và khớp logic trong `config/dashboard.yaml`.

## Mapping dữ liệu

| Panel | Event/field | Phép tổng hợp |
|---|---|---|
| Latency | `response_sent.latency_ms/ttft_ms` | latency P50/P95/P99 và TTFT P95 |
| Traffic | `request_received` | count, request/phút |
| Errors | `request_received`, `request_failed`, `error_type`, `tool_success` | error rate, breakdown và retrieval success |
| Cost | `response_sent.cost_usd` | tổng theo phút và toàn cửa sổ |
| Tokens | `response_sent.tokens_in/tokens_out` | tổng theo từng field |
| Quality | `response_sent.quality_score` | mean |

Giữ time range mặc định 60 phút, refresh 30 giây và hiển thị threshold/SLO line. Giá trị chính xác nằm trong `config/dashboard.yaml`; không tự đổi contract chỉ để ảnh dashboard đẹp hơn.

## Cách dựng

Dashboard đã có sẵn tại `dashboard.py`. Trên Windows, tạo môi trường riêng để
Streamlit không thay đổi dependencies của API:

```powershell
python -m venv .venv-dashboard
.\.venv-dashboard\Scripts\python.exe -m pip install -r dashboard-requirements.txt
.\.venv-dashboard\Scripts\python.exe -m streamlit run dashboard.py
```

Mở URL local mà Streamlit in ra (thường là `http://localhost:8501`). Dashboard
đọc trực tiếp `data/logs.jsonl`, giữ 60 phút UTC gần nhất và tự refresh mỗi 30
giây. Sáu panel lấy tên, đơn vị và threshold từ `config/dashboard.yaml`; đường
đỏ nét đứt là threshold. Nếu trang trống, chạy lại `python scripts/load_test.py`
trong môi trường API đang chạy. Không cần cài Streamlit vào venv của API.

Error rate lấy `request_failed / request_received`. Retrieval success lấy mọi
event có `tool_success`, gồm `response_sent` và `request_failed`, để không bỏ
sót lần gọi tool thành công.

1. Hoàn thiện logging/PII và chạy API.
2. Chạy `python scripts/load_test.py --concurrency 5` để tạo baseline.
3. Khởi động dashboard bằng lệnh Streamlit ở trên và xác nhận sáu panel có dữ liệu. Langfuse vẫn là nơi mở trace/prompt version để điều tra sâu.
4. Chạy validator:

```bash
python scripts/validate_dashboard.py
```

Validator kiểm tra cấu trúc contract; nó không thể chứng minh biểu đồ trong ảnh dùng đúng dữ liệu. Evidence runtime vẫn bắt buộc.

## Cách kiểm tra runtime

1. Lưu ảnh baseline và giá trị P95/error/cost hiện tại.
2. Bật một incident practice, ví dụ `python scripts/inject_incident.py --scenario <practice_scenario>`.
3. Chạy lại load test với cùng input và concurrency.
4. Xác nhận panel liên quan thay đổi theo đúng hướng theo loại practice scenario đã chọn.
5. Lọc log chậm, lấy correlation ID rồi mở trace có cùng ID.
6. Tắt incident bằng `python scripts/inject_incident.py --scenario <practice_scenario> --disable`.

Ảnh dashboard phải nhìn được tên panel, time range, đơn vị và threshold. Báo cáo phải dẫn lại trace ID hoặc log line dùng để giải thích thay đổi.
