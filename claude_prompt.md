# Brief projet — Assistant de compréhension de documents administratifs et médicaux

Tu es mon binôme de développement sur ce projet. Lis ce brief en entier avant d'écrire la
moindre ligne de code, puis propose-moi un plan avant de commencer.

---

## 1. Contexte

Projet intégrateur de 5e année en ingénierie IA et data, matière « IA générative et
textuelle ». Je suis **seul**, j'ai **quatre semaines** (du 16 novembre au 14 décembre 2026),
et je serai noté sur un rendu en quatre étapes avec soutenance.

Le sujet impose une progression en quatre incréments d'**une seule et même application**,
pas quatre projets séparés :

| Étape | Contenu | Poids |
| --- | --- | --- |
| 1 | Socle documentaire et RAG textuel | 20 % |
| 2 | Multimodalité (VLM) et fine-tuning d'un reranker | 30 % |
| 3 | Orchestration agentique (LangGraph) et serveur MCP | 30 % |
| 4 | Client web complet, sécurité, déploiement Docker | 20 % |

À chaque jalon : code versionné, README, procédure d'exécution, tests, démonstration.

---

## 2. Ce que fait le produit

Une personne reçoit un courrier administratif, un contrat ou une ordonnance qu'elle ne
comprend pas. Elle le colle en texte ou le prend en photo. Le système :

1. **lit** le document (PDF, image, texte) ;
2. **explique** son contenu en phrases courtes, en français simple, en arabe ou en darija ;
3. **liste les actions** à faire et **les dates limites** ;
4. **définit les mots difficiles**, en citant un corpus de référence ;
5. **répond aux questions** portant sur ce document, et seulement sur lui ;
6. **propose un rappel** pour une échéance, créé uniquement après accord explicite.

---

## 3. Contraintes non négociables

Ces quatre règles définissent le projet. Chacune doit être **testée automatiquement**, pas
seulement écrite dans un prompt. Si une décision technique les met en danger, arrête-toi et
préviens-moi.

- **Ne rien inventer.** Chaque affirmation de l'explication doit se rattacher à un passage du
  document fourni ou du corpus de référence. Ce qui n'y figure pas devient une incertitude
  déclarée dans la sortie, jamais une supposition.
- **Ne pas conseiller.** Aucun diagnostic médical, aucune stratégie juridique, aucune
  recommandation de traitement. Le système explique ce qui est écrit et renvoie vers un
  médecin, un pharmacien ou un juriste.
- **Ne pas agir seul.** Aucune écriture, aucun rappel, aucun envoi sans validation humaine
  portant sur le contenu exact, liée à l'utilisateur, et idempotente.
- **Ne pas conserver.** Documents effacés en fin de session ; données personnelles masquées
  avant toute journalisation.

---

## 4. Architecture visée

```
Client         Streamlit (web)
API            FastAPI — identités, sessions, autorisations
Orchestration  LangGraph — graphe d'états, interruption pour validation humaine
Services IA    RAG multimodal  ·  VLM  ·  Outils MCP
Données        Qdrant (vecteurs) · PostgreSQL (métadonnées) · MinIO (fichiers)
Observabilité  MLflow (expériences) · Docker Compose (déploiement)
```

**Pile par défaut**, avec repli si je n'ai pas de GPU de 16 Go :

| Couche | Choix | Repli sans GPU |
| --- | --- | --- |
| Lecture PDF et OCR | PyMuPDF + Tesseract (fra+ara) | OCR délégué au VLM |
| Embeddings | BGE-M3 | multilingual-e5-base |
| Base vectorielle | Qdrant via Docker | Chroma en fichier local |
| Vision-langage | Qwen2.5-VL-7B-Instruct local | API vision |
| Rédaction | Modèle instruct multilingue local | Même API |
| Reranking | bge-reranker-v2-m3 adapté | Aucun, mesuré comme baseline |

Avant d'écrire du code, **demande-moi de quel matériel je dispose** et adapte la pile.

---

## 5. Ce qui fait la différence entre 14 et 19

Le code qui marche ne suffit pas : une démo qui fonctionne est attendue, pas récompensée.
Ce qui fait monter la note, dans cet ordre :

1. **Un protocole d'évaluation chiffré**, construit **dès la semaine 1**, pas à la fin.
2. **Des comparaisons avec et sans** chaque composant, pour prouver que chacun sert.
3. **Une analyse d'erreurs** : les cas où le système échoue, classés par cause.
4. **Les limites assumées et mesurées**, notamment la qualité en darija.
5. **La reproductibilité** : `docker compose up` et tout démarre, chez moi comme chez le prof.

Donc : **construis le harnais d'évaluation avant d'optimiser quoi que ce soit.** À chaque
amélioration proposée, dis-moi quelle métrique elle doit faire bouger et vérifie-le.

### Les métriques à implémenter

- **Fidélité** : part des informations clés du document (dates, montants, actions, noms)
  présentes dans l'explication ; nombre d'informations inventées. Jeu de référence annoté à la
  main par mes soins, 40 documents.
- **Lisibilité** : score avant et après (Flesch adapté au français, longueur moyenne de phrase,
  part de mots hors des 3 000 plus fréquents).
- **Recherche** : nDCG@5 et MRR@10, pour comparer sans reranker, avec reranker initial, avec
  reranker adapté.
- **Sécurité** : taux de blocage sur un jeu d'attaques (injection de prompt cachée dans un
  document, tentative d'accès aux données d'un autre utilisateur, création de rappel sans
  approbation).
- **Refus** : part des demandes de conseil médical ou juridique correctement refusées.
- **Latence** : p50 et p95 de bout en bout.

Toutes ces mesures sont loguées dans MLflow, avec le hash du commit et la version des prompts.

---

## 6. Structure de dépôt attendue

```
.
├── README.md                  # démarrage en moins de 10 minutes
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── evaluation.md          # protocole, résultats, analyse d'erreurs
│   └── limites.md
├── src/
│   ├── ingestion/             # extraction, découpage, métadonnées
│   ├── index/                 # embeddings, Chroma
│   ├── vision/                # Tesseract OCR (pas de VLM)
│   ├── rag/                   # recherche, fusion, reranking
│   ├── agent/                 # graphe LangGraph
│   ├── mcp_server/            # outils MCP + autorisations
│   ├── api/                   # FastAPI
│   ├── ui/                    # Streamlit
│   └── schemas/               # modèles Pydantic
├── prompts/                   # versionnés, un fichier par rôle
├── eval/
│   ├── datasets/              # jeu annoté, jeu d'attaques
│   ├── metrics/
│   └── run_eval.py
└── tests/
```

---

## 7. Contrat de sortie

Toute réponse du système est un objet Pydantic validé, jamais du texte libre :

```python
class Action(BaseModel):
    action: str
    date_limite: date | None
    note: str | None

class Terme(BaseModel):
    terme: str
    explication: str
    source: str | None          # fichier + page du corpus

class Explication(BaseModel):
    type_document: str
    emetteur: str | None
    resume_simple: str
    actions: list[Action]
    termes: list[Terme]
    avertissement: str | None
    citations: list[Citation]
    incertitudes: list[str]     # ce qui manque dans le document
    langue: Literal["fr", "ar", "ary"]
```

Si le modèle ne peut pas remplir un champ à partir du document, il met `None` ou ajoute une
incertitude. Il ne comble jamais un trou.

---

## 8. Ordre de construction

Respecte cet ordre, il correspond aux jalons notés.

**Semaine 1 — socle (étape 1)**
- Corpus de référence : 30 à 50 documents publics, deux familles (administratif, médical),
  avec leurs métadonnées (source, langue, version, page).
- Pipeline d'ingestion, index Chroma, chaîne RAG, API FastAPI, interface Streamlit.
- **Et dès cette semaine** : le jeu annoté de 40 documents et `run_eval.py` qui tourne.
- Fin de semaine : une question sur un document produit une explication sourcée, et j'ai un
  premier tableau de scores.

**Semaine 2 — multimodal (étape 2)**
- Intégration du VLM, indexation des figures, recherche texte-image, fusion et reranking.
- 500 à 800 paires question/passage pour adapter le reranker.
- Tableau comparatif des trois configurations.

**Semaine 3 — agentique (étape 3)**
- Graphe LangGraph avec un nœud de vérification de fidélité qui peut rejeter une réponse.
- Serveur MCP exposant `get_procedure_info`, `get_user_deadlines`, `create_reminder`.
- Interruption du graphe pour approbation humaine, jeton lié au contenu exact, idempotence.

**Semaine 4 — intégration (étape 4)**
- Interface web complète, identités, Docker Compose, tests de sécurité, ~60 scénarios évalués.
- Documentation, rapport d'évaluation, support de soutenance.

---

## 9. Comment je veux que tu travailles

- **Demande avant de supposer.** Matériel disponible, corpus choisi, clés d'API : si ce n'est
  pas dans ce brief, pose-moi la question au lieu de choisir à ma place.
- **Propose un plan avant chaque étape**, et attends mon accord.
- **Commits petits et lisibles**, un par unité fonctionnelle, message en français.
- **Tests d'abord pour tout ce qui touche aux quatre contraintes** de la section 3.
- **Lance les tests et le linter** après chaque changement, et montre-moi la sortie réelle.
  Ne dis jamais qu'un test passe sans l'avoir exécuté.
- **N'invente aucune donnée.** Pas de corpus fictif, pas de résultats d'évaluation plausibles :
  si une mesure n'a pas tourné, dis-le.
- **Signale les dérives de périmètre.** Si une idée est intéressante mais ne sert aucun des
  quatre jalons, dis-le-moi et laisse-la de côté.
- **Explique tes choix techniques en deux lignes** quand ils ne sont pas évidents : j'ai une
  soutenance à défendre, je dois pouvoir justifier chaque composant.

---

## 10. Matériel et outils disponibles

### Configuration
- **RAM** : 16 Go
- **GPU** : Aucun
- **Inference locale** : Ollama

### Modèles disponibles
- `nomic-embed-text:latest` — embeddings multilingual
- `mistral:latest` — LLM principal
- `gemma3:4b` — LLM alternatif
- `llama3:latest` — LLM
- `llama3.2:1b` — petit modèle

### Pile adoptée
- OCR : Tesseract (fra + ara)
- Embeddings : nomic-embed-text
- LLM : mistral:latest
- Vecteurs : Chroma (fichier local)
- UI : Streamlit
- API : FastAPI

---

## 11. Première tâche

Ne code rien encore. Commence par :

1. Me poser les questions bloquantes (matériel, corpus, accès API, langues retenues).
2. Me proposer le squelette du dépôt et le `docker-compose.yml` de la semaine 1.
3. Me proposer le format du jeu de données annoté pour l'évaluation, avec un exemple rempli.

Ensuite seulement, on attaque l'ingestion.