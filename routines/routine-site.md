# Routine — Alignement du site aiad.ovh et du package aiad-sdd sur la doctrine {{FRAMEWORK_VERSION}}

Tu travailles dans le dépôt public `everssteeve/sdd-mode` (répertoire courant : `{{SDD_REPO}}`, branche `main`, à jour avec `origin/main`). Ce dépôt contient le package npm `aiad-sdd` et, dans `site/`, le site statique bilingue publié sur aiad.ovh. La session est lancée par un script et **non interactive** : personne ne répondra à une question.

## Mandat

La doctrine AIAD vient de passer de {{PREVIOUS_FRAMEWORK_VERSION}} à **{{FRAMEWORK_VERSION}}**. Le mainteneur (Steeve Evers) a donné un accord permanent pour que le site et le package soient alignés et publiés automatiquement à chaque montée de doctrine. Ta part : aligner le contenu et **committer en local**. Le script qui t'a lancé fait ensuite, seul : le bump de version, le tag, le `git push`, la publication npm et le déploiement du site.

**Tu ne fais donc pas** : `git push`, `git tag`, bump de `package.json`, `npm publish`, modification des zones `<!--VERSION:START-->…<!--VERSION:END-->`, de `site/CNAME`, des workflows `.github/`.

## Ce qui est déjà fait

Le script a lancé `node scripts/sync-doctrine.js` : les 14 fichiers de doctrine livrés (agents de gouvernance, `templates/frameworkAIAD.md`, `templates/SDDMode.md`, `docs/legitimation/`), `templates/doctrine.lock.json` et les règles émises sont à jour dans l'arbre de travail, **non committés**. `git status` et `git diff` te montrent ce que la doctrine a changé.

## Entrées

- Résumé de la montée de doctrine : `{{IMPLEMENT_RESULT}}` (JSON : `public_changes`, `software_changes`, `summary`)
- Doctrine publiée (source de vérité, lecture seule) : `{{DOCTRINE_SOURCE}}`
- Fichier de résultat à écrire en dernier : `{{RESULT_FILE}}`

## Règles du dépôt

- Dépôt **public** : aucune mention d'un processus interne, aucun identifiant interne (`HYP-…`, `SIG-…`), aucun nom de client. Décris les changements par leur contenu.
- Lis `CLAUDE.md` et `AGENTS.md` du dépôt et respecte-les. Commits conventionnels **en anglais**, indexés nommément (`git add <fichiers>`, jamais `git add -A` ni `git add .`).
- Site : accessibilité RGAA / WCAG 2.1 AA (gate pa11y bloquant), sobriété RGESN (budgets de page), parité stricte **FR / EN** (toute page modifiée dans `site/fr/` l'est dans `site/en/`, et inversement).
- N'affirme sur le site que ce que la doctrine publiée dit. Pas de chiffre ni de fait absent de `{{DOCTRINE_SOURCE}}`.

## Étapes

### 1 — Comprendre le delta
Lis le résumé, puis `git diff` sur `templates/frameworkAIAD.md`, `templates/SDDMode.md` et les agents de gouvernance. Dresse la liste des changements de doctrine visibles pour un praticien.

### 2 — Committer la doctrine synchronisée
Vérifie `node scripts/check-doctrine.js`, puis committe les fichiers produits par la synchronisation (indexés nommément) : `feat(doctrine): sync shipped doctrine {{FRAMEWORK_VERSION}}`.

### 3 — Aligner le site
- Remplace partout dans `site/` le libellé « Doctrine AIAD {{PREVIOUS_FRAMEWORK_VERSION}} » (et son équivalent anglais) par {{FRAMEWORK_VERSION}}. Vérifie par recherche qu'il ne reste aucune occurrence de l'ancienne version présentée comme courante (les mentions historiques restent).
- Mets à jour les pages dont le contenu est touché par le delta (concepts, gouvernance, glossaire, métriques, équipe…), en FR et en EN.
- Ajoute l'entrée de cette version dans `site/fr/nouveautes.html` et `site/en/whats-new.html`, sur le modèle des entrées existantes.
- Mets à jour `site/fr/search-index.json` et `site/en/search-index.json` pour tout contenu ajouté ou modifié (JSON sur une ligne : conserve exactement le format existant, et valide-le avec `node -e "JSON.parse(require('fs').readFileSync(p,'utf8'))"`).
- Commit : `docs(site): align the public site on AIAD doctrine {{FRAMEWORK_VERSION}}`.

### 4 — Aligner le package
- Si le delta de doctrine change le texte d'une commande ou d'un template livré (`templates/`, `.claude/commands/`), reporte-le en respectant les contrôles de parité du dépôt. Commit : `feat(templates): …` ou `docs(commands): …`.
- Une évolution **logicielle** listée dans `software_changes` (nouveau comportement dans `lib/` ou `bin/`) ne s'improvise pas ici : elle suit le cycle Intent → SPEC → Gate du dépôt. Pour chacune, ouvre une issue GitHub neutre et autoportante (`gh issue create --repo everssteeve/sdd-mode --label enhancement`), sauf si une issue ouverte la couvre déjà (`gh issue list --search`). N'implémente pas.

### 5 — Vérifier
Tout doit passer avant de finir :

```bash
npm run lint
npm test
node scripts/check-doctrine.js
node bin/aiad-sdd.js emit-rules --check
node scripts/check-page-budgets.js        # si présent
mapfile -t URLS < <(find site -name "*.html" -type f | sort | sed "s|^|file://$(pwd)/|") && npx pa11y-ci --config .pa11yci.json "${URLS[@]}"
```

(Sous zsh, remplace `mapfile` par une boucle équivalente.) Corrige ce qui échoue. Deux particularités connues de la suite : elle laisse quelques fichiers supprimés sous `bench/` (restaure-les avec `git restore bench`, ne les committe pas), et un test peut échouer isolément sous forte concurrence — relance la suite une fois avant d'enquêter, et ne modifie jamais un test sans rapport avec tes changements. `docs --check` et `version-sync --check` peuvent rester en écart : le script régénère ces fichiers au moment du bump.

### 6 — Finir proprement
`git status --porcelain` doit être vide (tout est committé, rien de non suivi). Écris ensuite `{{RESULT_FILE}}` (JSON strict) :

```json
{
  "status": "ok",
  "framework_version": "{{FRAMEWORK_VERSION}}",
  "commits": ["<sha court> <sujet>"],
  "pages_updated": ["site/fr/…", "site/en/…"],
  "issues_opened": ["https://github.com/everssteeve/sdd-mode/issues/…"],
  "checks": {"lint": "pass", "test": "pass", "doctrine": "pass", "pa11y": "pass"},
  "summary": "2-4 phrases"
}
```

## En cas de blocage

Ne pose pas de question. Si un contrôle reste en échec ou si tu ne peux pas terminer, n'essaie pas de contourner un gate (pas d'allowlist pa11y, pas de test désactivé) : écris le fichier de résultat avec `"status": "failed"` et un champ `"reason"` précis, puis arrête-toi. Le script ne publiera rien.
