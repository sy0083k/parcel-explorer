from __future__ import annotations

from collections.abc import Mapping

from app.services import map_event_service
from app.services.service_models import (
    LandClickMapEventCommand,
    MapEventCommand,
    SearchMapEventCommand,
    UnknownMapEventCommand,
    WebVisitContext,
    WebVisitEventCommand,
)


def build_map_event_command(payload: Mapping[str, object]) -> MapEventCommand:
    event_type = str(payload.get("eventType", "")).strip()
    if event_type == map_event_service.EVENT_TYPE_SEARCH:
        return SearchMapEventCommand(
            anon_id=payload.get("anonId"),
            min_area=payload.get("minArea"),
            search_term=payload.get("searchTerm"),
            raw_search_term=payload.get("rawSearchTerm"),
            raw_min_area_input=payload.get("rawMinAreaInput"),
            raw_max_area_input=payload.get("rawMaxAreaInput"),
            raw_rent_only=payload.get("rawRentOnly"),
        )
    if event_type == map_event_service.EVENT_TYPE_LAND_CLICK:
        return LandClickMapEventCommand(
            anon_id=payload.get("anonId"),
            land_address=payload.get("landAddress"),
            land_id=payload.get("landId"),
            click_source=payload.get("clickSource"),
        )
    return UnknownMapEventCommand(
        event_type=event_type,
        anon_id=payload.get("anonId"),
    )


def build_web_visit_event_command(
    payload: Mapping[str, object], *, context: WebVisitContext
) -> WebVisitEventCommand:
    return WebVisitEventCommand(
        context=context,
        event_type=payload.get("eventType"),
        anon_id=payload.get("anonId"),
        session_id=payload.get("sessionId"),
        page_path=payload.get("pagePath"),
        page_query=payload.get("pageQuery"),
        client_ts=payload.get("clientTs"),
        client_tz=payload.get("clientTz"),
        client_lang=payload.get("clientLang"),
        platform=payload.get("platform"),
        referrer_url=payload.get("referrerUrl"),
        referrer_domain=payload.get("referrerDomain"),
        utm_source=payload.get("utmSource"),
        utm_medium=payload.get("utmMedium"),
        utm_campaign=payload.get("utmCampaign"),
        utm_term=payload.get("utmTerm"),
        utm_content=payload.get("utmContent"),
        screen_width=payload.get("screenWidth"),
        screen_height=payload.get("screenHeight"),
        viewport_width=payload.get("viewportWidth"),
        viewport_height=payload.get("viewportHeight"),
    )
