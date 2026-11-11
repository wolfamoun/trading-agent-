# Fieldnote FX — alignement CV / code

État vérifié le 11 novembre 2026. Utiliser les formulations « construit », « implémenté » ou « évalué » uniquement quand la capacité correspondante est présente dans le dépôt et testée.

## Ce que le projet démontre actuellement

- **Architecture hybride d’agents spécialisés** : lecture technique et contrôle du risque fondés sur des règles explicites; agent LLM de sentiment limité aux titres récupérés; superviseur LLM qui synthétise les rapports. Les rôles peuvent s’exécuter indépendamment sur le même instantané et leurs états sont renvoyés par `/api/analyze`.
- **Modélisation FX** : 37 indicateurs calculés à partir de bougies OHLC; contexte macro de taux par devise avec source, date et avertissement de fraîcheur; actualités attribuées à un éditeur et une URL.
- **Recherche quantitative** : backtest SMA 10/30 avec signal de clôture appliqué à la bougie suivante, spread hypothétique, holdout chronologique 70/30, rendement, drawdown, Sharpe, fréquence positive, profit factor et benchmark achat/conservation.
- **RAG pédagogique** : corpus versionné de quatre références, recherche lexicale BM25, citations récupérées et liens visibles dans le chatbot.
- **Évaluation / MLOps léger** : version du prompt, cas d’évaluation, assertions de sécurité, mesure de latence et outil de comparaison Groq multi-modèle. Les tests automatiques sont hors ligne; un benchmark réel exige une clé renouvelée et coûte des appels API.
- **Pipeline de données à la demande** : récupération de cours Yahoo, titres Yahoo Finance Search et taux FRED; nettoyage, provenance, contrôles OHLC, valeurs manquantes et états d’erreur explicites.

## Formulation CV défendable maintenant

**Fieldnote FX — Recherche financière et analyse forex assistée par IA | Projet personnel, 2025–2026**

- Conçu une architecture hybride d’agents spécialisés en analyse technique, risque, sentiment des actualités et synthèse supervisée par LLM.
- Développé un pipeline Python d’ingestion et validation de cours OHLC, de titres financiers sourcés et de séries macroéconomiques FRED, avec horodatages et contrôle de fraîcheur.
- Calculé 37 indicateurs forex et créé un backtest SMA 10/30 à holdout chronologique 70/30, coûts de spread paramétrés et métriques de risque.
- Intégré un chatbot forex avec RAG lexical BM25 et citations, ainsi qu’un banc d’évaluation multi-modèle mesurant concepts requis, affirmations non étayées et latence.

## Ne pas annoncer comme terminé

- **Exécution de trades en direct** : aucune connexion broker ni aucun ordre n’existe. Le backtest est une simulation historique.
- **Flux unifié en temps réel** : le graphique TradingView/OANDA et les indicateurs Yahoo utilisent deux flux distincts. Le pipeline Yahoo/FRED/news s’actualise à la demande, pas en streaming.
- **Fine-tuning** : aucun modèle n’a été entraîné ou ajusté. Le projet comprend de la veille, du RAG et un benchmark; le fine-tuning reste une piste de recherche faute de corpus annoté et de résultats comparatifs.
- **Performance validée** : l’implémentation du backtest et ses contrôles sont testés sur données synthétiques. Il faut encore faire un rapport sur données historiques horodatées, sensibilité au spread, période walk-forward supplémentaire et comparaison hors échantillon avant toute affirmation sur la stratégie.
- **Déploiement public et base utilisateurs** : aucun compte, authentification ou base serveur n’est configuré. L’historique du chat reste dans `sessionStorage`.

## Étapes pour le défendre en entretien

1. Montrer `/api/analyze` et expliquer la donnée fournie à chacun des spécialistes.
2. Ouvrir les liens news et les dates FRED; expliquer qu’une série ancienne ou une source indisponible ne devient pas une affirmation.
3. Lancer le backtest, expliquer le décalage signal→bougie suivante, le holdout et les hypothèses de frais.
4. Montrer la recherche BM25, les documents récupérés et la citation dans le chat.
5. Exécuter `scripts/benchmark_models.py` avec deux modèles disponibles; comparer le même jeu de cas et examiner les échecs avant de choisir un modèle.
6. Présenter le fine-tuning comme une expérimentation future fondée sur des données annotées, jamais comme un modèle déjà entraîné.
