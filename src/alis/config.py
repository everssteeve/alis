import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Chemin racine du dossier ALIS opérationnel
ALIS_PATH = Path(
    os.getenv(
        "ALIS_PATH",
        str(
            Path.home()
            / "Library/CloudStorage/GoogleDrive-evers.steeve@gmail.com/Mon Drive/AIAD"
            / "06_AGENTS/alis"
        ),
    )
)

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ALIS_MODEL: str = os.getenv("ALIS_MODEL", "claude-sonnet-4-6")
SCORE_THRESHOLD: int = int(os.getenv("ALIS_SCORE_THRESHOLD", "12"))

# Règle permanente du Gardien (2026-11-11) : toute hypothèse dont le score est
# strictement supérieur à ce seuil est acceptée (GO) sans review manuelle.
AUTO_GO_ABOVE: float = float(os.getenv("ALIS_AUTO_GO_ABOVE", "14"))

# Cadence fixe du cycle (jours) — remplace le calendrier lunaire depuis le 2026-11-11.
CYCLE_CADENCE_DAYS: int = int(os.getenv("ALIS_CYCLE_CADENCE_DAYS", "28"))

# État local du cycle (hors Drive : lisible par launchd sans autorisation TCC).
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = Path(os.getenv("ALIS_STATE_DIR", str(REPO_ROOT / "state")))
CYCLE_STATE_FILE = STATE_DIR / "cycle.json"

# Sous-dossiers
SIGNALS_INBOX = ALIS_PATH / "signals" / "inbox"
SIGNALS_SCORED = ALIS_PATH / "signals" / "scored"
SIGNALS_ARCHIVED = ALIS_PATH / "signals" / "archived"
HYPOTHESES_PENDING = ALIS_PATH / "hypotheses" / "pending"
HYPOTHESES_GO = ALIS_PATH / "hypotheses" / "go"
HYPOTHESES_NOGO = ALIS_PATH / "hypotheses" / "nogo"
HYPOTHESES_DEFERRED = ALIS_PATH / "hypotheses" / "deferred"
DECISIONS = ALIS_PATH / "decisions"
BRIEFINGS = ALIS_PATH / "briefings"
RELEASES = ALIS_PATH / "releases"
TEMPLATES = ALIS_PATH / "templates"
WATCHLIST = ALIS_PATH / "WATCHLIST.md"
