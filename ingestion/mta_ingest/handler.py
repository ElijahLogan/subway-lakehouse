"""Poll every MTA feed once, write one gzipped NDJSON file per record type.

Batching all feeds into one file per record type per run avoids the small-file
problem: 1 run/minute -> ~4.3K files/day instead of ~26K.

Entry points:
  * lambda_handler(event, context)   AWS Lambda (scheduled every minute)
  * python -m mta_ingest.local       free local loop, no AWS at all
"""

from __future__ import annotations

import logging
import os
import time
import urllib.request
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from .feeds import all_feeds, feed_url
from .metrics import Metrics
from .parse import RECORD_TYPES, parse_feed
from .sinks import LocalSink, VolumeSink, object_key, to_ndjson_gz

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

USER_AGENT = "subway-lake/0.1 (+https://github.com/elijahlogan/subway-lakehouse)"

Fetcher = Callable[[str], bytes]


def http_fetch(path: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if key := os.environ.get("MTA_API_KEY"):  # not required today; supported if MTA adds it back
        headers["x-api-key"] = key
    req = urllib.request.Request(feed_url(path), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def run_once(sink, metrics: Metrics, fetch: Fetcher = http_fetch) -> dict:
    started = time.time()
    fetched_at = int(started)
    run_id = uuid.uuid4().hex[:8]
    feeds = all_feeds()

    def _one(item):
        feed_id, path = item
        try:
            return feed_id, parse_feed(feed_id, fetch(path), fetched_at), None
        except Exception as exc:  # one bad feed must not sink the run
            return feed_id, None, exc

    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        results = list(pool.map(_one, feeds.items()))

    batches: dict[str, list[dict]] = {k: [] for k in RECORD_TYPES}
    errors = 0
    for feed_id, parsed, exc in results:
        tags = [f"feed:{feed_id}"]
        if exc is not None:
            errors += 1
            log.warning("feed %s failed: %r", feed_id, exc)
            metrics.gauge("feed.fetch_error", 1, tags)
            continue
        metrics.gauge("feed.fetch_error", 0, tags)
        feed_ts = next((r["feed_timestamp"] for rows in parsed.values() for r in rows), None)
        if feed_ts:
            metrics.gauge("feed.lag_seconds", fetched_at - feed_ts, tags)
        metrics.gauge("feed.trip_updates", len(parsed["trip_updates"]), tags)
        for k in RECORD_TYPES:
            batches[k].extend(parsed[k])

    written = {}
    for record_type, rows in batches.items():
        if rows:
            written[record_type] = sink.write(
                object_key(record_type, fetched_at, run_id), to_ndjson_gz(rows)
            )

    metrics.gauge("run.duration_seconds", time.time() - started)
    metrics.gauge("run.feeds_failed", errors)
    metrics.flush()

    if errors == len(feeds):
        raise RuntimeError("every feed failed; see logs")
    summary = {"run_id": run_id, "errors": errors, "rows": {k: len(v) for k, v in batches.items()}}
    log.info("run complete %s", summary)
    return summary


# ---------------------------------------------------------------- Lambda glue

_cache: dict = {}


def _ssm(name: str | None) -> str | None:
    if not name:
        return None
    if name not in _cache:
        import boto3  # provided by the Lambda runtime; not bundled

        _cache[name] = boto3.client("ssm").get_parameter(Name=name, WithDecryption=True)[
            "Parameter"
        ]["Value"]
    return _cache[name]


def build_sink():
    token = os.environ.get("DATABRICKS_TOKEN") or _ssm(os.environ.get("DATABRICKS_TOKEN_PARAM"))
    return VolumeSink(os.environ["DATABRICKS_HOST"], token, os.environ["VOLUME_PATH"])


def build_metrics() -> Metrics:
    key = os.environ.get("DD_API_KEY") or _ssm(os.environ.get("DD_API_KEY_PARAM"))
    return Metrics(key, os.environ.get("DD_SITE", "datadoghq.com"), os.environ.get("ENV", "dev"))


def lambda_handler(event, context):
    return run_once(build_sink(), build_metrics())
