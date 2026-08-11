# Alert Rules And Runbook

Each alert is based on a user-visible symptom or an SLO breach. During an incident, collect evidence in this order: dashboard metric, Langfuse trace, then the JSON log line with the matching `correlation_id` or `trace_id`.

## HighLatencyP95

- Name: HighLatencyP95
- Severity: critical
- Related SLI/SLO: `latency_p95_ms <= 3000` over the active dashboard window.
- Condition and duration: `p95(response_sent.latency_ms, 5m) > 3000`.
- User impact: chat answers feel slow or time out; support workflows such as `refund` can become unreliable.
- First checks:
  1. Open the Latency panel and confirm P95/P99 crossed the 3000 ms threshold.
  2. Filter the same time range in Langfuse and open the slowest traces, prioritizing the affected `feature`.
  3. Use the trace metadata or `correlation_id` to find matching `response_sent` logs and compare `latency_ms`, `tokens_in`, `tokens_out`, `feature`, and `session_id`.
- Temporary mitigation: rollback the prompt label if a new prompt increased token count, reduce expensive RAG retrieval, or disable the injected incident after evidence is captured.
- Owner: CP2-SLO-alert-runbook.

## HighErrorRate

- Name: HighErrorRate
- Severity: critical
- Related SLI/SLO: `error_rate_pct <= 2`.
- Condition and duration: `count(request_failed, 5m) / count(request_received, 5m) * 100 > 2`.
- User impact: users receive failed responses instead of useful AI answers.
- First checks:
  1. Open the Errors panel and confirm the error rate is above 2 percent.
  2. Group failing logs by `error_type`, `feature`, `model`, and `env` to identify whether one workflow is affected.
  3. Open traces for failed requests and inspect the failing span, then link the trace to the log line by `correlation_id`.
- Temporary mitigation: rollback the last risky change, route traffic away from the failing feature, or use a local fallback response while the failing dependency is fixed.
- Owner: CP2-SLO-alert-runbook.

## QualityOrCostRegression

- Name: QualityOrCostRegression
- Severity: warning
- Related SLI/SLO: `quality_score_avg >= 0.75` and `daily_cost_usd <= 2.5`.
- Condition and duration: `mean(response_sent.quality_score, 10m) < 0.75 OR sum(response_sent.cost_usd, 60m) > 2.5`.
- User impact: users may receive weaker answers, or the same traffic may become too expensive to operate.
- First checks:
  1. Open Quality, Cost, and Tokens panels for the same time range and check whether quality dropped, cost rose, or token usage spiked.
  2. Compare traces by `prompt_name`, `prompt_label`, and `prompt_version` to see whether a prompt change caused the regression.
  3. Inspect `response_sent` logs for `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `feature`, and `session_id`.
- Temporary mitigation: rollback to the last known-good prompt label, cap max output tokens, or simplify retrieval context until quality and cost return within SLO.
- Owner: CP2-SLO-alert-runbook.

## Challenge Investigation Flow

For the official K3 challenge, `config/challenge.json` currently points to `rag_slow` on the `refund` feature. Use this flow after running the challenge load:

1. Metrics: verify the Latency panel crosses the SLO threshold and note the time range.
2. Traces: open Langfuse traces for `feature=refund` in that time range and capture the slow trace ID.
3. Logs: search `data/logs.jsonl` for the same `correlation_id` or `session_id`, then copy the relevant `response_sent` line into the report.
4. Root cause: state the component that made the request slow, the affected feature, and the evidence connecting metrics to traces and logs.
5. Prevention: keep the HighLatencyP95 alert, add dashboard review during prompt/RAG changes, and document rollback steps.
