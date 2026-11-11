# Guide de maîtrise de Fieldnote FX

## 1. Démarrer et vérifier le bureau

Depuis la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Ajoute une clé Groq fraîche dans `.env`, puis lance `uvicorn main:app --reload` et ouvre `http://127.0.0.1:8000`. L’endpoint `/api/health` indique si l’IA est configurée. Ne publie jamais `.env`.

## 2. Comprendre la chaîne de données

1. Le navigateur demande une paire et un horizon à `/api/market/{ticker}`.
2. `market_snapshot` récupère les bougies Yahoo Finance, supprime les points OHLC incohérents, vérifie les nombres et calcule les 37 indicateurs.
3. L’application affiche l’horodatage et la source. Yahoo est indicatif; les cotations TradingView/OANDA viennent d’un autre flux.
4. Quand tu lances **Lire le marché**, `/api/analyze` récupère les actualités Yahoo et les dernières séries de taux FRED pour les devises concernées. La fraîcheur et la disponibilité restent visibles dans le rapport des agents.

À retenir en entretien : le pipeline est à la demande et se relance lorsqu’on actualise/analyse. Il n’utilise ni WebSocket de prix de courtier ni flux consolidé du marché spot.

## 3. Expliquer le système d’agents

Dans `agents/team.py`, les rapports sont assemblés sous une version d’architecture.

- `technical.py` produit un score explicite à partir des EMA, RSI, MACD et ADX.
- `risk.py` décrit l’amplitude relative à l’ATR et expose les données manquantes. Il ne prétend pas connaître le capital, le levier, le stop ou le courtier d’un utilisateur.
- `news_sentiment.py` demande au modèle de classifier les titres récupérés. Il n’accepte que des identifiants présents dans le flux et retombe sur « indéterminé » si la réponse ne respecte pas le schéma.
- `macro_data.py` attribue une observation FRED à chaque devise et marque les valeurs anciennes. Les séries ont des fréquences et des définitions différentes; ce ne sont pas des décisions de politique monétaire parfaitement comparables.
- Le superviseur LLM synthétise l’instantané et les rapports. Les calculs de tendance et de risque sont des règles vérifiables, pas des décisions cachées du modèle.

Ouvre `POST /api/analyze` dans la documentation OpenAPI (`/docs`) pour voir le contrat de réponse et `agent_team`.

## 4. Comprendre le backtest

Le bouton **Tester la stratégie** appelle `POST /api/backtest`. La règle compare SMA 10 et SMA 30; le signal observé à la clôture ne s’applique qu’à la bougie suivante, ce qui limite le look-ahead. Les 70 % premiers points définissent la période de calibration fixe et les 30 % finaux forment le holdout chronologique.

- Rendement net : rendement composé après le coût de spread simplifié.
- Drawdown maximal : plus forte baisse depuis un sommet d’equity simulée.
- Sharpe annualisé : moyenne des rendements par période divisée par leur volatilité, annualisée selon l’horizon.
- Référence : acheter et conserver sur le même holdout, avec un coût d’entrée simulé.

Ce petit backtest sert à expliquer la méthodologie. Il n’inclut pas le slippage variable, les gaps, le financement overnight ou les règles d’exécution d’un courtier. Avant d’affirmer une performance, ajoute plusieurs périodes walk-forward, des tests de sensibilité aux frais et des données historiques propres.

## 5. Expliquer le RAG et le chatbot

`agents/retrieval.py` recherche les termes de la question dans quatre documents éducatifs avec BM25 lexical. Les passages sélectionnés sont joints au contexte du modèle et les URL correspondantes sont affichées dans la réponse.

RAG signifie que le modèle reçoit des documents retrouvés au moment de la question. Cela aide à répondre avec des sources, mais ne garantit pas la vérité. Ici, il s’agit d’un petit corpus lexical, pas d’une base vectorielle ni d’un corpus exhaustif. Les messages restent dans `sessionStorage` pour la session; aucune base serveur ni authentification n’est configurée.

## 6. Évaluer les modèles

Les tests hors ligne :

```powershell
python -m compileall -q main.py agents research tests scripts
python -m unittest discover -s tests -v
node --check static/app.js
```

Pour le benchmark réel, démarre l’application et configure localement une nouvelle clé Groq ainsi que `FIELDNOTE_BENCHMARK_MODELS` avec deux modèles disponibles, séparés par des virgules. Exécute `python scripts/benchmark_models.py`. Le script réutilise les mêmes cas et instantanés, mesure la latence, vérifie les concepts attendus et exclut quelques formulations dangereuses, puis écrit un rapport dans `evals/results/`.

Ce score ne juge pas toute la qualité financière du modèle. Lis chaque réponse ratée, ajoute un cas ciblé, garde une version de prompt fixe et compare les modèles avant d’en changer.

## 7. Où placer le fine-tuning

Le fine-tuning n’est pas implémenté. Pour le justifier, il faudrait une collection de dialogues FX de qualité, des annotations cohérentes, des données séparées entre entraînement et évaluation et un gain mesuré par rapport au prompt/RAG. Sans cela, le RAG sourcé est plus facile à mettre à jour et à contrôler. Vérifie aussi que le fournisseur choisi permet effectivement d’entraîner le modèle ciblé.

## Démonstration portfolio en cinq minutes

1. Choisis EUR/USD et affiche RSI, ATR, ADX, source et horodatage.
2. Lance l’analyse; montre les rôles technique, risque, sentiment et macro, y compris toute donnée marquée ancienne ou indisponible.
3. Ouvre un lien de titre et distingue le fait cité de l’interprétation générée.
4. Lance le backtest et explique holdout, décalage à la bougie suivante et coûts simplifiés.
5. Pose une question sur les pips ou l’ADX au chat et montre le lien pédagogique récupéré.
6. Présente le fine-tuning et le trading direct comme des travaux futurs, pas comme des fonctions livrées.
