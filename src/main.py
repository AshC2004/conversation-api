"""Conversation API — FastAPI application entry point."""

from fastapi import FastAPI

from src.auth.routes import router as auth_router
from src.config.cors import SecurityHeadersMiddleware, configure_cors
from src.middleware.error_handler import register_error_handlers
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="Conversation API",
    description="A production-grade REST API for managing AI-powered conversations with streaming support.",
    version="1.0.0",
)

# --- Middleware (order matters: outermost first) ---
# 1. Request ID — outermost so every response gets an ID
app.add_middleware(RequestIDMiddleware)
# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)
# 3. CORS
configure_cors(app)
# 4. Rate limiter
app.add_middleware(RateLimiterMiddleware)

# --- Error handlers ---
register_error_handlers(app)

# --- Routes ---
app.include_router(auth_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
