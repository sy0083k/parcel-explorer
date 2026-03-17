from __future__ import annotations

from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services.service_models import WebVisitContext, WebVisitEventCommand
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
    NormalizedWebVisitCore,
    NormalizedWebVisitEvent,
    UserAgentContext,
)


def record_web_visit_event(command: WebVisitEventCommand) -> None:
    normalized_event = normalize_web_visit_event(command)
    persist_web_visit_event(normalized_event)


def normalize_web_visit_event(command: WebVisitEventCommand) -> NormalizedWebVisitEvent:
    context = command.context
    core = normalize_web_visit_core(command, context)
    client_context = normalize_client_context(command)
    marketing_context = normalize_marketing_context(command)
    user_agent_context = derive_user_agent_context(context)
    return assemble_normalized_web_visit_event(core, client_context, marketing_context, user_agent_context)


def normalize_web_visit_core(command: WebVisitEventCommand, context: WebVisitContext) -> NormalizedWebVisitCore:
    return NormalizedWebVisitCore(
        anon_id=normalize_required_token(command.anon_id, "anonId"),
        session_id=normalize_required_token(command.session_id, "sessionId"),
        event_type=normalize_event_type(command.event_type),
        page_path=normalize_page_path(command.page_path, allowed_paths=context.allowed_web_track_paths),
        page_query=normalize_query_string(command.page_query, max_length=1024),
        occurred_at=parse_client_ts(command.client_ts),
    )


def assemble_normalized_web_visit_event(
    core: NormalizedWebVisitCore,
    client_context: ClientContext,
    marketing_context: MarketingContext,
    user_agent_context: UserAgentContext,
) -> NormalizedWebVisitEvent:
    return NormalizedWebVisitEvent(
        anon_id=core.anon_id,
        session_id=core.session_id,
        event_type=core.event_type,
        page_path=core.page_path,
        page_query=core.page_query,
        occurred_at=core.occurred_at,
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


def normalize_client_context(command: WebVisitEventCommand) -> ClientContext:
    return ClientContext(
        client_tz=normalize_optional_string(command.client_tz, max_length=64),
        client_lang=normalize_optional_string(command.client_lang, max_length=64),
        platform=normalize_optional_string(command.platform, max_length=64),
        screen_width=normalize_optional_int(command.screen_width, min_value=0, max_value=20000),
        screen_height=normalize_optional_int(command.screen_height, min_value=0, max_value=20000),
        viewport_width=normalize_optional_int(command.viewport_width, min_value=0, max_value=20000),
        viewport_height=normalize_optional_int(command.viewport_height, min_value=0, max_value=20000),
    )


def normalize_marketing_context(command: WebVisitEventCommand) -> MarketingContext:
    referrer_url = normalize_referrer_url(command.referrer_url)
    return MarketingContext(
        referrer_url=referrer_url,
        referrer_domain=normalize_referrer_domain(command.referrer_domain, referrer_url),
        utm_source=normalize_optional_string(command.utm_source, max_length=256),
        utm_medium=normalize_optional_string(command.utm_medium, max_length=256),
        utm_campaign=normalize_optional_string(command.utm_campaign, max_length=256),
        utm_term=normalize_optional_string(command.utm_term, max_length=256),
        utm_content=normalize_optional_string(command.utm_content, max_length=256),
    )


def derive_user_agent_context(context: WebVisitContext) -> UserAgentContext:
    user_agent = (context.user_agent or "")[:500] or None
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
