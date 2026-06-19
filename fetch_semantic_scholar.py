#!/usr/bin/env python3
"""
Coleta citações e metadados do Semantic Scholar para artigos do SBBD.
Usa title-search para identificar os artigos (sem DOI disponível).

Atributos coletados:
  - citation_count, influential_citation_count
  - reference_count
  - fields_of_study
  - s2_paper_id, external_ids (DOI, ArXiv, etc.)
  - is_open_access, open_access_pdf
  - publication_types
  - tldr (resumo automático gerado pelo S2)

Saída: results/s2_sbbd.csv
"""

import os
import json
import time
import requests
import pandas as pd
from dotenv import dotenv_values

BASE_DIR    = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CORPUS_PATH = os.path.join(BASE_DIR, "corpus.jsonl")
OUT_PATH    = os.path.join(RESULTS_DIR, "s2_sbbd.csv")

S2_API  = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = (
    "paperId,externalIds,title,year,citationCount,influentialCitationCount,"
    "referenceCount,fieldsOfStudy,publicationTypes,isOpenAccess,"
    "openAccessPdf,tldr,authors,venue,publicationDate"
)

# Lê chave do S2 se disponível (aumenta rate limit de 1 para 10 req/s)
_env = dotenv_values(os.path.join(BASE_DIR, "chaves.env"))
S2_API_KEY = _env.get("S2_API_KEY", "")

SESSION = requests.Session()
headers = {"User-Agent": "sbbd-bibliometric-study/1.0"}
if S2_API_KEY:
    headers["x-api-key"] = S2_API_KEY
    print(f"  [S2] Usando API key — rate limit: 10 req/s")
else:
    print(f"  [S2] Sem API key — rate limit: 1 req/s")
SESSION.headers.update(headers)

# Intervalo entre requisições (s)
REQ_INTERVAL = 0.12 if S2_API_KEY else 1.1


def load_corpus_titles() -> list[dict]:
    """Carrega títulos do corpus tentando extrair da primeira linha do texto."""
    records = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            rec   = json.loads(line)
            # Primeira linha não vazia como proxy de título
            lines = [l.strip() for l in rec["text"].split("\n") if l.strip()]
            title = lines[0][:200] if lines else ""
            records.append({
                "year":     rec["year"],
                "filename": rec["filename"],
                "title_guess": title,
            })
    return records


def search_paper(title: str, year: int, retries: int = 4) -> dict | None:
    """Busca um artigo pelo título no Semantic Scholar."""
    for attempt in range(retries):
        try:
            r = SESSION.get(S2_API, params={
                "query":  title[:200],
                "fields": S2_FIELDS,
                "limit":  3,
                "year":   f"{year}-{year}",
            }, timeout=20)

            if r.status_code == 429:
                wait = 2 ** attempt * 10
                print(f"\n    [429] aguardando {wait}s...", end="", flush=True)
                time.sleep(wait)
                continue

            if r.status_code != 200:
                return None

            results = r.json().get("data", [])
            if not results:
                return None

            # Pega o primeiro resultado (já filtrado por ano)
            return results[0]

        except requests.RequestException:
            time.sleep(2 ** attempt)

    return None


def extract_s2(paper: dict, year: int, filename: str) -> dict:
    if paper is None:
        return {
            "year": year, "filename": filename,
            "s2_found": False,
            "s2_paper_id": "", "doi": "", "arxiv_id": "",
            "s2_title": "", "s2_year": None,
            "citation_count": None, "influential_citation_count": None,
            "reference_count": None,
            "fields_of_study": "",
            "publication_types": "",
            "is_open_access": None, "oa_pdf_url": "",
            "tldr": "",
            "author_count_s2": None,
            "venue": "",
            "publication_date": "",
        }

    ext  = paper.get("externalIds", {}) or {}
    tldr = paper.get("tldr", {}) or {}
    oa   = paper.get("openAccessPdf", {}) or {}

    return {
        "year":     year,
        "filename": filename,
        "s2_found": True,
        "s2_paper_id":  paper.get("paperId", ""),
        "doi":          ext.get("DOI", ""),
        "arxiv_id":     ext.get("ArXiv", ""),
        "s2_title":     paper.get("title", ""),
        "s2_year":      paper.get("year"),
        "citation_count":             paper.get("citationCount"),
        "influential_citation_count": paper.get("influentialCitationCount"),
        "reference_count":            paper.get("referenceCount"),
        "fields_of_study":   "|".join(paper.get("fieldsOfStudy", []) or []),
        "publication_types": "|".join(paper.get("publicationTypes", []) or []),
        "is_open_access":    paper.get("isOpenAccess"),
        "oa_pdf_url":        oa.get("url", ""),
        "tldr":              tldr.get("text", ""),
        "author_count_s2":   len(paper.get("authors", []) or []),
        "venue":             paper.get("venue", ""),
        "publication_date":  paper.get("publicationDate", ""),
    }


def main():
    print("Carregando corpus SBBD...")
    corpus = load_corpus_titles()
    print(f"  {len(corpus)} artigos")

    # Retomada: carrega progresso anterior se existir
    done_files = set()
    rows = []
    if os.path.exists(OUT_PATH):
        prev = pd.read_csv(OUT_PATH)
        rows = prev.to_dict("records")
        done_files = set(prev["filename"].tolist())
        print(f"  Retomando: {len(done_files)} artigos já processados")

    corpus = [r for r in corpus if r["filename"] not in done_files]

    found    = sum(1 for r in rows if r.get("s2_found"))
    not_found = sum(1 for r in rows if not r.get("s2_found"))
    total = len(rows) + len(corpus)

    print("\nBuscando no Semantic Scholar...")
    for i, rec in enumerate(corpus, len(rows) + 1):
        print(f"  [{i:3d}/{total}] {rec['year']} | {rec['title_guess'][:60]}...", end=" ", flush=True)

        paper = search_paper(rec["title_guess"], rec["year"])
        row   = extract_s2(paper, rec["year"], rec["filename"])
        rows.append(row)

        if row["s2_found"]:
            found += 1
            print(f"✓  cit={row['citation_count']}", flush=True)
        else:
            not_found += 1
            print("✗", flush=True)

        time.sleep(REQ_INTERVAL)

        # Checkpoint a cada 50 artigos
        if i % 50 == 0:
            pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
            print(f"  [checkpoint] {i}/{len(corpus)} salvo em {OUT_PATH}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    out = OUT_PATH

    print(f"\n=== Semantic Scholar — SBBD ===")
    print(f"  Encontrados: {found}/{total} ({found/total*100:.0f}%)")
    print(f"  Não encontrados: {not_found}")

    found_df = df[df["s2_found"]]
    if not found_df.empty:
        print(f"\n  Por ano (artigos encontrados):")
        by_year = found_df.groupby("year").agg(
            papers_found=("s2_paper_id", "count"),
            avg_citations=("citation_count", "mean"),
            avg_influential=("influential_citation_count", "mean"),
            avg_references=("reference_count", "mean"),
        ).round(2)
        print(by_year.to_string())

    print(f"\n  Salvo: {out}")


if __name__ == "__main__":
    main()
