from __future__ import annotations

import html
import json
import math
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
WINDOW_MINUTES = 60
REFRESH_SECONDS = 30


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _read_recent_records(now: datetime) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []

    cutoff = now - timedelta(minutes=WINDOW_MINUTES)
    records: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and timestamp >= cutoff:
            records.append(record)
    return records


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile / 100 * len(ordered)) - 1))
    return ordered[index]


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _format_number(value: float, suffix: str = "") -> str:
    return f"{value:,.2f}{suffix}"


def _panel(title: str, threshold: str, rows: list[tuple[str, str]]) -> str:
    rows_html = "".join(
        f"<div class='metric'><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>"
        for label, value in rows
    )
    return (
        "<section class='panel'>"
        f"<h2>{html.escape(title)}</h2>"
        f"<p class='threshold'>Threshold: {html.escape(threshold)}</p>"
        f"{rows_html}</section>"
    )


def render_dashboard(now: datetime | None = None) -> str:
    current_time = now or datetime.now(timezone.utc)
    records = _read_recent_records(current_time)
    responses = [record for record in records if record.get("event") == "response_sent"]
    requests = [record for record in records if record.get("event") == "request_received"]
    failures = [record for record in records if record.get("event") == "request_failed"]

    latencies = [value for record in responses if (value := _number(record.get("latency_ms"))) is not None]
    ttft_values = [value for record in responses if (value := _number(record.get("ttft_ms"))) is not None]
    costs = [value for record in responses if (value := _number(record.get("cost_usd"))) is not None]
    tokens_in = [value for record in responses if (value := _number(record.get("tokens_in"))) is not None]
    tokens_out = [value for record in responses if (value := _number(record.get("tokens_out"))) is not None]
    quality = [value for record in responses if (value := _number(record.get("quality_score"))) is not None]

    retrieval = [
        record for record in records
        if record.get("tool_name") == "retrieval" and isinstance(record.get("tool_success"), bool)
    ]
    retrieval_success = (
        100 * sum(record["tool_success"] for record in retrieval) / len(retrieval)
        if retrieval else 0.0
    )
    error_rate = 100 * len(failures) / len(requests) if requests else 0.0
    error_types = Counter(
        str(record.get("error_type", "unknown")) for record in failures
    )
    error_summary = ", ".join(f"{name}: {count}" for name, count in error_types.items()) or "none"

    panels = [
        _panel("Latency and TTFT", "P95 latency <= 3000 ms", [
            ("Latency P50", _format_number(_percentile(latencies, 50), " ms")),
            ("Latency P95", _format_number(_percentile(latencies, 95), " ms")),
            ("Latency P99", _format_number(_percentile(latencies, 99), " ms")),
            ("TTFT P95", _format_number(_percentile(ttft_values, 95), " ms")),
        ]),
        _panel("Traffic", "At least 1 request/minute", [
            ("Requests", str(len(requests))),
            ("Rate", _format_number(len(requests) / WINDOW_MINUTES, " requests/min")),
        ]),
        _panel("Errors and retrieval", "Error rate <= 2%; retrieval success >= 90%", [
            ("Error rate", _format_number(error_rate, "%")),
            ("Retrieval success", _format_number(retrieval_success, "%")),
            ("Error types", error_summary),
        ]),
        _panel("Cost", "Total <= USD 2.50", [
            ("Total cost", _format_number(sum(costs), " USD")),
            ("Responses measured", str(len(costs))),
        ]),
        _panel("Tokens", "Total <= 50,000 tokens", [
            ("Input tokens", _format_number(sum(tokens_in))),
            ("Output tokens", _format_number(sum(tokens_out))),
        ]),
        _panel("Quality proxy", "Mean >= 0.75", [
            ("Mean quality", _format_number(mean(quality) if quality else 0.0)),
            ("Responses measured", str(len(quality))),
        ]),
    ]

    generated_at = current_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta http-equiv='refresh' content='{REFRESH_SECONDS}'>
  <title>Day 13 Monitoring Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f7f8fc; color: #172033; }}
    .meta {{ color: #5f6b85; }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); }}
    .panel {{ background: white; border-radius: 12px; padding: 1.25rem; box-shadow: 0 2px 10px #17203315; }}
    h1 {{ margin-bottom: .25rem; }} h2 {{ font-size: 1.05rem; margin-top: 0; }}
    .threshold {{ color: #5f6b85; font-size: .9rem; min-height: 2.5rem; }}
    .metric {{ border-top: 1px solid #edf0f5; display: flex; gap: 1rem; justify-content: space-between; padding: .55rem 0; }}
    .metric strong {{ text-align: right; }}
  </style>
</head>
<body>
  <h1>Day 13 Monitoring and LLMOps</h1>
  <p class='meta'>Source: {html.escape(str(LOG_PATH))} | Window: last {WINDOW_MINUTES} minutes | Refresh: {REFRESH_SECONDS}s | Generated: {generated_at}</p>
  <p class='meta'>Records in window: {len(records)}. Empty panels show zero until the API receives traffic.</p>
  <main class='grid'>{''.join(panels)}</main>
</body>
</html>"""