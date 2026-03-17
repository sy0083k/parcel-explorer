from __future__ import annotations

from typing import Any

from fastapi import Request

from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services.web_stats_normalizers import (
    classify_browser_family,
    classify_device_type,
    classify_os_family,
    is_bot_user_agent,
    normalize_event_type,
    normalize_optional_int,
    normalize_optional_string,
    normalize_page_path,
    normalize_query_string,
    normalize_referrer_domain,
    normalize_referrer_url,
    normalize_required_token,
    parse_client_ts,
)
from app.services.web_stats_types import (
    ClientContext,
    MarketingContext,
    NormalizedWebVisitEvent,
    UserAgentContext,
)


def record_web_visit_event(payload: dict[str, Any], request: Request, *, allowed_paths: tuple[str, ...]) -> None:
    normalized_event = normalize_web_visit_event(payload, request, allowed_paths=allowed_paths)
    persist_web_visit_event(normalized_event)


def normalize_web_visit_event(
    payload: dict[str, Any],
    request: Request,
    *,
    allowed_paths: tuple[str, ...],
) -> NormalizedWebVisitEvent:
    event_type = normalize_event_type(payload.get("eventType"))
    anon_id = normalize_required_token(payload.get("anonId"), "anonId")
    session_id = normalize_required_token(payload.get("sessionId"), "sessionId")
    page_path = normalize_page_path(payload.get("pagePath"), allowed_paths=allowed_paths)
    page_query = normalize_query_string(payload.get("pageQuery"), max_length=1024)
    occurred_at = parse_client_ts(payload.get("clientTs"))

    client_context = normalize_client_context(payload)
    marketing_context = normalize_marketing_context(payload)
    user_agent_context = derive_user_agent_context(request)

    return NormalizedWebVisitEvent(
        anon_id=anon_id,
        session_id=session_id,
        event_type=event_type,
        page_path=page_path,
        page_query=page_query,
        occurred_at=occurred_at,
        client_tz=client_context.client_tz,
        client_lang=client_context.client_lang,
        platform=client_context.platform,
        referrer_url=marketing_context.referrer_url,
        referrer_domain=marketing_context.referrer_domain,
        utm_source=marketing_context.utm_source,
        utm_medium=marketing_context.utm_medium,
        utm_campaign=marketing_context.utm_campaign,
        utm_term=marketing_context.utm_term,
        utm_content=marketing_context.utm_content,
        screen_width=client_context.screen_width,
        screen_height=client_context.screen_height,
        viewport_width=client_context.viewport_width,
        viewport_height=client_context.viewport_height,
        user_agent=user_agent_context,
    )


def normalize_client_context(payload: dict[str, Any]) -> ClientContext:
    return ClientContext(
        client_tz=normalize_optional_string(payload.get("clientTz"), max_length=64),
        client_lang=normalize_optional_string(payload.get("clientLang"), max_length=64),
        platform=normalize_optional_string(payload.get("platform"), max_length=64),
        screen_width=normalize_optional_int(payload.get("screenWidth"), min_value=0, max_value=20000),
        screen_height=normalize_optional_int(payload.get("screenHeight"), min_value=0, max_value=20000),
        viewport_width=normalize_optional_int(payload.get("viewportWidth"), min_value=0, max_value=20000),
        viewport_height=normalize_optional_int(payload.get("viewportHeight"), min_value=0, max_value=20000),
    )


def normalize_marketing_context(payload: dict[str, Any]) -> MarketingContext:
    referrer_url = normalize_referrer_url(payload.get("referrerUrl"))
    return MarketingContext(
        referrer_url=referrer_url,
        referrer_domain=normalize_referrer_domain(payload.get("referrerDomain"), referrer_url),
        utm_source=normalize_optional_string(payload.get("utmSource"), max_length=256),
        utm_medium=normalize_optional_string(payload.get("utmMedium"), max_length=256),
        utm_campaign=normalize_optional_string(payload.get("utmCampaign"), max_length=256),
        utm_term=normalize_optional_string(payload.get("utmTerm"), max_length=256),
        utm_content=normalize_optional_string(payload.get("utmContent"), max_length=256),
    )


def derive_user_agent_context(request: Request) -> UserAgentContext:
    user_agent = request.headers.get("user-agent", "")[:500] or None
    is_bot = is_bot_user_agent(user_agent or "")
    return UserAgentContext(
        user_agent=user_agent,
        is_bot=is_bot,
        browser_family=classify_browser_family(user_agent or ""),
        device_type=classify_device_type(user_agent or "", is_bot=is_bot),
        os_family=classify_os_family(user_agent or ""),
    )


def persist_web_visit_event(event: NormalizedWebVisitEvent) -> None:
    with db_connection() as conn:
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id=event.anon_id,
            session_id=event.session_id,
            event_type=event.event_type,
            page_path=event.page_path,
            page_query=event.page_query,
            occurred_at=event.occurred_at,
            client_tz=event.client_tz,
            client_lang=event.client_lang,
            platform=event.platform,
            user_agent=event.user_agent.user_agent,
            is_bot=event.user_agent.is_bot,
            referrer_url=event.referrer_url,
            referrer_domain=event.referrer_domain,
            utm_source=event.utm_source,
            utm_medium=event.utm_medium,
            utm_campaign=event.utm_campaign,
            utm_term=event.utm_term,
            utm_content=event.utm_content,
            screen_width=event.screen_width,
            screen_height=event.screen_height,
            viewport_width=event.viewport_width,
            viewport_height=event.viewport_height,
            browser_family=event.user_agent.browser_family,
            device_type=event.user_agent.device_type,
            os_family=event.user_agent.os_family,
        )
        conn.commit()
