#!/usr/bin/env python3
"""Run lightweight non-functional checks against the in-process ASGI app.

Checks:
- response latency report (p50/p95) for representative public endpoints
- error rate
- X-Request-ID header presence for observability

Optionally validates p95 regression against a baseline JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

ENV_DEFAULTS = {
    "APP_NAME": "IdlePublicProperty",
    "MAP_CENTER_LON": "126.45",
    "MAP_CENTER_LAT": "36.78",
    "MAP_DEFAULT_ZOOM": "14",
    "VWORLD_WMTS_KEY": "test-key",
    "VWORLD_GEOCODER_KEY": "test-key",
    "ADMIN_ID": "admin",
    "ADMIN_PW_HASH": "$2b$12$MGjgBz6IZSV2boORoUbbQeLqG11Nry5H75zvbYOpJWfMaucKkVSZ6",
    "SECRET_KEY": "test-secret-key",
    "ALLOWED_IPS": "127.0.0.1/32,::1/128",
    "SESSION_HTTPS_ONLY": "false",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@contextmanager
def temp_env(values: dict[str, str]):
    original = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_app() -> Any:
    with temp_env(ENV_DEFAULTS):
        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        return app_main.app


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    sorted_data = sorted(data)
    index = int(round((len(sorted_data) - 1) * p))
    return sorted_data[index]


async def run_checks(
    *,
    samples: int,
    baseline: dict[str, float] | None,
    max_regression_ratio: float,
    max_error_rate: float,
) -> int:
    app = build_app()
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    results: dict[str, dict[str, float | int]] = {}
    failures: list[str] = []
    total_requests = 0
    total_errors = 0

    endpoints: list[tuple[str, str, dict[str, Any] | None]] = [
        ("GET", "/api/config", None),
        ("GET", "/api/lands?limit=100", None),
        (
            "POST",
            "/api/events",
            {
                "eventType": "search",
                "anonId": "nf-anon-1",
                "minArea": 120,
                "searchTerm": "대산읍",
            },
        ),
        (
            "POST",
            "/api/web-events",
            {
                "eventType": "visit_start",
                "anonId": "nf-anon-1",
                "sessionId": "nf-session-1",
                "pagePath": "/",
                "clientTs": 1763596800,
                "clientTz": "Asia/Seoul",
            },
        ),
    ]

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for method, path, payload in endpoints:
            latencies_ms: list[float] = []
            errors = 0
            missing_request_id = 0

            for _ in range(samples):
                started = time.perf_counter()
                if method == "GET":
                    response = await client.get(path)
                else:
                    response = await client.post(path, json=payload)
                elapsed_ms = (time.perf_counter() - started) * 1000

                total_requests += 1
                latencies_ms.append(elapsed_ms)

                if "x-request-id" not in response.headers:
                    missing_request_id += 1
                    errors += 1
                    total_errors += 1
                elif response.status_code >= 400:
                    errors += 1
                    total_errors += 1

            p50 = round(statistics.median(latencies_ms), 2)
            p95 = round(percentile(latencies_ms, 0.95), 2)
            error_rate = round(errors / samples, 4)
            key = f"{method} {path}"
            results[key] = {
                "samples": samples,
                "p50_ms": p50,
                "p95_ms": p95,
                "error_rate": error_rate,
                "missing_request_id": missing_request_id,
            }

            if error_rate > max_error_rate:
                failures.append(f"{key}: error_rate={error_rate} > {max_error_rate}")

            if baseline and key in baseline:
                baseline_p95 = baseline[key]
                if baseline_p95 > 0:
                    regression = (p95 - baseline_p95) / baseline_p95
                    if regression > max_regression_ratio:
                        failures.append(
                            f"{key}: p95 regression {regression:.2%} exceeds {max_regression_ratio:.2%}"
                        )

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))

    total_error_rate = (total_errors / total_requests) if total_requests else 0.0
    if total_error_rate > max_error_rate:
        failures.append(f"aggregate error_rate={total_error_rate:.4f} > {max_error_rate}")

    if failures:
        print("\n[non-functional-check] FAIL")
        for line in failures:
            print(f"- {line}")
        return 1

    print("\n[non-functional-check] PASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run non-functional checks for public API endpoints.")
    parser.add_argument("--samples", type=int, default=30, help="Requests per endpoint")
    parser.add_argument(
        "--baseline",
        type=str,
        default="",
        help="Optional JSON file containing baseline p95 values keyed by 'METHOD /path'",
    )
    parser.add_argument(
        "--max-regression-ratio",
        type=float,
        default=0.10,
        help="Allowed p95 regression ratio vs baseline (e.g. 0.10 == 10%%)",
    )
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=0.005,
        help="Allowed error rate for each endpoint and aggregate",
    )
    return parser.parse_args()


def load_baseline(path: str) -> dict[str, float] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(key): float(value) for key, value in data.items()}


def main() -> int:
    args = parse_args()
    baseline = load_baseline(args.baseline)
    return asyncio.run(
        run_checks(
            samples=args.samples,
            baseline=baseline,
            max_regression_ratio=args.max_regression_ratio,
            max_error_rate=args.max_error_rate,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
