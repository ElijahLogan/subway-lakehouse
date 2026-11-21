"""Run the poller on your own machine: the $0 alternative to Lambda.

python -m mta_ingest.local --interval 60          # upload to the Volume
LOCAL_OUTPUT_DIR=./data python -m mta_ingest.local --once   # write to disk
"""

from __future__ import annotations

import argparse
import logging
import time

from .handler import build_metrics, build_sink, run_once


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=int, default=60, help="seconds between polls")
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sink, metrics = build_sink(), build_metrics()
    while True:
        t0 = time.time()
        try:
            run_once(sink, metrics)
        except Exception:
            logging.exception("run failed")
        if args.once:
            break
        time.sleep(max(0, args.interval - (time.time() - t0)))


if __name__ == "__main__":
    main()
