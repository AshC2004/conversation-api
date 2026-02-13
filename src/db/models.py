"""Database table name constants and type references."""

# Table names — single source of truth for Supabase queries
USERS = "users"
CONVERSATIONS = "conversations"
MESSAGES = "messages"
API_KEYS = "api_keys"
REFRESH_TOKENS = "refresh_tokens"

# Role constants
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
VALID_ROLES = {ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM}
