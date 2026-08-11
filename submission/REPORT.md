# Day 13 Observability Report

## 1. Group Info

- Group name:
- Repository URL:
- Final commit SHA:
- Members and roles:

## 2. Technical Results

- `validate_logs.py` score: 100/100. Evidence: `submission/evidence/validate_logs_cp2.txt`.
- Total traces: 10 Langfuse traces with metadata for CP2. Evidence: `submission/evidence/langfuse_10_traces_cp2.txt`.
- Remaining PII leaks: 0 according to `validate_logs.py`.
- Dashboard path: Streamlit local, run `streamlit run scripts/dashboard.py` and open `http://localhost:8501`. Data source: `data/logs.jsonl`. `error_rate_pct` = count(`request_failed`) / count(`request_received`) * 100.

## 3. Logging And Tracing

- Correlation ID evidence: `data/logs.jsonl` and `submission/evidence/validate_logs_cp2.txt`; validator found 11 unique correlation IDs.
- PII redaction evidence: `validate_logs.py` reported `Potential PII leaks detected: 0`; sample message preview redacts email as `[REDACTED_EMAIL]`.
- Trace waterfall evidence: use one trace from `submission/evidence/langfuse_10_traces_cp2.txt`, for example `d8ef17c116d45a84319d214182fb733b`.
- Notable span explanation: app attaches prompt metadata to trace and generation updates. Technical evidence: `submission/evidence/prompt_tracing_tests_cp2.txt`.

## 4. Prompt Versioning

- Prompt name: `day13-chat`.
- Baseline version/label: version 1 with labels `baseline` and `production`.
- Candidate version/label: version 2 with label `candidate`.
- Trace ID for each version: baseline `ba47689dd827372ce961c566258774cf`; candidate `eb06a44a39378ef187d1b4fb13722c02`. Evidence: `submission/evidence/langfuse_trace_ids_cp2.txt`.
- Label switch or rollback evidence: `submission/evidence/prompt_label_rollback_cp2.txt` shows `production` moved to version 2 and rolled back to version 1. Local tests confirm the app records `prompt_name`, `prompt_label`, and `prompt_version` in trace metadata.

## 5. Dashboard, SLO And Alerts

- `validate_dashboard.py` result: `HOP LE: 6/6 panel co trong dashboard contract.` Evidence: `submission/evidence/validate_dashboard_cp2.txt`.
- Dashboard evidence: screenshots are stored in `submission/evidence/Screenshot 2026-08-11 105102.png` through `submission/evidence/Screenshot 2026-08-11 105716.png`. Dashboard test evidence: `submission/evidence/dashboard_tests_cp2.txt`.
- Selected SLOs and reasons:

| Panel | Metric | SLO threshold | Reason |
|---|---|---|---|
| Latency | P95 latency | <= 3000 ms | Keeps chat responses usable and exposes slow RAG/model paths early. |
| Traffic | rate/min | >= 1 req/min | Confirms the service is receiving normal traffic. |
| Errors | error_rate_pct | <= 2% | Keeps failed user requests within an acceptable bound. |
| Cost | total cost | <= 2.50 USD | Keeps the lab workload inside the cost budget. |
| Tokens | total tokens | <= 50,000 | Detects prompt or retrieval changes that consume too many tokens. |
| Quality | mean score | >= 0.75 | Keeps the answer quality proxy above the minimum acceptable level. |

- Alert rules and runbook: `config/alert_rules.yaml` defines `HighLatencyP95`, `HighErrorRate`, and `QualityOrCostRegression`. The runbook in `docs/alerts.md` investigates incidents with the Metrics -> Traces -> Logs flow and includes a specific flow for the official `rag_slow` challenge on the `refund` feature.

## 6. Challenge Investigation

- Challenge ID: `day13-k3-observability-v1`.
- Symptom from metrics: expected latency increase on the `refund` feature because `config/challenge.json` sets incident `rag_slow`.
- Related trace ID: pending Langfuse trace ID from the official challenge run.
- Related log line/correlation ID: pending after running `python scripts/inject_incident.py` and `python scripts/load_test.py --challenge --concurrency 5`.
- Root cause: expected slow RAG path for `refund`; confirm with dashboard latency, slow Langfuse trace, and matching `response_sent` log.
- Fix action: disable the incident or revert the RAG/prompt change that increased latency after evidence is captured.
- Preventive measure: keep `HighLatencyP95`, review dashboard before prompt/RAG releases, and keep rollback steps in `docs/alerts.md`.

## 7. Individual Contributions

| Member | Work | Commit/PR | Learned |
|---|---|---|---|
| Thanh vien C | Built the six-panel dashboard in `scripts/dashboard.py`: latency P50/P95/P99, traffic, error rate, cost, tokens, quality, with SLO threshold indicators. | _(fill commit SHA)_ | How to calculate `error_rate_pct` from JSONL logs and visualize SLO status. |
| CP2 owner | Set SLO note, wrote alert rules, wrote alert runbook, generated CP2 validator evidence, and documented the incident investigation flow. | _(fill commit SHA)_ | How to connect Metrics -> Traces -> Logs and turn SLOs into actionable alerts. |
