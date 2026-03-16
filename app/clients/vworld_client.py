import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests

from app.clients.http_client import NonRetryableHTTPError, get_json_with_retry
from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


def _classify_vworld_outcome(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.Timeout):
        return "timeout"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "transport_error"
    if isinstance(exc, (requests.exceptions.HTTPError, NonRetryableHTTPError)):
        return "upstream_error"
    if isinstance(exc, (json.JSONDecodeError, KeyError, ValueError, TypeError)):
        return "invalid_payload"
    return "upstream_error"


def check_geocoder_health(
    *,
    api_key: str,
    timeout_s: float,
    retries: int,
    backoff_s: float,
    request_id: str = "-",
) -> bool:
    sample_geo_url = (
        "https://api.vworld.kr/req/address"
        "?service=address&request=getcoord&type=parcel"
        "&address=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C+%EC%A4%91%EA%B5%AC+%EC%84%B8%EC%A2%85%EB%8C%80%EB%A1%9C+110"
        f"&key={api_key}"
    )
    payload = get_json_with_retry(
        sample_geo_url,
        timeout_s=timeout_s,
        retries=retries,
        backoff_s=backoff_s,
        request_id=request_id,
    )
    status = payload.get("response", {}).get("status")
    return status in {"OK", "NOT_FOUND"}


@dataclass(frozen=True)
class VWorldClient:
    api_key: str
    timeout_s: float
    retries: int
    backoff_s: float

    def get_parcel_geometry(self, address: str, request_id: str = "-") -> str | None:
        encoded_address = quote_plus(address)
        geo_url = (
            "https://api.vworld.kr/req/address"
            f"?service=address&request=getcoord&address={encoded_address}"
            f"&key={self.api_key}&type=parcel"
        )

        # Geocoder step
        geocoder_status_ok = False
        t0 = time.perf_counter()
        try:
            res = get_json_with_retry(
                geo_url,
                timeout_s=self.timeout_s,
                retries=self.retries,
                backoff_s=self.backoff_s,
                request_id=request_id,
            )
            geocoder_latency = round((time.perf_counter() - t0) * 1000, 2)
            geocoder_status_ok = res.get("response", {}).get("status") == "OK"
            geocoder_outcome = "success" if geocoder_status_ok else "not_found"
        except Exception as exc:
            geocoder_latency = round((time.perf_counter() - t0) * 1000, 2)
            geocoder_outcome = _classify_vworld_outcome(exc)
            logger.info(
                "vworld request completed",
                extra={
                    "event": "vworld.request.completed",
                    "actor": "system",
                    "request_id": request_id,
                    "step": "geocoder",
                    "latency_ms": geocoder_latency,
                    "outcome": geocoder_outcome,
                    "status": 500,
                },
            )
            return None

        logger.info(
            "vworld request completed",
            extra={
                "event": "vworld.request.completed",
                "actor": "system",
                "request_id": request_id,
                "step": "geocoder",
                "latency_ms": geocoder_latency,
                "outcome": geocoder_outcome,
                "status": 200,
            },
        )

        if not geocoder_status_ok:
            return None

        try:
            point = res["response"]["result"]["point"]
            x = point["x"]
            y = point["y"]
        except (KeyError, TypeError):
            return None

        wfs_url = (
            f"https://api.vworld.kr/req/wfs?key={self.api_key}&service=WFS&version=1.1.0"
            f"&request=GetFeature&typename=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun"
            f"&bbox={x},{y},{x},{y}&srsname=EPSG:4326&output=application/json"
        )

        # WFS step
        t1 = time.perf_counter()
        try:
            wfs_res = get_json_with_retry(
                wfs_url,
                timeout_s=self.timeout_s,
                retries=self.retries,
                backoff_s=self.backoff_s,
                request_id=request_id,
            )
            wfs_latency = round((time.perf_counter() - t1) * 1000, 2)
            wfs_outcome = "success"
        except Exception as exc:
            wfs_latency = round((time.perf_counter() - t1) * 1000, 2)
            wfs_outcome = _classify_vworld_outcome(exc)
            logger.info(
                "vworld request completed",
                extra={
                    "event": "vworld.request.completed",
                    "actor": "system",
                    "request_id": request_id,
                    "step": "wfs",
                    "latency_ms": wfs_latency,
                    "outcome": wfs_outcome,
                    "status": 500,
                },
            )
            return None

        logger.info(
            "vworld request completed",
            extra={
                "event": "vworld.request.completed",
                "actor": "system",
                "request_id": request_id,
                "step": "wfs",
                "latency_ms": wfs_latency,
                "outcome": wfs_outcome,
                "status": 200,
            },
        )

        if wfs_res.get("features"):
            return json.dumps(wfs_res["features"][0]["geometry"])
        return json.dumps({"type": "Point", "coordinates": [float(x), float(y)]})
