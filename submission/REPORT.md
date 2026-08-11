# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — 54 records, 0 record thiếu field bắt buộc, 0 record thiếu enrichment, 21 correlation ID. Ảnh: `submission/evidence/validate_logs.png`
- Tổng số traces: **15** trên Langfuse (10 baseline + 5 challenge), vượt mức tối thiểu 10
- Số PII leak còn lại: **0**
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

- Challenge ID: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, affected feature `refund`, `latency_threshold_ms` = 2000)
- Bằng chứng đầy đủ: `submission/evidence/challenge_investigation.txt` và `submission/evidence/challenge_logs.jsonl`

**Triệu chứng từ metrics**

| Chỉ số | Baseline (10 req, feature qa/summary) | Sau challenge (thêm 5 req feature refund) |
|---|---|---|
| P50 latency | 874 ms | 886 ms |
| P95 latency | 919 ms | **3483 ms** |
| error_breakdown | rỗng | rỗng |
| avg_cost_usd | 0.002 | 0.002 |
| quality_avg | 0.88 | 0.87 |

P95 vượt SLO 3000 ms và vượt `latency_threshold_ms` = 2000 ms, trong khi P50 gần như đứng yên. Chênh lệch P50/P95 cho thấy chỉ một nhóm request bị chậm chứ không phải toàn hệ thống. Error rate giữ 0% và cost/quality không đổi, nên loại được giả thuyết crash, cost spike và suy giảm chất lượng model.

**Trace ID liên quan** (Langfuse, lọc theo `session_id`)

| session_id | trace_id | latency |
|---|---|---|
| k3-challenge-s01 | `79308270e4cb6ff3759f279731ad1aa9` | 3.485 s |
| k3-challenge-s02 | `a0a176ba24e68a9374a602064e2f3567` | 3.389 s |
| k3-challenge-s03 | `ce38710631cda3daabbd95caf6fcd9d4` | 3.405 s |
| k3-challenge-s04 | `75649130653f02ad95999e8d96db1aeb` | 3.419 s |
| k3-challenge-s05 | `58d6046236d7273f760c9f6fa1706c40` | 3.368 s |

Cả 5 trace đều mang `prompt_name=day13-chat`, `prompt_version=local-v1`, `prompt_label=production` — prompt không đổi so với baseline, nên loại được giả thuyết "đổi prompt làm chậm". Span generation giữ nguyên ~0.85 s như baseline; phần dôi ra nằm trước bước gọi LLM, tức bước RAG retrieval.

**Log line / correlation ID liên quan**

| correlation_id | feature | latency_ms |
|---|---|---|
| req-21dbc811 | refund | 3483 |
| req-960cad93 | refund | 3418 |
| req-d54d1c9a | refund | 3404 |
| req-32689838 | refund | 3388 |
| req-e1ed76cd | refund | 3366 |

So với baseline 824–919 ms, mỗi request challenge cộng thêm khoảng 2500 ms. Con số này gần như bằng nhau ở cả 5 request, nghĩa là độ trễ cố định chứ không phải do tải cao — nếu do tải thì độ trễ sẽ phân tán. Log `service=control` xác nhận cửa sổ thời gian: `incident_enabled rag_slow` lúc `04:37:57.922484Z`, `incident_disabled` lúc `04:38:36.073972Z`, và cả 5 request rơi trọn trong khoảng đó.

**Root cause**

Cờ `rag_slow` được bật khiến hàm `retrieve()` trong [app/mock_rag.py:17-18](../app/mock_rag.py#L17-L18) chèn `time.sleep(2.5)` trước khi trả tài liệu. Độ trễ này nằm trên đường đi đồng bộ của mọi request nên cộng thẳng vào latency đầu-cuối. Trong hệ thống thật, đây tương ứng với vector store hoặc retrieval backend bị chậm — index xuống cấp, connection pool cạn, hoặc timeout của downstream đặt quá cao nên request cứ chờ thay vì fail nhanh.

**Fix action**

1. Tắt cờ sự cố ngay: `POST /incidents/rag_slow/disable` (đã chạy, xác nhận `{"rag_slow": false}`). Trong hệ thật tương đương rollback bản deploy hoặc tắt feature flag của retrieval path.
2. Đặt timeout cho `retrieve()` ở mức thấp hơn SLO (ví dụ 800 ms) và fallback sang câu trả lời không có tài liệu khi quá hạn, thay vì để request chờ vô hạn.
3. Chạy lại `load_test.py` và xác nhận P95 quay về dưới 1000 ms trước khi đóng incident.

**Preventive measure**

1. Thêm alert trên P95 latency với ngưỡng 3000 ms, cửa sổ 5 phút — hiện tại sự cố chỉ lộ ra khi có người mở dashboard.
2. Tách latency theo từng span (retrieval, generation) thành metric riêng, để lần sau đọc metrics là biết ngay tầng nào chậm mà chưa cần mở trace.
3. Thêm alert phân kỳ P50/P95: khi P95 tăng mà P50 đứng yên thì đó là dấu hiệu sự cố khu trú ở một subset request, cần điều tra theo `feature` chứ không phải toàn hệ thống.
4. Đưa `latency_ms` theo `feature` vào dashboard để phát hiện sớm khi một feature lệch khỏi phần còn lại.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
| | | | |
| Tạ Thị Nga | Xây dựng dashboard 6 panel (`scripts/dashboard.py`): Latency P50/P95/P99, Traffic, Error rate %, Cost, Tokens, Quality — có SLO threshold và badge xanh/đỏ. Chạy `validate_dashboard.py` đạt HỢP LỆ 6/6. | _12b80f1830429bfa8af530bffb57376fe5512749_ | Cách tính `error_rate_pct` từ JSONL log; thiết kế dashboard không cần DB; trực quan hoá SLO bằng Gauge/Donut chart |
| | | | |
| | | | |
