"""Decode GTFS-RT protobuf payloads into JSON-friendly rows.

Rows are kept lightly nested (one trip update row carries its list of stop
time updates) so the raw files stay compact. Silver explodes them in Spark.
"""

from __future__ import annotations

from google.transit import gtfs_realtime_pb2

RECORD_TYPES = ("trip_updates", "vehicle_positions", "alerts")


def _trip(t) -> dict:
    return {
        "trip_id": t.trip_id or None,
        "route_id": t.route_id or None,
        "start_date": t.start_date or None,
        "start_time": t.start_time or None,
    }


def _event_time(stu, field: str) -> int | None:
    if stu.HasField(field):
        ev = getattr(stu, field)
        return ev.time or None
    return None


def _text(translated) -> str | None:
    for tr in translated.translation:
        if not tr.language or tr.language.startswith("en"):
            return tr.text
    return translated.translation[0].text if translated.translation else None


def parse_feed(feed_id: str, payload: bytes, fetched_at: int) -> dict[str, list[dict]]:
    """Parse one feed snapshot. Returns rows grouped by record type."""
    msg = gtfs_realtime_pb2.FeedMessage()
    msg.ParseFromString(payload)

    base = {
        "feed_id": feed_id,
        "feed_timestamp": msg.header.timestamp or None,
        "fetched_at": fetched_at,
    }
    out: dict[str, list[dict]] = {k: [] for k in RECORD_TYPES}

    for e in msg.entity:
        if e.HasField("trip_update"):
            tu = e.trip_update
            out["trip_updates"].append(
                {
                    **base,
                    "entity_id": e.id,
                    **_trip(tu.trip),
                    "stop_time_updates": [
                        {
                            "stop_id": s.stop_id or None,
                            "arrival_time": _event_time(s, "arrival"),
                            "departure_time": _event_time(s, "departure"),
                        }
                        for s in tu.stop_time_update
                    ],
                }
            )
        if e.HasField("vehicle"):
            v = e.vehicle
            out["vehicle_positions"].append(
                {
                    **base,
                    "entity_id": e.id,
                    **_trip(v.trip),
                    "stop_id": v.stop_id or None,
                    "current_stop_sequence": v.current_stop_sequence,
                    "current_status": gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(
                        v.current_status
                    ),
                    "vehicle_timestamp": v.timestamp or None,
                }
            )
        if e.HasField("alert"):
            a = e.alert
            out["alerts"].append(
                {
                    **base,
                    "entity_id": e.id,
                    "route_ids": sorted({ie.route_id for ie in a.informed_entity if ie.route_id}),
                    "stop_ids": sorted({ie.stop_id for ie in a.informed_entity if ie.stop_id}),
                    "active_periods": [
                        {"start": p.start or None, "end": p.end or None} for p in a.active_period
                    ],
                    "header_text": _text(a.header_text),
                    "description_text": _text(a.description_text),
                }
            )
    return out
