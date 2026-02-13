"""Conversation API — FastAPI application entry point."""

from fastapi import FastAPI

from src.auth.routes import router as auth_router
from src.conversations.routes import router as conversations_router
from src.messages.routes import router as messages_router
from src.usage.routes import router as usage_router
from src.config.cors import SecurityHeadersMiddleware, configure_cors
from src.middleware.error_handler import register_error_handlers
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="Conversation API",
    description=(
        "A production-grade REST API for managing AI-powered conversations with streaming support.\n\n"
        "## Features\n"
        "- JWT and API key authentication\n"
        "- Conversation CRUD with ownership enforcement\n"
        "- Real-time token-by-token streaming via SSE\n"
        "- Multi-provider LLM support (Groq + Google AI fallback)\n"
        "- Context window management and token counting\n"
        "- Per-user rate limiting (standard + AI tiers)\n"
        "- Cost estimation and usage tracking\n\n"
        "## Authentication\n"
        "All endpoints (except `/health`, `/docs`, `/api/v1/auth/*`) require authentication.\n"
        "Use `Authorization: Bearer <jwt>` or `X-API-Key: <key>` header."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Auth", "description": "Authentication: register, login, token refresh, logout"},
        {"name": "Conversations", "description": "CRUD operations for conversations"},
        {"name": "Messages", "description": "Send messages, list messages, streaming"},
        {"name": "Streaming", "description": "Server-Sent Events for real-time message delivery"},
        {"name": "Usage", "description": "Usage statistics and model information"},
    ],
)

# --- Middleware (order matters: outermost first) ---
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
configure_cors(app)
app.add_middleware(RateLimiterMiddleware)

# --- Error handlers ---
register_error_handlers(app)

# --- Routes ---
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(usage_router)


@app.get("/health", tags=["Health"], summary="Health check", description="Returns OK if the service is running.")
async def health_check():
    return {"status": "ok"}
