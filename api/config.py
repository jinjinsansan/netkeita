import os
from dotenv import load_dotenv

load_dotenv()

DLOGIC_API_URL = os.getenv("DLOGIC_API_URL", "http://localhost:8000")
PREFETCH_DIR = os.getenv("PREFETCH_DIR", "../dlogic-agent/data/prefetch")
PORT = int(os.getenv("PORT", "5001"))
