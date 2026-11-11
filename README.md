# Fieldnote Markets

Application indépendante d’analyse éducative du marché des changes, écrite pour ce portfolio avec une identité visuelle propre. Elle récupère des cours indicatifs depuis Yahoo Finance, calcule des indicateurs explicites sur des bougies OHLC, fait coopérer un analyste technique déterministe, un contrôleur de risque déterministe et un superviseur Groq, puis propose un backtest chronologique hors échantillon d’une stratégie SMA. Elle n’exécute aucun ordre.

## Lancer en local

Python 3.11 ou supérieur est nécessaire.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Ouvre `.env`, ajoute **une clé Groq nouvellement créée**, puis démarre le serveur.

```powershell
uvicorn main:app --reload
```

Visite <http://127.0.0.1:8000>. La liste inclut 14 paires majeures et crosses G10. Choisis D1, H4, H1 ou M15. Le bureau calcule SMA/EMA, RSI, MACD, bandes de Bollinger, ATR, ADX/+DI/-DI, stochastique, CCI, Williams %R, OBV, Ichimoku, pivots et retracements de Fibonacci. Les calculs utilisent l’historique de prix OHLC reçu.

Le chat garde jusqu’à 40 messages dans `sessionStorage` pour l’onglet courant; l’API ne reçoit que les 12 derniers messages. Le bouton ↺ ouvre une nouvelle conversation. Le bouton de thème change toute l’interface entre clair et sombre. Entrée envoie le message; Maj+Entrée ajoute une nouvelle ligne.

## Agents et backtest

`agents/technical.py` produit un biais descriptif à partir des EMA, RSI, MACD et ADX calculés localement. `agents/risk.py` signale l’amplitude relative à l’ATR et les limites de données; il ne calcule aucune taille de position sans capital, stop, devise du compte et règles courtier. `agents/news_data.py` récupère des titres Yahoo Finance en conservant éditeur, date et URL; `agents/news_sentiment.py` classe seulement les titres récupérés et n’accepte que des références à leurs identifiants. `agents/macro_data.py` lit les dernières séries de taux FRED disponibles pour les deux devises et marque les observations anciennes. `agents/retrieval.py` applique une recherche lexicale BM25 sur une petite base de références pédagogiques; le chatbot reçoit les extraits et l’interface montre les liens réellement récupérés. `agents/team.py` rassemble les rapports avant la synthèse Groq. Les pannes de sources sont renvoyées comme états « indisponible » et ne sont pas transformées en faits.

Le bouton **Tester la stratégie** exécute un croisement SMA 10/30 avec signaux de clôture appliqués à la bougie suivante, séparation chronologique 70/30 et coût de spread configurable par défaut à 1 pip. Il rapporte le rendement net simulé, le drawdown maximal, le Sharpe annualisé, le nombre de changements de position et un benchmark achat/conservation. C’est une démonstration de recherche reproductible, pas une preuve de rentabilité : glissement, gaps, financement, exécution courtier et sélection de paramètres ne sont pas modélisés.

### Étapes de recherche pour le portfolio

1. Agents technique et risque + stratégie SMA et backtest hors échantillon (implémentés).
2. Ingestion d’actualités sourcées, classification du sentiment avec références aux titres et horodatages (implémentées).
3. Séries de taux macro FRED, fraîcheur et valeurs manquantes visibles (implémentées; définitions et fréquences diffèrent selon la devise).
4. Évaluation par modèle et version de prompt sur un jeu forex (script implémenté; à exécuter avec une clé Groq fraîche pour produire les résultats).

Le benchmark se lance avec `GROQ_API_KEY`, `FIELDNOTE_BENCHMARK_MODELS` (modèles séparés par des virgules) et le serveur local démarré, puis `python scripts/benchmark_models.py`. Il compare chaque modèle sur les mêmes cas et instantanés, vérifie les concepts requis et les affirmations interdites, mesure la latence et écrit un rapport JSON non versionné dans `evals/results/`. Les tests automatiques utilisent des réponses simulées et ne consomment pas de quota Groq.

La base RAG inclut des références pédagogiques citées de OANDA, Fidelity, BIS et CFTC. Le retriever est lexical BM25, pas un magasin d’embeddings ni une architecture de fine-tuning. Le fine-tuning reste une piste de recherche : il faudrait d’abord collecter et annoter un jeu d’entraînement propre, puis le comparer au modèle de base sur les évaluations hors échantillon.

## Vérifications et évaluation

```powershell
python -m compileall -q main.py agents research tests scripts
python -m unittest discover -s tests -v
```

La suite est sans clé API et simule la réponse Groq pour tester le contexte FX, les erreurs fournisseur, les limites d’historique, les identifiants de requête, les garde-fous et les calculs d’indicateurs. Pour lancer les scénarios de qualité sur un serveur configuré, démarre l’application puis exécute `python scripts/run_chat_eval.py`. Cette évaluation appelle le modèle et peut consommer les quotas configurés.

Le graphique TradingView suit la paire et l’horizon sélectionnés, avec RSI, MACD et ADX ajoutés par défaut. La barre d’outils du graphique permet d’afficher d’autres études et outils de tracé.

## Flux TradingView et calculs de l’application

Le graphique intégré utilise le widget officiel TradingView avec le flux forex OANDA. TradingView indique que les cotations forex de ses widgets sont en temps réel. Le widget reste hébergé par TradingView et s’actualise dans la page quand la paire ou l’horizon change. [Documentation du graphique TradingView](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/) · [Disponibilité des données des widgets](https://www.tradingview.com/widget-docs/faq/data/)

Les cartes de cours, les 37 indicateurs calculés par Fieldnote et le contexte envoyé à Groq continuent d’utiliser l’instantané Yahoo Finance. Ces valeurs peuvent différer du flux OANDA du graphique. TradingView ne permet pas d’exporter les données de ses widgets ni de lire leurs indicateurs via une API publique; obtenir un flux unique en temps réel pour le graphique, les cartes et l’assistant demanderait un fournisseur de données avec une API adaptée. [FAQ données TradingView](https://www.tradingview.com/widget-docs/faq/data/)

## Publier gratuitement sur Render

1. Crée un dépôt GitHub public pour ce nouveau projet et pousse les fichiers de ce dossier.
2. Dans Render, crée un Blueprint à partir de ce dépôt. Le fichier `render.yaml` décrit le service.
3. Dans la configuration du service, ajoute `GROQ_API_KEY` comme variable secrète. Ajoute une clé fraîche dans Render, jamais dans GitHub.
4. Render construira le site et affichera une adresse `onrender.com`.

Render Free suspend un service Web après 15 minutes sans trafic et son stockage local est éphémère. Le premier visiteur après la veille peut donc attendre environ une minute. Fieldnote garde l’historique utilisateur dans le navigateur et le service n’enregistre pas les clés API. [Limites Render Free](https://render.com/docs/free)

## Architecture

- `static/` contient l’interface française responsive, le graphique TradingView intégré, un graphique SVG de secours et le rendu des états.
- `main.py` sert le site, expose les cotations D1/H4/H1/M15, calcule les indicateurs FX sur les bougies OHLC et appelle Groq côté serveur.
- `/api/health` confirme la présence de la configuration, sans renvoyer la clé.
- `/api/analyze` valide le symbole, récupère l’instantané Yahoo et renvoie une analyse structurée.
- `GROQ_MODEL` peut remplacer le modèle par défaut. L’analyse demande une réponse JSON et accepte aussi les blocs JSON entourés de balises Markdown.
- `/api/pairs` expose les 14 paires suivies et `/api/chat` alimente le tuteur FX avec l’instantané de marché sélectionné.

Groq utilise son endpoint de complétion compatible OpenAI. La clé reste dans les variables d’environnement serveur. L’assistant reçoit le dernier instantané de la paire et les derniers messages de conversation. [Référence API Groq](https://console.groq.com/docs/api-reference)

## Exploitation IA

Chaque réponse est marquée `fx-chat-v2`. Les journaux structurés consignent modèle, version du prompt, paire, horizon, latence, longueur de la réponse et identifiant de requête; ils n’enregistrent ni clé API ni texte des conversations. Les appels Groq réutilisent un client HTTP avec délai maximal et une relance courte sur erreurs transitoires. Les réponses trop courtes ou invalides sont rejetées, et l’interface propose une relance sans dupliquer le message.

Le service limite les routes IA à 12 requêtes par minute et par adresse cliente, avec `Retry-After` en cas de dépassement. Cette limite est en mémoire et s’applique à une instance. Une architecture multi-instance doit déplacer ce compteur dans un stockage partagé et ajouter des alertes basées sur les journaux.

## Sécurité et limites

Les sorties affichées sont générées par un modèle et ne constituent pas un conseil financier. Aucune IA ne peut garantir une réponse parfaite; vérifie les sources et les horaires avant toute décision. Le forex de gré à gré comporte des risques de levier et de pertes importantes. Les cotations Yahoo sont indicatives, peuvent être retardées et ne reflètent pas nécessairement un flux négociable chez un courtier. Les marchés spot FX n’ont pas de volume centralisé, l’OBV présenté utilise le proxy de volume fourni par Yahoo. L’application n’exécute aucune transaction et n’expose aucune clé au navigateur. Avant publication, régénère toute clé précédemment partagée et publie une politique de confidentialité adaptée à l’audience. [Avis de la CFTC sur le forex](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html)

Ce projet est une réécriture indépendante qui reprend l’idée générale de recherche multi-agents de TradingAgents. Le dépôt amont et son code sont sous licence Apache-2.0. [TradingAgents](https://github.com/TauricResearch/TradingAgents)

Interface créée avec la méthode Unslop de Damir Sokolovsky, licence CC BY 4.0.
