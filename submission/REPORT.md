# Day 13 Observability Report

## 1. Thông tin nhóm

- Tên nhóm: B2
- Đường dẫn repository: [github.com/VinUni-AI20k/Day13-K4-Observability.git](https://github.com/VinUni-AI20k/Day13-K4-Observability.git)
- Commit SHA cuối:
- Thành viên và vai trò:

| MSSV        | Họ và tên           | Vai trò                                                |
| ----------- | ---------------------- | ------------------------------------------------------- |
| 2A202601225 | Nguyễn Duy Hải Bằng | Thành viên A — API & Middleware (CP1 Correlation ID) |
| 2A202601267 | Trần Thị Thanh Tâm  | Thành viên B — Security Engineer (CP1 PII Scrubbing) |
| 2A202601125 | Tạ Thị Nga           | Thành viên C — Dashboard & SLO (CP2)                 |
| 2A202601105 | Huỳnh Hoàng Việt    | CP2 owner — Tracing & Prompt Versioning                |
| 2A202601433 | Nguyễn Văn Tiến     | CP3 owner — Incident Investigation                     |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — 54 bản ghi, 0 bản ghi thiếu field bắt buộc, 0 record thiếu enrichment, 21 correlation ID. Ảnh: `submission/evidence/validate_logs.png`
- Tổng số traces: **15** trên Langfuse (10 baseline + 5 challenge), vượt mức tối thiểu 10
- Số PII leak còn lại: **0**
- Link/đường dẫn dashboard: Streamlit local — `streamlit run scripts/dashboard.py` → http://localhost:8501 | Nguồn dữ liệu: `data/logs.jsonl` | `error_rate_pct` = count(`request_failed`) / count(`request_received`) × 100

## 3. Logging và Tracing

- **Bằng chứng correlation ID:** `data/logs.jsonl` và `submission/evidence/validate_logs_cp2.txt`; validator ghi nhận 11 correlation ID duy nhất trong lần chạy CP2 (các lần chạy khác xem mục 2). Ví dụ cụ thể là `submission/evidence/correlation_id_logs.jsonl`: mọi dòng log của cùng một request đều mang chung một ID dạng `req-<8-hex>`, từ middleware cho tới `response_sent`.
- **Bằng chứng che PII:**

  - `submission/evidence/validate_logs_pii_cp1.txt` — `validate_logs.py` báo `Potential PII leaks detected: 0` và `+ [PASSED] PII scrubbing` trên 31 record với 10 correlation ID duy nhất (điểm ước tính 100/100).
  - `submission/evidence/pii_redacted_logs.jsonl` — ba dòng log tại đúng vị trí PII lẽ ra xuất hiện, hiển thị `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]` và `[REDACTED_CREDIT_CARD]`. Số lượng khớp chính xác ba mẫu PII cài sẵn trong `data/sample_queries.jsonl` (dòng 1, 5, 9), nghĩa là không có gì lọt ra và cũng không che thừa.
  - `submission/evidence/pii_tests_cp1.txt` — 12/12 test trong `tests/test_pii.py` pass, gồm `test_scrub_event_runs_before_the_file_writer` xác nhận processor che PII thực sự được đăng ký trong chain của structlog và chạy trước bộ ghi file.
  - *Lưu ý khi diễn giải:* riêng dòng `PASSED` của validator không chứng minh được bộ che hoạt động. Starter code đã bọc sẵn `summarize_text()` ở hai field preview tại [app/main.py:53](../app/main.py#L53) và [app/main.py:70](../app/main.py#L70), nên hai đường đó vốn đã sạch từ trước khi có thay đổi nào. Đóng góp thật nằm ở những field không ai bọc: `str(exc)` tại [app/main.py:88](../app/main.py#L88) và traceback do `format_exc_info` sinh ra. Bằng chứng cho phần này là unit test, không phải dòng validator.
- **Bằng chứng trace waterfall:** lấy một trace trong `submission/evidence/langfuse_10_traces_cp2.txt`, ví dụ `d8ef17c116d45a84319d214182fb733b` (project `cmso2mhmv03v0ad0cwpep8la0`). Trace tương đương trong project CP3 là `79308270e4cb6ff3759f279731ad1aa9` (project `cmso2bf6j03clad0jxpunmc7i`) — xem ghi chú cuối mục 4.
- **Prompt metadata gắn vào trace:** app gắn metadata prompt vào trace và generation qua `update_current_trace` và `update_current_generation` trong [app/agent.py](../app/agent.py). Bằng chứng kỹ thuật: `submission/evidence/prompt_tracing_tests_cp2.txt`.
- **Span đáng chú ý — bước RAG retrieval:** trace `79308270e4cb6ff3759f279731ad1aa9` tổng cộng 3.485 s. Span generation (gọi LLM) chỉ chiếm khoảng 0.85 s, đúng bằng mức của các trace baseline. Toàn bộ phần dôi ra khoảng 2.5 s nằm ở đoạn trước khi gọi LLM, tức lời gọi `retrieve()` tại [app/agent.py:32](../app/agent.py#L32).

  Span này đáng chú ý vì ba lý do. **Thứ nhất**, nó nằm trên đường đi đồng bộ: mọi request đều phải chờ nó xong mới đi tiếp, nên thời gian của nó cộng thẳng vào latency người dùng cảm nhận, không có cách nào giấu đi. **Thứ hai**, nó gọi ra ngoài hệ thống — trong thực tế là vector store — tức là điểm mà độ trễ không do code của mình quyết định; đây thường là nghi phạm đầu tiên khi latency tăng mà CPU và error rate không đổi. **Thứ ba**, nếu chỉ nhìn log thì `response_sent` chỉ cho một con số `latency_ms` gộp; phải mở trace mới tách được 3.4 s đó thành 0.85 s gọi model và 2.5 s chờ retrieval. Đây chính là điều trace làm được mà log không làm được.

## 4. Quản lý phiên bản prompt

- Tên prompt: `day13-chat`.
- Version baseline: version 1, gắn label `baseline` và `production`.
- Version candidate: version 2, gắn label `candidate`.
- Trace ID của từng version: baseline `ba47689dd827372ce961c566258774cf`; candidate `eb06a44a39378ef187d1b4fb13722c02`. Bằng chứng: `submission/evidence/langfuse_trace_ids_cp2.txt`.
- Bằng chứng đổi label và rollback: `submission/evidence/prompt_label_rollback_cp2.txt` cho thấy label `production` được chuyển sang version 2 rồi rollback về version 1. Test local xác nhận app ghi `prompt_name`, `prompt_label` và `prompt_version` vào metadata của trace.

## 5. Dashboard, SLO và Alert

- Kết quả `validate_dashboard.py`: `HOP LE: 6/6 panel co trong dashboard contract.` Bằng chứng: `submission/evidence/validate_dashboard_cp2.txt`.
- Bằng chứng dashboard: ảnh chụp màn hình lưu tại `submission/evidence/Dashboard1.png`, `submission/evidence/Dashboard2.png`, `submission/evidence/Dashboard3.png`, `submission/evidence/validate_dashboard.png` và `submission/evidence/validate_logs.png`. Bằng chứng test dashboard: `submission/evidence/dashboard_tests_cp2.txt`.
- SLO đã chọn và lý do:

| Panel   | Chỉ số       | Ngưỡng SLO | Lý do                                                                                      |
| ------- | -------------- | ------------ | ------------------------------------------------------------------------------------------- |
| Latency | P95 latency    | <= 3000 ms   | Giữ thời gian phản hồi ở mức dùng được và lộ sớm đường RAG/model bị chậm. |
| Traffic | rate/min       | >= 1 req/min | Xác nhận service vẫn đang nhận traffic bình thường.                                 |
| Errors  | error_rate_pct | <= 2%        | Giữ tỉ lệ request lỗi trong ngưỡng chấp nhận được.                               |
| Cost    | total cost     | <= 2.50 USD  | Giữ chi phí của buổi lab trong ngân sách.                                             |
| Tokens  | total tokens   | <= 50,000    | Phát hiện thay đổi prompt hoặc retrieval làm tiêu quá nhiều token.                 |
| Quality | mean score     | >= 0.75      | Giữ chỉ số đại diện cho chất lượng câu trả lời trên mức tối thiểu.          |

- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, affected feature `refund`, `latency_threshold_ms` = 2000)
- Bằng chứng đầy đủ: `submission/evidence/challenge_investigation.txt` và `submission/evidence/challenge_logs.jsonl`

**Triệu chứng từ metrics**

| Chỉ số        | Baseline (10 req, feature qa/summary) | Sau challenge (thêm 5 req feature refund) |
| --------------- | ------------------------------------- | ------------------------------------------ |
| P50 latency     | 874 ms                                | 886 ms                                     |
| P95 latency     | 919 ms                                | **3483 ms**                          |
| error_breakdown | rỗng                                 | rỗng                                      |
| avg_cost_usd    | 0.002                                 | 0.002                                      |
| quality_avg     | 0.88                                  | 0.87                                       |

P95 vượt SLO 3000 ms và vượt `latency_threshold_ms` = 2000 ms, trong khi P50 gần như đứng yên. Chênh lệch P50/P95 cho thấy chỉ một nhóm request bị chậm chứ không phải toàn hệ thống. Error rate giữ 0% và cost/quality không đổi, nên loại được giả thuyết crash, cost spike và suy giảm chất lượng model.

**Trace ID liên quan** (Langfuse, lọc theo `session_id`)

| session_id       | trace_id                             | latency |
| ---------------- | ------------------------------------ | ------- |
| k3-challenge-s01 | `79308270e4cb6ff3759f279731ad1aa9` | 3.485 s |
| k3-challenge-s02 | `a0a176ba24e68a9374a602064e2f3567` | 3.389 s |
| k3-challenge-s03 | `ce38710631cda3daabbd95caf6fcd9d4` | 3.405 s |
| k3-challenge-s04 | `75649130653f02ad95999e8d96db1aeb` | 3.419 s |
| k3-challenge-s05 | `58d6046236d7273f760c9f6fa1706c40` | 3.368 s |

Cả 5 trace đều mang `prompt_name=day13-chat`, `prompt_version=local-v1`, `prompt_label=production` — prompt không đổi so với baseline, nên loại được giả thuyết "đổi prompt làm chậm". Span generation giữ nguyên ~0.85 s như baseline; phần dôi ra nằm trước bước gọi LLM, tức bước RAG retrieval.

**Log line / correlation ID liên quan**

| correlation_id | feature | latency_ms |
| -------------- | ------- | ---------- |
| req-21dbc811   | refund  | 3483       |
| req-960cad93   | refund  | 3418       |
| req-d54d1c9a   | refund  | 3404       |
| req-32689838   | refund  | 3388       |
| req-e1ed76cd   | refund  | 3366       |

So với baseline 824–919 ms, mỗi request challenge cộng thêm khoảng 2500 ms. Con số này gần như bằng nhau ở cả 5 request, nghĩa là độ trễ cố định chứ không phải do tải cao — nếu do tải thì độ trễ sẽ phân tán. Log `service=control` xác nhận cửa sổ thời gian: `incident_enabled rag_slow` lúc `04:37:57.922484Z`, `incident_disabled` lúc `04:38:36.073972Z`, và cả 5 request rơi trọn trong khoảng đó.

**Nguyên nhân gốc**

Cờ `rag_slow` được bật khiến hàm `retrieve()` trong [app/mock_rag.py:17-18](../app/mock_rag.py#L17-L18) chèn `time.sleep(2.5)` trước khi trả tài liệu. Độ trễ này nằm trên đường đi đồng bộ của mọi request nên cộng thẳng vào latency đầu-cuối. Trong hệ thống thật, đây tương ứng với vector store hoặc retrieval backend bị chậm — index xuống cấp, connection pool cạn, hoặc timeout của downstream đặt quá cao nên request cứ chờ thay vì fail nhanh.

**Hành động khắc phục**

1. Tắt cờ sự cố ngay: `POST /incidents/rag_slow/disable` (đã chạy, xác nhận `{"rag_slow": false}`). Trong hệ thật tương đương rollback bản deploy hoặc tắt feature flag của retrieval path.
2. Đặt timeout cho `retrieve()` ở mức thấp hơn SLO (ví dụ 800 ms) và fallback sang câu trả lời không có tài liệu khi quá hạn, thay vì để request chờ vô hạn.
3. Chạy lại `load_test.py` và xác nhận P95 quay về dưới 1000 ms trước khi đóng incident.

**Biện pháp phòng ngừa**

1. Thêm alert trên P95 latency với ngưỡng 3000 ms, cửa sổ 5 phút — hiện tại sự cố chỉ lộ ra khi có người mở dashboard.
2. Tách latency theo từng span (retrieval, generation) thành metric riêng, để lần sau đọc metrics là biết ngay tầng nào chậm mà chưa cần mở trace.
3. Thêm alert phân kỳ P50/P95: khi P95 tăng mà P50 đứng yên thì đó là dấu hiệu sự cố khu trú ở một subset request, cần điều tra theo `feature` chứ không phải toàn hệ thống.
4. Đưa `latency_ms` theo `feature` vào dashboard để phát hiện sớm khi một feature lệch khỏi phần còn lại.

## 7. Đóng góp cá nhân

Commit SHA dưới đây lấy trực tiếp từ `git log` nên đối chiếu được với repository. Vai trò được xác định theo file mà từng thành viên thực sự thay đổi, không phải theo phân công trên giấy.

### 7.1. Bảng tóm tắt commit

Vai trò chi tiết xem mục 1. Bảng này ánh xạ từng thành viên sang commit tương ứng để đối chiếu với `git log`.

| MSSV        | Thành viên           | Commit chính            |
| ----------- | ---------------------- | ------------------------ |
| 2A202601225 | Nguyễn Duy Hải Bằng | `9fc91ee`              |
| 2A202601267 | Trần Thị Thanh Tâm  | `d80f481`, `4a9e45e` |
| 2A202601125 | Tạ Thị Nga           | `12b80f1`, `bd55514` |
| 2A202601105 | Huỳnh Hoàng Việt    | `9c7e299`, `0fb82a1` |
| 2A202601433 | Nguyễn Văn Tiến     | `bf05cfb`              |

### 7.2. Nguyễn Duy Hải Bằng — API & Middleware (CP1 Correlation ID)

**Commit:** `9fc91eebd0ebb24f94da3481a8106306c47297bb`

**Nhiệm vụ đã làm**

- Sinh correlation ID theo format `req-<8-hex>` trong [app/middleware.py](../app/middleware.py); nhận lại `x-request-id` từ upstream khi giá trị khớp regex an toàn, tránh log injection.
- `bind_contextvars` correlation ID ngay tại middleware, nhờ đó mọi log phát sinh trong request đều tự mang ID mà không cần truyền tay qua từng hàm.
- Enrich log endpoint `/chat` trong [app/main.py](../app/main.py) với `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- Trả `x-request-id` và `x-response-time-ms` về response header để client đối chiếu được với log server.
- Thêm exception handler ghi `http_request_failed` kèm `error_type` và latency.
- `clear_contextvars` sau mỗi request để context không rò từ request này sang request khác.
- Viết `tests/test_middleware_correlation.py`.

**Bằng chứng:** `submission/evidence/correlation_id_logs.jsonl`, `submission/evidence/validate_logs_after_cp1_middleware.txt`

### 7.3. Trần Thị Thanh Tâm — Security Engineer (CP1 PII Scrubbing)

**Commit:** `d80f481e8014397bd2b25c2cfa3a9039e43a8904`; `4a9e45e412d86f1579290cad3b43161009ea849e`

**Nhiệm vụ đã làm**

- Mở rộng `PII_PATTERNS` trong [app/pii.py](../app/pii.py) từ 4 lên 8 pattern: bổ sung hộ chiếu VN, CMND 9 số, ngày sinh, địa chỉ tiếng Việt. Ghi chú trong code phụ thuộc thứ tự `email` phải chạy trước các pattern số.
- Đăng ký `scrub_event` vào processor chain của structlog trong [app/logging_config.py](../app/logging_config.py). Hàm này có sẵn trong starter code nhưng bị comment out nên chưa bao giờ chạy.
- Đặt `scrub_event` **sau** `format_exc_info` và **trước** `JsonlFileProcessor`, để traceback exception cũng được che trước khi ghi xuống đĩa.
- Viết lại `scrub_event` thành quét đệ quy toàn bộ `event_dict` — chuỗi, dict lồng nhau, list, tuple — thay vì chỉ `payload` một tầng như bản cũ.
- Nâng `tests/test_pii.py` từ 2 lên 12 test, gồm test khoá thứ tự pattern, test chặn false positive trên field kỹ thuật, và test xác nhận processor thực sự được đăng ký trong chain.

**Bằng chứng:** `submission/evidence/pii_redacted_logs.jsonl`, `submission/evidence/validate_logs_pii_cp1.txt`, `submission/evidence/pii_tests_cp1.txt`

**Điều đã học:** Thứ tự processor quyết định phạm vi bảo vệ. Scrub phải chạy **sau** `format_exc_info` vì trước đó traceback vẫn là object chứ chưa phải chuỗi để regex quét được, và phải **trước** bộ ghi file vì dữ liệu đã xuống đĩa là không thu hồi được. Nguyên tắc rút ra: vùng phủ của bộ che phải rộng bằng vùng phủ của bộ dò — `validate_logs.py` quét cả record sau `json.dumps`, nên che chọn lọc vài field là tự chừa cửa cho lọt. Ngoài ra, dòng `PASSED` của validator không tự chứng minh phần scrub hoạt động, vì starter code đã bọc `summarize_text()` sẵn ở hai đường preview; bằng chứng thật nằm ở unit test.

### 7.4. Tạ Thị Nga — Dashboard & SLO (CP2)

**Commit:** `12b80f1830429bfa8af530bffb57376fe5512749`; `bd55514934c93d3d54939917e549c57d9bb43386`

**Nhiệm vụ đã làm**

- Xây dựng dashboard 6 panel trong `scripts/dashboard.py`: Latency P50/P95/P99, Traffic, Error rate %, Cost, Tokens, Quality.
- Gắn SLO threshold cho từng panel kèm badge xanh/đỏ thể hiện trạng thái đạt hay vi phạm.
- Chạy `validate_dashboard.py` đạt HỢP LỆ 6/6 panel theo dashboard contract.
- Thu thập và đặt tên lại ảnh bằng chứng dashboard.

**Bằng chứng:** `submission/evidence/Dashboard1.png`, `Dashboard2.png`, `Dashboard3.png`, `validate_dashboard.png`, `validate_logs.png`, `dashboard_tests_cp2.txt`

**Điều đã học:** Cách tính `error_rate_pct` từ log JSONL; thiết kế dashboard không cần database; trực quan hoá SLO bằng Gauge/Donut chart.

### 7.5. Huỳnh Hoàng Việt — Tracing & Prompt Versioning (CP2)

**Commit:** `9c7e299dbfca967939bb60590f820dd239adfcaf; 0fb82a16b7d8db28dda9eaca064317f01d8480cd`

**Nhiệm vụ đã làm**

- Tạo trace Langfuse kèm metadata cho tối thiểu 10 request.
- Dựng prompt `day13-chat` version 1 và 2, gắn label `baseline`, `production`, `candidate`.
- Thực hiện đổi label `production` sang v2 rồi rollback về v1, lưu bằng chứng trước và sau.
- Hoàn thiện `config/alert_rules.yaml`, `config/slo.yaml` và runbook trong `docs/alerts.md`.

**Bằng chứng:** `submission/evidence/langfuse_10_traces_cp2.txt`, `langfuse_trace_ids_cp2.txt`, `prompt_versions_cp2.txt`, `prompt_label_requests_cp2.txt`, `prompt_label_rollback_cp2.txt`, `prompt_tracing_tests_cp2.txt`, `validate_dashboard_cp2.txt`, `validate_logs_cp2.txt`

**Điều đã học:** Cách nối luồng Metrics → Traces → Logs và biến SLO thành alert có thể hành động được.

### 7.6. Nguyễn Văn Tiến — Điều tra sự cố (CP3)

**Commit:** `bf05cfb3459b861db1d66d7875a5adfdfbb94563`

**Nhiệm vụ đã làm**

- Chạy challenge chính thức `day13-k3-observability-v1` với input trong `config/challenge.json`.
- Xác định triệu chứng từ metrics: P95 vọt lên 3483 ms trong khi P50 gần như đứng yên, cho thấy sự cố khu trú ở một nhóm request chứ không phải toàn hệ thống.
- Dùng 5 trace Langfuse khoanh vùng phần latency dôi ra nằm trước bước gọi LLM, tức bước RAG retrieval.
- Dùng log và correlation ID chứng minh root cause: cờ `rag_slow` chèn `time.sleep(2.5)` trong `app/mock_rag.py`, cộng thẳng vào latency đầu-cuối.
- Đề xuất hành động khắc phục (timeout và fallback cho `retrieve()`) và biện pháp phòng ngừa (alert P95, tách metric theo span, alert phân kỳ P50/P95).
- Viết mục 6 của báo cáo này.

**Bằng chứng:** `submission/evidence/challenge_investigation.txt`, `submission/evidence/challenge_logs.jsonl`
**Điều đã học:** Ba tầng quan sát trả lời ba câu hỏi khác nhau và không tầng nào thay được tầng nào. Metrics nói có vấn đề nhưng đã gộp mọi request thành một con số nên không chỉ được chỗ; traces mổ một request thành từng span nên nói được ở đâu; logs giữ dữ liệu thật của từng dòng nên mới chứng minh được tại sao.
