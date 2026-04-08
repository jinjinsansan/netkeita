import os
from dotenv import load_dotenv

load_dotenv(".env.local")

DLOGIC_API_URL = os.getenv("DLOGIC_API_URL", "http://localhost:8000")
PREFETCH_DIR = os.getenv("PREFETCH_DIR", "../dlogic-agent/data/prefetch")
PORT = int(os.getenv("PORT", "5002"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.netkeita.com")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Comma-separated LINE user IDs allowed to create / edit / delete articles.
# Example .env.local entry:
#   ADMIN_LINE_USER_IDS=Uxxxxxxxxxxxxxxxxxxx,Uyyyyyyyyyyyyyyyyyyy
ADMIN_LINE_USER_IDS = [
    s.strip() for s in os.getenv("ADMIN_LINE_USER_IDS", "").split(",") if s.strip()
]

# Internal API key for server-to-server article posting (e.g. dlogic-note cron)
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
