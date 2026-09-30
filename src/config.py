import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

# Resolve files from the project directory, not from the process working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Read the project's .env file when present. Real environment variables still win.
load_dotenv(PROJECT_ROOT / ".env")

# ---- LLM (OpenRouter) ----
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")

# ---- Database ----
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financial")
DB_USER = os.getenv("DB_USER", "agent")
DB_PASSWORD = os.getenv("DB_PASSWORD", "agentpass")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_DSN = DATABASE_URL or (
    f"postgresql://{quote(DB_USER, safe='')}:{quote(DB_PASSWORD, safe='')}"
    f"@{DB_HOST}:{DB_PORT}/{quote(DB_NAME, safe='')}"
)
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

# ---- Agent behaviour ----
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
_schema_path = Path(os.getenv("SCHEMA_PATH", "schema.yaml")).expanduser()
SCHEMA_PATH = _schema_path if _schema_path.is_absolute() else PROJECT_ROOT / _schema_path
