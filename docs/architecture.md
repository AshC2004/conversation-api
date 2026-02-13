# Architecture

## Overview

The Conversation API is a modular FastAPI application that provides a complete backend for AI-powered chat interfaces. It connects authenticated users to LLM providers through a layered architecture with clear separation of concerns.

```
Request Flow:

Client Request
  → RequestID Middleware (assign UUID)
  → Security Headers Middleware (nosniff, DENY, HSTS)
  → CORS Middleware (origin validation)
  → Rate Limiter Middleware (sliding window check)
  → FastAPI Router
    → Auth Dependency (JWT / API key verification)
    → Service Layer (business logic + ownership checks)
    → Repository / LLM Client (data access / model calls)
  → Response (JSON or SSE stream)
```

## Key Architectural Decisions

### 1. FastAPI + Supabase (No ORM)

**Decision**: Use Supabase's PostgREST client directly instead of SQLAlchemy or another ORM.

**Rationale**: Supabase provides a typed, parameterized query builder that prevents SQL injection while staying lightweight. Avoids ORM overhead for what is primarily a CRUD + LLM-call application. RLS policies in Supabase provide an additional security layer at the database level.

### 2. Service / Repository Pattern

**Decision**: Separate routes (HTTP concerns), services (business logic), and repositories (data access).

**Rationale**: Routes handle request parsing and response formatting. Services enforce authorization (ownership checks) and orchestrate operations. Repositories contain Supabase queries. This makes each layer independently testable and keeps route handlers thin.

### 3. JWT + API Key Dual Authentication

**Decision**: Support both Bearer JWT tokens and X-API-Key header authentication.

**Rationale**: JWTs suit interactive browser-based clients (short-lived access + refresh rotation). API keys suit programmatic access and integrations. Both paths resolve to a `CurrentUser` object so downstream code is auth-method agnostic.

**Token flow**:
- Access tokens: 30-minute expiry, contain user_id and email
- Refresh tokens: 7-day expiry, stored as SHA-256 hash in DB, revoked on use (rotation)
- API keys: SHA-256 hashed, checked for active status and expiry

### 4. In-Memory Rate Limiting

**Decision**: Sliding window rate limiter using in-memory dictionaries keyed by user_id.

**Rationale**: Simple, zero-dependency solution suitable for single-instance deployment. Two tiers: standard (60/min) for general API use, AI generation (10/min) for LLM endpoints. Easily replaceable with Redis for multi-instance deployments.

**Trade-off**: State is lost on restart and not shared across instances. Acceptable for the current deployment model.

## Streaming Implementation

### SSE Event Format

The streaming endpoint follows a structured event protocol inspired by Anthropic's Messages API:

```
1. message_start     — contains message ID and model
2. content_block_start — signals start of text content
3. content_block_delta — one per token/chunk from LLM
4. content_block_stop  — signals end of text content
5. message_delta     — contains stop_reason and token usage
6. message_stop      — signals end of message
```

On error mid-stream:
```
error — contains error type and message, then stream closes
```

### Stream Lifecycle

1. User message is saved to DB **before** streaming begins
2. Context is built (system prompt + conversation history within token budget)
3. SSE response opens with `text/event-stream` content type
4. LLM generates tokens, each yielded as `content_block_delta`
5. After stream completes, the full assistant response is saved to DB with token count and latency
6. If the client disconnects mid-stream, generation stops and partial content is discarded

### Fallback During Streaming

If the primary LLM provider (Groq) fails to initialize the stream, the system falls back to Google AI (Gemini) before any tokens are sent. Mid-stream failures result in an error event — there is no mid-stream provider switch.

## Context Window Management

### Strategy: Sliding Window with Anchored First Message

```
[system_prompt] + [first_user_message] + [...most_recent_messages_that_fit]
```

**Algorithm**:
1. Reserve tokens for system prompt
2. Calculate remaining budget (default: 6000 tokens)
3. Always include the first user message (provides conversation context)
4. Fill remaining budget from most recent messages backward
5. If the first message doesn't fit, skip it and use only recent messages

**Why anchor the first message**: The first message often establishes the topic or persona. Keeping it provides better context than a purely recency-based window.

## Cost Optimization

### Token Counting
- Uses `tiktoken` with `cl100k_base` encoding (reasonable approximation across models)
- Token counts stored per message for historical tracking

### Cost Estimation
- Maintains a price table per model (input/output rates per 1K tokens)
- Cost logged per request and stored in message metadata
- Usage stats endpoint aggregates totals per user

### Model Selection
- Default model (Llama 3.1 8B Instant) chosen for speed and low cost
- Users can override per-conversation or per-message
- Fallback model (Gemini 1.5 Flash) activated automatically on primary failure

## Security Measures

| Layer | Measure |
|-------|---------|
| Transport | HSTS header enforces HTTPS |
| CORS | Explicit origin allowlist, no wildcards |
| Headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection |
| Authentication | bcrypt password hashing, JWT with expiry, refresh token rotation |
| Authorization | Ownership verification on every resource access |
| Data access | Parameterized queries via Supabase client (no string concatenation) |
| Error handling | Structured error responses, no stack traces or internal paths exposed |
| Rate limiting | Per-user sliding window prevents abuse |
| Request tracing | UUID per request via X-Request-ID header |

## Database Schema

Five tables with foreign key relationships:

- `users` — authentication records
- `conversations` — chat sessions owned by users
- `messages` — individual messages within conversations
- `api_keys` — hashed API keys for programmatic access
- `refresh_tokens` — hashed refresh tokens with revocation support

RLS is enabled on all sensitive tables. Cascading deletes ensure cleanup when conversations or users are removed.
