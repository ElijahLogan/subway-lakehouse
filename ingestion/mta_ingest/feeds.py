"""MTA subway GTFS-Realtime feed registry.

Feed IDs are short names used in tags, file paths and table columns.
See https://www.mta.info/developers for the official list.
"""

BASE_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/"

# feed_id -> URL path (already URL-encoded, as the MTA publishes it)
SUBWAY_FEEDS: dict[str, str] = {
    "ace": "nyct%2Fgtfs-ace",
    "bdfm": "nyct%2Fgtfs-bdfm",
    "g": "nyct%2Fgtfs-g",
    "jz": "nyct%2Fgtfs-jz",
    "nqrw": "nyct%2Fgtfs-nqrw",
    "l": "nyct%2Fgtfs-l",
    "1234567s": "nyct%2Fgtfs",
    "sir": "nyct%2Fgtfs-si",
}

ALERT_FEEDS: dict[str, str] = {
    "subway_alerts": "camsys%2Fsubway-alerts",
}


def feed_url(path: str) -> str:
    return BASE_URL + path


def all_feeds() -> dict[str, str]:
    return {**SUBWAY_FEEDS, **ALERT_FEEDS}
