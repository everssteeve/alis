from dataclasses import dataclass, field
from pathlib import Path
from datetime import date
from enum import Enum


class Decision(str, Enum):
    GO = "GO"
    NOGO = "NO GO"
    DEFER = "DEFER"
    PENDING = "PENDING"


class Component(str, Enum):
    FRAMEWORK = "framework"
    SDD_MODE = "sdd-mode"
    ALIS = "alis"
    CONSTITUTION = "constitution"


class SignalCategory(str, Enum):
    FRAMEWORK = "framework"
    SDD_MODE = "sdd-mode"
    GOUVERNANCE = "gouvernance"
    ECOSYSTEME = "écosystème"
    COMMUNAUTE = "communauté"
    CONSTITUTION = "constitution"


@dataclass
class SignalScore:
    frequence: int = 0       # 1-5
    impact: int = 0          # 1-5
    urgence: int = 0         # 1-5
    complexite: int = 0      # 1-5 (inversé : 5 = simple)

    @property
    def total(self) -> int:
        return self.frequence + self.impact + self.urgence + self.complexite


@dataclass
class Signal:
    id: str                  # SIG-YYYY-MM-NNN
    source_type: str         # externe | interne
    origin: str              # veille web | mission terrain | communauté | observation
    url: str = ""
    summary: str = ""
    detail: str = ""
    category: str = ""
    date: date = field(default_factory=date.today)
    score: SignalScore = field(default_factory=SignalScore)
    path: Path = field(default_factory=Path)
    raw_content: str = ""

    @property
    def score_total(self) -> int:
        return self.score.total


@dataclass
class Hypothesis:
    id: str                  # HYP-YYYY-MM-NNN
    title: str
    component: str
    summary: str = ""
    proposed_modification: str = ""
    terrain_justification: str = ""
    benefit: str = ""
    risk: str = ""
    effort: str = ""
    score: float = 0
    signal_ids: list[str] = field(default_factory=list)
    decision: Decision = Decision.PENDING
    decision_date: str = ""
    decision_comment: str = ""
    deferred_from: str = ""  # cycle précédent si DEFER
    path: Path = field(default_factory=Path)
    raw_content: str = ""

    @property
    def priority(self) -> str:
        if self.score >= 16:
            return "haute"
        elif self.score >= 12:
            return "moyenne"
        else:
            return "basse"
