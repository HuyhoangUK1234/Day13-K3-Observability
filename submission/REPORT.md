# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard: Streamlit local — `streamlit run scripts/dashboard.py` → http://localhost:8501 | Nguồn dữ liệu: `data/logs.jsonl` | `error_rate_pct` = count(`request_failed`) / count(`request_received`) × 100

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel có trong dashboard contract.**
- Evidence dashboard: `submission/evidence/dashboard_screenshot.png` và `submission/evidence/validate_dashboard_passed.png`
- SLO đã chọn và lý do:

| Panel | Chỉ số | Ngưỡng SLO | Lý do |
|---|---|---|---|
| Latency | P95 latency | ≤ 3000 ms | Đảm bảo trải nghiệm người dùng không bị chậm |
| Traffic | rate/min | ≥ 1 req/min | Xác nhận hệ thống đang nhận traffic bình thường |
| Errors | error_rate_pct | ≤ 2% | Giới hạn tỷ lệ lỗi ở mức chấp nhận được |
| Cost | total cost | ≤ $2.50 | Kiểm soát chi phí trong giới hạn ngân sách |
| Tokens | total tokens | ≤ 50,000 | Tránh sử dụng token vượt mức |
| Quality | mean score | ≥ 0.75 | Đảm bảo chất lượng câu trả lời AI đạt tối thiểu |

- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
| | | | |
| Tạ Thị Nga | Xây dựng dashboard 6 panel (`scripts/dashboard.py`): Latency P50/P95/P99, Traffic, Error rate %, Cost, Tokens, Quality — có SLO threshold và badge xanh/đỏ. Chạy `validate_dashboard.py` đạt HỢP LỆ 6/6. | _12b80f1830429bfa8af530bffb57376fe5512749_ | Cách tính `error_rate_pct` từ JSONL log; thiết kế dashboard không cần DB; trực quan hoá SLO bằng Gauge/Donut chart |
| | | | |
| | | | |
