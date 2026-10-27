"""Secret-free AI configuration and an explicit model-access diagnostic."""

from fastapi import HTTPException
from openai import APIConnectionError, APIError, APIStatusError, AsyncOpenAI

from app.agent.copilot_research import ResearchSettings


def ai_status(settings: ResearchSettings) -> dict:
    configured = bool(settings.openai_api_key.get_secret_value().strip())
    enabled = configured and settings.ai_enabled
    state = (
        "disabled"
        if not settings.ai_enabled
        else "configured"
        if configured
        else "not_configured"
    )
    messages = {
        "configured": "AI is configured. Run a connection check to verify model access.",
        "disabled": "AI generation is disabled by the workspace administrator. Calculations and exports remain available.",
        "not_configured": "AI is not connected. Calculations, sensitivity recommendations and exports remain available.",
    }
    return {
        "state": state,
        "can_generate": enabled,
        "model": settings.openai_model,
        "connection_verified": False,
        "research_domains": settings.research_domains,
        "message": messages[state],
    }


def require_ai(settings: ResearchSettings):
    if not settings.ai_enabled:
        raise HTTPException(
            503, "AI generation is disabled by the workspace administrator."
        )
    if not settings.openai_api_key.get_secret_value().strip():
        raise HTTPException(
            503,
            "AI is not connected. The workspace administrator must configure OPENAI_API_KEY on the backend.",
        )


def provider_message(status: int) -> str:
    return {
        401: "AI authentication failed. Ask the workspace administrator to check the provider key.",
        403: "The AI account cannot access the configured model or tool.",
        404: "The configured AI model is unavailable to this account.",
        429: "The AI rate or billing limit was reached. Retry later or ask the administrator to check account limits.",
    }.get(status, "The AI provider is unavailable. Retry later.")


async def check_connection(settings: ResearchSettings) -> dict:
    require_ai(settings)
    try:
        async with AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=15,
            max_retries=0,
        ) as client:
            await client.models.retrieve(settings.openai_model)
    except APIStatusError as exc:
        raise HTTPException(503, provider_message(exc.status_code)) from exc
    except (APIConnectionError, TimeoutError, APIError) as exc:
        raise HTTPException(
            503, "Could not reach the AI provider. Retry the connection check."
        ) from exc
    return {
        **ai_status(settings),
        "connection_verified": True,
        "message": "Provider authentication and model access verified. Generation, billing quota and live-search compatibility are checked when a request runs.",
    }
