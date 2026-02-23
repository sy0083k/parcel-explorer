import json
from dataclasses import dataclass
from urllib.parse import quote_plus

from app.clients.http_client import get_json_with_retry


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
        try:
            res = get_json_with_retry(
                geo_url,
                timeout_s=self.timeout_s,
                retries=self.retries,
                backoff_s=self.backoff_s,
                request_id=request_id,
            )
            if res.get("response", {}).get("status") != "OK":
                return None

            point = res["response"]["result"]["point"]
            x = point["x"]
            y = point["y"]

            wfs_url = (
                f"https://api.vworld.kr/req/wfs?key={self.api_key}&service=WFS&version=1.1.0"
                f"&request=GetFeature&typename=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun"
                f"&bbox={x},{y},{x},{y}&srsname=EPSG:4326&output=application/json"
            )
            wfs_res = get_json_with_retry(
                wfs_url,
                timeout_s=self.timeout_s,
                retries=self.retries,
                backoff_s=self.backoff_s,
                request_id=request_id,
            )
            if wfs_res.get("features"):
                return json.dumps(wfs_res["features"][0]["geometry"])
            return json.dumps({"type": "Point", "coordinates": [float(x), float(y)]})
        except Exception:
            return None
