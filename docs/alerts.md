# Alert Runbooks

All investigations follow the same evidence order: Metrics -> Logs -> Traces.
Use only sanitized logs and traces. Do not copy raw user input, secrets, or PII into a ticket.

## HighLatencyP95

- Signal: P95 of `response_sent.latency_ms` is above 3000 ms for 5 minutes.
- Severity: warning.
- User impact: users wait longer for an answer.
- Owner and channel: `student-2A202602652`, Slack `#k4-l3b-alerts`.

Initial investigation:

1. Confirm the affected time range in the latency panel; compare P50, P95, P99, and TTFT P95.
2. Filter `data/logs.jsonl` for `response_sent` records with high `latency_ms`; select a matching `correlation_id`.
3. Open the Langfuse trace with that correlation ID and compare the `retrieval` and `llm-generation` durations.

Mitigation:

- If retrieval is slow, disable the practice scenario, restore the vector-store configuration, or reduce retrieval work.
- If generation is slow, rollback the prompt label or reduce prompt/context size after verifying the trace evidence.
- Re-run the same workload and verify P95 returns below the threshold before resolving the alert.

## HighErrorRate

- Signal: `request_failed / request_received` is above 2% for 5 minutes.
- Severity: critical.
- User impact: requests fail instead of returning an answer.
- Owner and channel: `student-2A202602652`, Slack `#k4-l3b-alerts`.

Initial investigation:

1. Confirm the error-rate panel and identify the error type and affected time range.
2. Filter `request_failed` logs in that period and select a sanitized log line with a `correlation_id`.
3. Open the trace with the same correlation ID; inspect the status and duration of `retrieval` and `llm-generation`.

Mitigation:

- For retrieval timeouts, disable the practice incident, restore the dependency, then retry a small workload.
- For generation failures, check the configured prompt/model connection and roll back the prompt label if the regression aligns with the incident.
- Keep the alert open until the error rate remains below 2% for the configured duration.

## LowRetrievalSuccess

- Signal: retrieval success rate (`tool_success == true`) is below 90% for 5 minutes.
- Severity: warning.
- User impact: answers may be incomplete, use fallback context, or fail.
- Owner and channel: `student-2A202602652`, Slack `#k4-l3b-alerts`.

Initial investigation:

1. Confirm the retrieval success rate and traffic volume in the dashboard error panel.
2. Filter logs for `tool_name=retrieval` and `tool_success=false`; capture a relevant `correlation_id`.
3. Open the trace with that correlation ID and inspect the `retrieval` observation for an error or abnormal duration.

Mitigation:

- Disable the practice failure scenario and validate vector-store availability.
- Retry the same query after recovery, then confirm retrieval success is at least 90%.
- Add a regression test or dependency health check when the failure mode is understood.