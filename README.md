# Following the Wave or Riding Alone? A Decade of Thematic Evolution at SBBD vs. VLDB (2016–2025)

Reproducible pipeline and research artifacts for the SBBD 2026 vision paper.

This repository accompanies the paper:

> Tiago de Melo (2026). **Following the Wave or Riding Alone? A Decade of
> Thematic Evolution at SBBD vs. VLDB (2016–2025).** Brazilian Symposium on
> Databases (SBBD 2026), Vision Papers track.

The study is the first longitudinal, full-text topic-modeling comparison
between the Brazilian Symposium on Databases (SBBD) and the international VLDB
conference over a full decade (2016–2025), covering **3,525 papers** in two
languages. It pairs the topical analysis with a bibliometric characterisation
drawn from OpenAlex and Semantic Scholar.

**Headline findings:** (1) *convergence* — 58% of SBBD topics align semantically
with VLDB topics; (2) *temporal lag* — SBBD absorbs mainstream trends with a
median lag of ~1.5 years; (3) *divergence* — 13 SBBD-exclusive topics reflect a
strongly applied, Brazil-centric research identity. A notable counter-example is
privacy research, where SBBD peaked ~3 years *ahead* of VLDB, consistent with the
early adoption pressure of Brazil's LGPD.

---

## Repository layout

```
.
├── *.py                      # the full pipeline (run order documented below)
├── requirements.txt          # Python dependencies
├── chaves.env.example        # template for API keys (copy to chaves.env)
├── LICENSE                   # MIT — covers the source code
├── LICENSE-data              # CC-BY-4.0 — covers everything under release/data/
└── release/
    ├── index.html            # browsable landing page for the artifacts
    ├── plots/                # all 14 figures from the paper (PDF)
    └── data/
        ├── corpus_sbbd.jsonl         # SBBD full-text corpus (open access, SOL)
        ├── corpus_sbbd_stats.txt     # extraction statistics
        ├── bibliometrics_comparison.csv   # year-by-year SBBD vs VLDB indicators
        ├── topic_matches.csv              # SBBD↔VLDB semantic alignment + lag
        ├── per_paper/                     # per-paper metadata (SBBD + VLDB)
        ├── sbbd/                          # SBBD topic-modeling outputs
        └── vldb/                          # VLDB topic-modeling outputs
```

### What is **not** in this repository (and why)

- **Raw source PDFs** (`pdfs/`, `vldb_pdfs/`) — not redistributable; download
  them with the scripts below.
- **VLDB full-text corpus** (`vldb_corpus.jsonl`) — the Proceedings of the VLDB
  Endowment are under their own copyright. Only **derived** VLDB outputs (topic
  assignments, labels, OpenAlex metadata) are included. Reconstruct the corpus
  locally with `download_vldb.py` + `extract_text_vldb.py`.
- The **SBBD full-text corpus is included** (`release/data/corpus_sbbd.jsonl`)
  because SBBD papers are openly available via the SBC Open Library.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# API keys (only needed to re-run label refinement / Semantic Scholar fetch)
cp chaves.env.example chaves.env   # then edit with your keys
```

`refine_topics.py` requires an Anthropic API key; `fetch_semantic_scholar.py`
optionally uses a Semantic Scholar key (higher rate limit). Text extraction
also requires the **Tesseract OCR** binary installed on the system for the
small set of scanned SBBD 2020 PDFs.

---

## Pipeline (run order)

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `download_pdfs.py` / `download_vldb.py` | Download SBBD (SOL) and VLDB (vldb.org) PDFs into `pdfs/` and `vldb_pdfs/` |
| 2 | `extract_text.py` / `extract_text_vldb.py` | Extract full text (PyMuPDF, Tesseract OCR fallback) → `corpus.jsonl`, `vldb_corpus.jsonl` |
| 3 | `fetch_sol_titles.py` | Recover SBBD canonical titles + DOIs from SOL |
| 3 | `fetch_pdf_metadata.py` | Page counts, author counts, affiliations/countries from PDFs |
| 3 | `fetch_openalex.py` | Full VLDB bibliometric metadata via OpenAlex |
| 3 | `fetch_semantic_scholar.py` | SBBD citation metadata via Semantic Scholar |
| 4 | `topic_modeling.py` | BERTopic per venue → `results/{sbbd,vldb}/` (31 / 35 topics) |
| 5 | `refine_topics.py` | Claude-assisted topic label refinement → `refined_labels.json` |
| 6 | `analyze_evolution.py` | Temporal topic-prevalence tables and plots |
| 7 | `analyze_comparison.py` | Semantic alignment, temporal lag, exclusive topics |
| 8 | `analyze_bibliometrics.py` | Bibliometric comparison figures |

**Method summary:** BERTopic with the multilingual sentence-embedding model
`paraphrase-multilingual-MiniLM-L12-v2` (chosen because 99% of SBBD papers mix
Portuguese and English), UMAP dimensionality reduction, and HDBSCAN clustering.
Raw KeyBERT-style keyword strings are refined into concise English labels with
Claude Haiku. Topics are aligned across venues by cosine similarity of their
labels (match threshold 0.60), and the temporal lag of a matched pair is the
difference between the peak-prevalence years in each venue.

---

## Data dictionary (release/data/)

- **`corpus_sbbd.jsonl`** — one JSON object per line: `{year, filename, text}`
  for 489 SBBD papers.
- **`bibliometrics_comparison.csv`** — 10 years × 15 columns: paper counts,
  pages, authors, citations, references, international collaboration, OA rate.
- **`topic_matches.csv`** — for each of the 31 SBBD topics: best-matching VLDB
  topic, cosine similarity, and match flag (≥ 0.60).
- **`per_paper/sbbd_metadata.csv`** — Semantic Scholar metadata for 488/489 SBBD papers.
- **`per_paper/sbbd_titles_dois.csv`** — canonical SBBD titles + DOIs from SOL.
- **`per_paper/vldb_metadata.csv`** — OpenAlex metadata for all 3,036 VLDB papers.
- **`{sbbd,vldb}/topic_info.csv`** — topic ID, document count, top keywords, label.
- **`{sbbd,vldb}/refined_labels.json`** — topic ID → Claude-refined English label.
- **`{sbbd,vldb}/topic_evolution.csv`** — % of papers per year for each topic.
- **`{sbbd,vldb}/docs_topics.csv`** — per-paper topic assignment (−1 = outlier).

---

## License

- **Source code:** MIT (see [`LICENSE`](LICENSE)).
- **Data artifacts** (everything under `release/data/`): CC-BY-4.0
  (see [`LICENSE-data`](LICENSE-data)).

## Citation

```bibtex
@inproceedings{demelo2026sbbdvldb,
  title     = {Following the Wave or Riding Alone? A Decade of Thematic
               Evolution at SBBD vs. VLDB (2016--2025)},
  author    = {de Melo, Tiago},
  booktitle = {Proceedings of the Brazilian Symposium on Databases (SBBD),
               Vision Papers track},
  year      = {2026}
}
```
