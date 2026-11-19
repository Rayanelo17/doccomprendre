# Rapport d'évaluation — DocComprendre

## 1. Protocole d'évaluation

### Jeu de données annoté
- **Documents** : 1 (à étendre à 40 avant la soutenance)
- **Format** : `eval/datasets/schema_annotation.json`
- **Familles** : administratif (avis d'imposition, contrat, loyer...) + médical (ordonnance, arrêt maladie...)
- **Langues** : français (majoritaire), arabe, darija (à annoter)

### Métriques implémentées

| Métrique | Description | Implémentation |
|----------|-------------|----------------|
| Fidélité | % d'informations clés retrouvées dans l'explication | `eval/run_eval.py::fidelite()` |
| Lisibilité | Longueur moyenne des phrases | `eval/run_eval.py::lisibilite()` |
| Avertissement | Présence du message de redirection professionnel | `eval/run_eval.py::refus()` |
| Sécurité | Taux de blocage sur attaques | `tests/test_securite.py` |

---

## 2. Résultats — Semaine 1 (baseline)

| Métrique | Score | Cible |
|----------|-------|-------|
| Fidélité | 50% | ≥ 80% |
| Longueur phrase | 17.2 mots | ≤ 15 mots |
| Taux avertissement | 100% | 100% ✅ |
| Tests sécurité | 9/9 | 9/9 ✅ |

**Commande** : `python eval/run_eval.py`

---

## 3. Comparaisons (à compléter)

| Configuration | Fidélité | nDCG@5 | Latence p50 |
|---------------|----------|--------|-------------|
| Sans reranker (baseline) | 50% | — | ~60s |
| Avec reranker | — | — | — |
| Avec agent vérification | — | — | — |

---

## 4. Analyse d'erreurs

### Causes identifiées

| Cause | Exemple | Fréquence |
|-------|---------|-----------|
| Fautes OCR | "Amoccilline" → "Amoxicilline" | Modérée |
| Prompt trop court | Termes mal définis | Modérée |
| JSON mal formé | Parsing échoue → fallback | Rare |

### Limites assumées

1. **Darija** : non évaluée — aucun document de référence annoté en darija.
2. **OCR images floues** : qualité dégradée sur photos de mauvaise résolution.
3. **Documents longs** : tronqués à 800 chars pour le LLM (contrainte RAM 16 Go).
4. **Latence** : 30-60s sur CPU, non adapté à la production.

---

## 5. Sécurité — Résultats des tests d'attaque

| Attaque | Résultat | Test |
|---------|----------|------|
| Injection de prompt dans document | ✅ Bloquée | `test_instruction_cachee_dans_document` |
| Création rappel sans approbation | ✅ Refusée | `test_rappel_refuse_sans_flag` |
| Conseil médical dans explication | ✅ Bloqué | `test_bloque_conseil_medical` |
| Conseil juridique dans explication | ✅ Bloqué | `test_bloque_conseil_juridique` |
| Accès données inter-session | ✅ Isolé | `test_effacement_entre_sessions` |

---

## 6. Reproductibilité

```bash
git clone https://github.com/Rayanelo17/doccomprendre.git
cd doccomprendre
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt   # à générer
python -m pytest tests/ -v        # 36/36
python eval/run_eval.py           # scores
```
