# Video Demo Script — Conversation API

## Pre-recording Setup

```bash
# Terminal 1: Start the server
cd ~/Projects/conversation-api
source .venv/bin/activate
uvicorn src.main:app --reload

# Terminal 2: Have these ready
export BASE=http://localhost:8000
```

Open in browser: `http://localhost:8000/docs` (Swagger UI)

---

## Repo 2 Segment (~5 min)

### 1. Project Overview (30s)

> "This is a production-grade REST API for AI-powered conversations — think a backend for ChatGPT-style apps. Built with FastAPI, Supabase for Postgres, and Groq as the primary LLM provider with Google Gemini as a fallback."

Show the folder structure in your editor:

```
src/
├── auth/           → JWT + API key authentication
├── config/         → Settings, CORS
├── conversations/  → CRUD with ownership enforcement
├── db/             → Supabase client
├── llm/            → Multi-provider LLM abstraction
├── messages/       → Send, stream, SSE events
├── middleware/      → Rate limiter, request ID, error handler
└── usage/          → Cost tracking, models listing
```

> "Layered architecture — routes handle HTTP, services enforce business rules, repositories talk to the database."

---

### 2. Auth Flow (1 min)

**Register:**
```bash
curl -s -X POST $BASE/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"SecurePass123"}' | python3 -m json.tool
```

> "Registration returns a JWT access token and a refresh token. Passwords are bcrypt-hashed, refresh tokens are stored as SHA-256 hashes in the database."

**Login:**
```bash
curl -s -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"SecurePass123"}' | python3 -m json.tool
```

Save the token:
```bash
export TOKEN=<paste access_token>
```

**Show 401:**
```bash
curl -s $BASE/api/v1/conversations | python3 -m json.tool
```

> "Without a token, you get a structured 401 with a request ID for traceability. Every error follows this same format — type, message, request_id. No stack traces ever leak."

---

### 3. Conversation + Non-Streaming Message (1 min)

**Create conversation:**
```bash
curl -s -X POST $BASE/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","system_prompt":"You are a helpful coding assistant."}' | python3 -m json.tool
```

Save the ID:
```bash
export CID=<paste conversation id>
```

**Send a message:**
```bash
curl -s -X POST $BASE/api/v1/conversations/$CID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"What is a REST API? Explain in 2 sentences."}' | python3 -m json.tool
```

> "Notice the response includes latency_ms, token_count, the model used, finish_reason, and in the metadata — input token count and estimated cost in USD. Every request is tracked."

---

### 4. Streaming — The Main Event (1 min)

```bash
curl -N -X POST $BASE/api/v1/conversations/$CID/messages/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Write a Python function that checks if a number is prime."}'
```

> "Real token-by-token streaming over Server-Sent Events. The event format follows a structured protocol — message_start, then content_block_delta for each token, then message_stop."

> "The event sequence is: message_start → content_block_start → content_block_delta (repeats for every token) → content_block_stop → message_delta with usage stats → message_stop."

> "After the stream finishes, the full response is saved to the database with token count and latency. If the client disconnects mid-stream, we detect it and stop generation."

---

### 5. Swagger Docs (30s)

Switch to browser showing `http://localhost:8000/docs`

> "Full OpenAPI documentation generated automatically by FastAPI. Every endpoint has descriptions, request schemas, and is organized by tags — Auth, Conversations, Messages, Streaming, Usage."

Click through a couple endpoints to show the schemas.

Also show: `http://localhost:8000/redoc` briefly.

---

### 6. Highlight Reel (1 min)

**Auto-title generation:**
```bash
curl -s "$BASE/api/v1/conversations/$CID" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print('Title:', json.load(sys.stdin)['data']['title'])"
```

> "On the first message in any conversation, an async background task calls the LLM to generate a concise title. It's fire-and-forget — doesn't block the response."

**Ownership enforcement (403):**
```bash
# Register a second user
OTHER=$(curl -s -X POST $BASE/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"other@example.com","password":"OtherPass123"}')
OTHER_TOKEN=$(echo $OTHER | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Try to access the first user's conversation
curl -s "$BASE/api/v1/conversations/$CID" \
  -H "Authorization: Bearer $OTHER_TOKEN" | python3 -m json.tool
```

> "403 Forbidden. Every resource operation checks ownership at the service layer."

**Usage stats:**
```bash
curl -s $BASE/api/v1/usage/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

> "Per-user aggregation of tokens used and estimated cost. Helpful for monitoring and budgeting."

**Models endpoint:**
```bash
curl -s $BASE/api/v1/models -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

> "Lists all supported models with provider, context window size, and cost per 1K tokens."

**Tests:**
```bash
pytest tests/ -v
```

> "26 integration tests covering auth flows, conversation CRUD with ownership checks, message sending, token counting, and SSE streaming format validation. All passing."

---

## Code Walkthrough Talking Points (for shared segment)

### Architecture Decisions
- **FastAPI + Supabase without an ORM** — Supabase's query builder is already parameterized and type-safe, keeps things lightweight
- **Service/Repository pattern** — routes stay thin, business logic is testable in isolation
- **Dual auth (JWT + API key)** — JWTs for interactive use, API keys for programmatic access, both resolve to the same CurrentUser object

### Security Implementation
- Bcrypt password hashing
- JWT with short-lived access tokens (30min) and refresh token rotation
- CORS with explicit origin allowlist (no wildcards)
- Security headers: HSTS, X-Frame-Options DENY, nosniff, XSS protection
- Structured errors that never expose internals
- Per-user rate limiting with Retry-After headers

### Streaming Implementation
- Uses Starlette's StreamingResponse with async generator
- Each LLM token yielded as an SSE content_block_delta event
- Client disconnect detection stops generation
- Full response saved to DB after stream completes
- If primary provider (Groq) fails before streaming starts, falls back to Google Gemini

### What I'd Improve With More Time
- Redis-backed rate limiting for horizontal scaling
- WebSocket support alongside SSE
- Conversation search and filtering
- Message editing and regeneration
- Prompt caching for repeated system prompts
- More granular API key scopes
