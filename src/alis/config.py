from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

# Chemin racine du dossier ALIS opérationnel
ALIS_PATH = Path(
    os.getenv(
        "ALIS_PATH",
        str(
            Path.home()
            / "Library/CloudStorage/GoogleDrive-evers.steeve@gmail.com/Mon Drive/AIAD/06_AGENTS/alis"
        ),
    )
)

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ALIS_MODEL: str = os.getenv("ALIS_MODEL", "claude-sonnet-4-6")
SCORE_THRESHOLD: int = int(os.getenv("ALIS_SCORE_THRESHOLD", "12"))

# Sous-dossiers
SIGNALS_INBOX = ALIS_PATH / "signals" / "inbox"
SIGNALS_SCORED = ALIS_PATH / "signals" / "scored"
SIGNALS_ARCHIVED = ALIS_PATH / "signals" / "archived"
HYPOTHESES_PENDING = ALIS_PATH / "hypotheses" / "pending"
HYPOTHESES_GO = ALIS_PATH / "hypotheses" / "go"
HYPOTHESES_NOGO = ALIS_PATH / "hypotheses" / "nogo"
HYPOTHESES_DEFERRED = ALIS_PATH / "hypotheses" / "deferred"
BRIEFINGS = ALIS_PATH / "briefings"
RELEASES = ALIS_PATH / "releases"
TEMPLATES = ALIS_PATH / "templates"
WATCHLIST = ALIS_PATH / "WATCHLIST.md"
