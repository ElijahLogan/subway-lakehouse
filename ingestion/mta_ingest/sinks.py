"""Where snapshot batches get written: a Unity Catalog Volume, or local disk."""

from __future__ import annotations

import gzip
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from pathlib import Path


def to_ndjson_gz(rows: list[dict]) -> bytes:
    body = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n"
    return gzip.compress(body.encode(), compresslevel=6)


def object_key(record_type: str, fetched_at: int, run_id: str) -> str:
    """raw/<record_type>/dt=YYYY-MM-DD/<epoch>_<run_id>.json.gz (UTC)."""
    dt = datetime.fromtimestamp(fetched_at, tz=UTC)
    return f"{record_type}/dt={dt:%Y-%m-%d}/{fetched_at}_{run_id}.json.gz"


class VolumeSink:
    """Upload files to a Unity Catalog Volume using the Databricks Files API.

    No AWS storage involved: the Volume lives in Databricks-managed storage.
    """

    def __init__(self, host: str, token: str, volume_path: str, timeout: int = 30):
        self.host = host.rstrip("/")
        self.token = token
        self.volume_path = volume_path.rstrip("/")  # e.g. /Volumes/subway/raw/landing
        self.timeout = timeout

    def write(self, key: str, data: bytes) -> str:
        path = f"{self.volume_path}/{key}"
        url = f"{self.host}/api/2.0/fs/files{urllib.parse.quote(path)}?overwrite=true"
        req = urllib.request.Request(
            url,
            data=data,
            method="PUT",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/octet-stream",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp.read()
        return path


class LocalSink:
    """Write to a local folder. Handy for development and for tests."""
    def __init__(self, host: str, token: str, volume_path: str, timeout: int = 30):
        self.host = host.rstrip("/")
        self.token = token
        self.volume_path = volume_path.rstrip("/")  # e.g. /Volumes/subway/raw/landing
        self.timeout = timeout

    def __init__(self, root: str):
        self.root = Path(root)

    def write(self, key: str, data: bytes) -> str:
        path = f"{self.volume_path}/{key}"
        url = f"{self.host}/api/2.0/fs/files{urllib.parse.quote(path)}?overwrite=true"
        req = urllib.request.Request(
            url,
            data=data,
            method="PUT",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/octet-stream",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp.read()
        return path