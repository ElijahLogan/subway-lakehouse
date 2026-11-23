"""Optional Datadog custom metrics (free tier friendly).

Sends a handful of gauges per run via the v2 series API. If DD_API_KEY is not
set, metrics are logged and dropped, so the pipeline never depends on Datadog.

Keep tag cardinality low (feed + env only): the free plan allows ~100 custom
metrics per host, and every unique metric+tag combination counts as one.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request

log = logging.getLogger(__name__)

GAUGE = 3


class Metrics:
    def __init__(self, api_key: str | None, site: str = "datadoghq.com", env: str = "dev"):
        self.api_key = api_key
        self.site = site
        self.env = env
        self._series: list[dict] = []

    def gauge(self, name: str, value: float, tags: list[str] | None = None) -> None:
        self._series.append(
            {
                "metric": f"subway_lake.{name}",
                "type": GAUGE,
                "points": [{"timestamp": int(time.time()), "value": float(value)}],
                "tags": [f"env:{self.env}", *(tags or [])],
            }
        )

    def flush(self) -> None:
        series, self._series = self._series, []
        if not series:
            return
        if not self.api_key:
            log.info("metrics (not sent, no DD_API_KEY): %s", json.dumps(series))
            return
        req = urllib.request.Request(
            f"https://api.{self.site}/api/v2/series",
            data=json.dumps({"series": series}).encode(),
            method="POST",
            headers={"DD-API-KEY": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception:  # metrics must never break ingestion
            log.exception("failed to send metrics to Datadog")
