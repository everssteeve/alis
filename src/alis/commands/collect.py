"""Phase 1 — Collecte de signaux depuis la WATCHLIST.

Sources surveillées :
- Flux RSS / pages web des sujets de la WATCHLIST
- Pages GitHub releases/tags des outils SDD clés
"""

from datetime import date
from pathlib import Path
import re

import httpx
import feedparser
from bs4 import BeautifulSoup
from rich.console import Console
import anthropic

from ..config import ANTHROPIC_API_KEY, ALIS_MODEL, SIGNALS_INBOX, WATCHLIST
from ..models import Signal, SignalScore

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Sources de veille automatisables — Cartographie ALIS v1.0
# Référence complète : sources/VEILLE-CARTOGRAPHIE.md
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SOURCES: list[dict] = [

    # ── Strate 1 — Rapports de fond (signal structurel) ──────────────────────
    {
        "id": "anthropic-research",
        "name": "Anthropic Research — Publications",
        "type": "web",
        "url": "https://www.anthropic.com/research",
        "category": "écosystème",
        "keywords": ["agent", "coding", "agentic", "specification", "context"],
        "strate": 1,
    },
    {
        "id": "github-octoverse",
        "name": "GitHub Blog — AI & Octoverse",
        "type": "rss",
        "url": "https://github.blog/feed/",
        "category": "écosystème",
        "keywords": ["ai", "copilot", "spec", "agent", "coding", "octoverse"],
        "strate": 1,
    },

    # ── Strate 2 — Newsletters (signal tactique) ─────────────────────────────
    {
        "id": "simon-willison",
        "name": "Simon Willison's Weblog",
        "type": "rss",
        "url": "https://simonwillison.net/atom/everything/",
        "category": "écosystème",
        "keywords": ["llm", "agent", "claude", "spec", "coding", "ai"],
        "strate": 2,
    },
    {
        "id": "latent-space",
        "name": "Latent Space (swyx + Alessio)",
        "type": "rss",
        "url": "https://www.latent.space/feed",
        "category": "écosystème",
        "keywords": ["agent", "engineering", "spec", "context", "ai"],
        "strate": 2,
    },
    {
        "id": "ethan-mollick",
        "name": "Ethan Mollick — One Useful Thing",
        "type": "rss",
        "url": "https://www.oneusefulthing.org/feed",
        "category": "framework",
        "keywords": ["ai", "agent", "productivity", "workflow", "human"],
        "strate": 2,
    },

    # ── Strate 3 — Médias techniques (signal éditorial) ──────────────────────
    {
        "id": "infoq-ai",
        "name": "InfoQ — AI/ML & Architecture",
        "type": "rss",
        "url": "https://feed.infoq.com/",
        "category": "framework",
        "keywords": ["agent", "specification", "architecture", "ai", "sdd", "spec"],
        "strate": 3,
    },
    {
        "id": "thenewstack-ai",
        "name": "The New Stack — AI Engineering",
        "type": "rss",
        "url": "https://thenewstack.io/feed/",
        "category": "écosystème",
        "keywords": ["agent", "ai engineering", "spec", "context", "agentic"],
        "strate": 3,
    },

    # ── Strate 4 — Sources primaires éditeurs (signal produit) ───────────────
    {
        "id": "anthropic-news",
        "name": "Anthropic — Blog & News",
        "type": "rss",
        "url": "https://www.anthropic.com/rss.xml",
        "category": "écosystème",
        "keywords": ["agent", "coding", "claude", "specification", "workflow", "mcp"],
        "strate": 4,
    },
    {
        "id": "fowler-bliki",
        "name": "Martin Fowler — Bliki",
        "type": "rss",
        "url": "https://martinfowler.com/feed.atom",
        "category": "sdd-mode",
        "keywords": ["spec", "sdd", "agentic", "ai", "agent", "specification"],
        "strate": 4,
    },
    {
        "id": "tessl-blog",
        "name": "Tessl — Blog",
        "type": "web",
        "url": "https://tessl.io/blog",
        "category": "sdd-mode",
        "keywords": ["spec", "agent", "sdd", "specification"],
        "strate": 4,
    },
    {
        "id": "github-kiro",
        "name": "AWS Kiro — Changelog",
        "type": "web",
        "url": "https://kiro.dev/changelog/",
        "category": "sdd-mode",
        "keywords": [],
        "strate": 4,
    },
    {
        "id": "github-speckit",
        "name": "GitHub Spec Kit — Releases",
        "type": "github_releases",
        "url": "https://api.github.com/repos/github/spec-kit/releases",
        "category": "sdd-mode",
        "keywords": [],
        "strate": 4,
    },
    {
        "id": "mcp-spec",
        "name": "Model Context Protocol — Spec & Updates",
        "type": "github_releases",
        "url": "https://api.github.com/repos/modelcontextprotocol/specification/releases",
        "category": "écosystème",
        "keywords": [],
        "strate": 4,
    },
    {
        "id": "openai-blog",
        "name": "OpenAI — Blog",
        "type": "rss",
        "url": "https://openai.com/blog/rss.xml",
        "category": "écosystème",
        "keywords": ["agent", "codex", "spec", "coding", "agentic"],
        "strate": 4,
    },

    # ── Strate 5 — Recherche (signal avancé) ─────────────────────────────────
    {
        "id": "arxiv-cs-ai",
        "name": "arXiv — cs.AI (Agents & Software Engineering)",
        "type": "rss",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "category": "framework",
        "keywords": [
            "agent", "specification", "software engineering",
            "context", "spec-driven", "llm agent",
        ],
        "strate": 5,
    },
    {
        "id": "arxiv-cs-se",
        "name": "arXiv — cs.SE (Software Engineering)",
        "type": "rss",
        "url": "https://rss.arxiv.org/rss/cs.SE",
        "category": "sdd-mode",
        "keywords": ["agent", "specification", "llm", "code generation", "context"],
        "strate": 5,
    },
    {
        "id": "huggingface-papers",
        "name": "Hugging Face — Daily Papers",
        "type": "rss",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "écosystème",
        "keywords": ["agent", "coding", "specification", "context", "software"],
        "strate": 5,
    },

    # ── Strate 6 — Communautés (signaux faibles) ─────────────────────────────
    {
        "id": "hackernews",
        "name": "Hacker News — Front Page",
        "type": "rss",
        "url": "https://news.ycombinator.com/rss",
        "category": "écosystème",
        "keywords": [
            "spec-driven", "sdd", "agentic", "claude code", "cursor",
            "specification", "context engineering", "kiro", "mcp",
        ],
        "strate": 6,
    },
    {
        "id": "reddit-claudeai",
        "name": "Reddit — r/ClaudeAI",
        "type": "rss",
        "url": "https://www.reddit.com/r/ClaudeAI/.rss",
        "category": "écosystème",
        "keywords": ["spec", "agent", "workflow", "coding", "context"],
        "strate": 6,
    },
    {
        "id": "reddit-experienced-devs",
        "name": "Reddit — r/ExperiencedDevs",
        "type": "rss",
        "url": "https://www.reddit.com/r/ExperiencedDevs/.rss",
        "category": "framework",
        "keywords": ["ai", "agent", "spec", "specification", "workflow", "agentic"],
        "strate": 6,
    },
    {
        "id": "github-claudecode",
        "name": "GitHub — Claude Code Releases",
        "type": "github_releases",
        "url": "https://api.github.com/repos/anthropics/claude-code/releases",
        "category": "écosystème",
        "keywords": [],
        "strate": 6,
    },

    # ── Strate 7 — Écosystème FR & Gouvernance (signal local) ────────────────
    {
        "id": "cnil-blog",
        "name": "CNIL — Blog (RGPD & IA)",
        "type": "rss",
        "url": "https://www.cnil.fr/fr/rss.xml",
        "category": "gouvernance",
        "keywords": ["ia", "intelligence artificielle", "rgpd", "ai act", "données"],
        "strate": 7,
    },
    {
        "id": "eu-aiact",
        "name": "EU AI Act — Tracker",
        "type": "web",
        "url": "https://artificialintelligenceact.eu/",
        "category": "gouvernance",
        "keywords": ["ai act", "regulation", "compliance", "high-risk", "omnibus"],
        "strate": 7,
    },
    {
        "id": "infoq-fr",
        "name": "InfoQ France",
        "type": "rss",
        "url": "https://www.infoq.com/fr/feed/",
        "category": "framework",
        "keywords": ["agent", "ia", "spécification", "architecture", "agilité"],
        "strate": 7,
    },

    # ── Strate 8 — Voix longues (signal philosophique) ───────────────────────
    {
        "id": "kent-beck",
        "name": "Kent Beck — Substack",
        "type": "rss",
        "url": "https://tidyfirst.substack.com/feed",
        "category": "constitution",
        "keywords": ["ai", "agent", "human", "software", "design", "intent"],
        "strate": 8,
    },
    {
        "id": "pluralistic",
        "name": "Cory Doctorow — Pluralistic",
        "type": "rss",
        "url": "https://pluralistic.net/feed/",
        "category": "constitution",
        "keywords": ["ai", "tech", "governance", "human", "autonomy"],
        "strate": 8,
    },
    {
        "id": "thoughtworks-radar",
        "name": "ThoughtWorks — Technology Radar",
        "type": "web",
        "url": "https://www.thoughtworks.com/radar",
        "category": "sdd-mode",
        "keywords": ["specification", "agent", "ai", "adopt", "trial"],
        "strate": 8,
    },
]

SIGNAL_ANALYSIS_PROMPT = """Analyse cet article/publication et détermine s'il constitue un signal pertinent pour le framework AIAD.

AIAD est un meta-framework pour le développement produit à l'ère des agents IA.
Il s'intéresse à : SDD (Spec-Driven Development), governance IA, context engineering,
outils agentiques (Kiro, Tessl, Spec Kit), conformité (AI Act, RGPD), pratiques terrain.

**Article** :
Titre : {title}
Source : {source}
Date : {date}
Contenu : {content}

Réponds en JSON strict :
{{
  "is_relevant": true/false,
  "summary": "1-2 phrases résumant le signal si pertinent",
  "category": "framework|sdd-mode|gouvernance|écosystème|communauté|constitution",
  "detail": "description complète du signal (3-5 phrases)"
}}

Si non pertinent, retourne seulement {{"is_relevant": false}}.
"""


def _next_signal_id() -> str:
    today = date.today().strftime("%Y-%m-%d")
    SIGNALS_INBOX.mkdir(parents=True, exist_ok=True)
    existing = list(SIGNALS_INBOX.glob(f"SIG-{today}-*.md"))
    # Compter aussi les scored pour ce jour
    from ..config import SIGNALS_SCORED
    if SIGNALS_SCORED.exists():
        existing += list(SIGNALS_SCORED.glob(f"SIG-{today}-*.md"))
    idx = len(existing) + 1
    return f"SIG-{today}-{idx:03d}"


def _write_signal(sig_id: str, source: dict, title: str, url: str, analysis: dict) -> Path:
    SIGNALS_INBOX.mkdir(parents=True, exist_ok=True)
    path = SIGNALS_INBOX / f"{sig_id}.md"

    content = f"""# Signal ALIS

## Identifiant
{sig_id}

## Source
- **Type** : externe
- **Origine** : veille web
- **URL / Référence** : {url}

## Signal
**Résumé** : {analysis['summary']}

**Détail** : {analysis['detail']}

## Catégorie
{analysis['category']}

## Date de captation
{date.today().strftime('%Y-%m-%d')}

## Scoring (rempli automatiquement en Couche 2)
| Dimension | Score (1-5) | Justification |
|-----------|-------------|---------------|
| Fréquence | | |
| Impact | | |
| Urgence | | |
| Complexité (inversé) | | |
| **Score total** | **/20** | |

## Seuil de passage en hypothèse : ≥ 12/20
"""
    path.write_text(content, encoding="utf-8")
    return path


def _fetch_rss(source: dict) -> list[dict]:
    """Récupère les dernières entrées d'un flux RSS."""
    try:
        feed = feedparser.parse(source["url"])
        items = []
        keywords = [k.lower() for k in source.get("keywords", [])]
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            content = entry.get("summary", entry.get("content", [{}])[0].get("value", ""))
            link = entry.get("link", "")
            # Filtre par mots-clés si définis
            if keywords:
                text = (title + " " + content).lower()
                if not any(k in text for k in keywords):
                    continue
            items.append({"title": title, "content": content[:2000], "url": link})
        return items
    except Exception as e:
        console.print(f"[yellow]RSS {source['name']} : {e}[/yellow]")
        return []


def _fetch_github_releases(source: dict) -> list[dict]:
    """Récupère les dernières releases GitHub."""
    try:
        resp = httpx.get(source["url"], timeout=10, headers={"User-Agent": "alis-bot/1.0"})
        releases = resp.json()
        return [
            {
                "title": f"{source['name']} — {r['name'] or r['tag_name']}",
                "content": r.get("body", "")[:2000],
                "url": r.get("html_url", ""),
            }
            for r in releases[:5]
        ]
    except Exception as e:
        console.print(f"[yellow]GitHub {source['name']} : {e}[/yellow]")
        return []


def _fetch_web(source: dict) -> list[dict]:
    """Scrape une page web pour trouver des articles récents."""
    try:
        resp = httpx.get(source["url"], timeout=15, headers={"User-Agent": "alis-bot/1.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        keywords = [k.lower() for k in source.get("keywords", [])]
        for a in soup.find_all("a", href=True)[:30]:
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            if keywords and not any(k in title.lower() for k in keywords):
                continue
            href = a["href"]
            if not href.startswith("http"):
                href = source["url"].rstrip("/") + "/" + href.lstrip("/")
            items.append({"title": title, "content": "", "url": href})
        return items[:10]
    except Exception as e:
        console.print(f"[yellow]Web {source['name']} : {e}[/yellow]")
        return []


def _analyse_with_claude(
    client: anthropic.Anthropic, source: dict, item: dict
) -> dict | None:
    """Détermine si un article est un signal ALIS pertinent."""
    import json

    prompt = SIGNAL_ANALYSIS_PROMPT.format(
        title=item["title"],
        source=source["name"],
        date=date.today().isoformat(),
        content=item["content"][:3000],
    )

    try:
        message = client.messages.create(
            model=ALIS_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        console.print(f"[yellow]Analyse Claude : {e}[/yellow]")
    return None


def _load_extra_sources_from_watchlist() -> list[dict]:
    """Lit WATCHLIST.md pour extraire des URLs supplémentaires à surveiller."""
    if not WATCHLIST.exists():
        return []
    content = WATCHLIST.read_text(encoding="utf-8")
    # Cherche les URLs dans le fichier
    urls = re.findall(r"https?://[^\s\)\"]+", content)
    sources = []
    for url in set(urls):
        # Exclure les URLs génériques
        if any(x in url for x in ["github.com", "fowler", "tessl", "anthropic"]):
            continue
        sources.append(
            {
                "id": f"watchlist-{len(sources)}",
                "name": url.split("/")[2],
                "type": "web",
                "url": url,
                "category": "écosystème",
                "keywords": [],
            }
        )
    return sources[:5]  # Limiter


def run_collect(dry_run: bool = False, sources_override: list[str] | None = None) -> None:
    """Point d'entrée de la commande `alis collect`."""
    if not ANTHROPIC_API_KEY and not dry_run:
        console.print("[red]✗ ANTHROPIC_API_KEY manquant dans .env[/red]")
        return

    sources = DEFAULT_SOURCES + _load_extra_sources_from_watchlist()
    if sources_override:
        sources = [s for s in sources if s["id"] in sources_override]

    console.print(f"[bold]ALIS Collect[/bold] — {len(sources)} sources surveillées")

    if dry_run:
        console.print("[dim]--dry-run : listing des sources[/dim]")
        for s in sources:
            console.print(f"  [{s['type']}] {s['name']} — {s['url']}")
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    total_signals = 0

    for source in sources:
        console.print(f"\n[dim]Collecte : {source['name']}...[/dim]")

        if source["type"] == "rss":
            items = _fetch_rss(source)
        elif source["type"] == "github_releases":
            items = _fetch_github_releases(source)
        else:
            items = _fetch_web(source)

        if not items:
            console.print("  (aucun article)")
            continue

        console.print(f"  {len(items)} articles candidats")

        for item in items:
            analysis = _analyse_with_claude(client, source, item)
            if not analysis or not analysis.get("is_relevant"):
                continue

            sig_id = _next_signal_id()
            path = _write_signal(sig_id, source, item["title"], item["url"], analysis)
            total_signals += 1
            console.print(
                f"  [green]+[/green] {sig_id} : {analysis['summary'][:80]}"
            )

    console.print(
        f"\n[green]✓ {total_signals} signal(s) capté(s) dans signals/inbox/[/green]"
    )
    if total_signals > 0:
        console.print("Lance [bold]alis score[/bold] pour analyser et scorer les signaux.")
