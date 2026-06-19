#!/usr/bin/env python3
"""
Coleta metadados bibliométricos completos de SBBD e VLDB via OpenAlex API.

Atributos extraídos por artigo:
  - Identificadores: openalex_id, doi, title, year, publication_date
  - Autoria: author_count, authors (nomes), orcid_count
  - Afiliações: institutions, countries, is_international (≥2 países)
  - Impacto: cited_by_count, referenced_works_count
  - Físico: page_count, first_page, last_page
  - Acesso: is_oa, oa_status, oa_url
  - Conteúdo: abstract, concepts (OpenAlex), topics (OpenAlex), language
  - Venue: source_name, source_type, volume, issue

Saída: results/openalex_{sbbd,vldb}.csv  +  results/openalex_authors.csv
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime

BASE_DIR   = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# E-mail para o "polite pool" da OpenAlex (maior rate-limit)
POLITE_EMAIL = "tmelo@uea.edu.br"

YEARS = list(range(2016, 2026))
YEAR_FILTER = "|".join(str(y) for y in YEARS)

# SBBD tem cobertura muito baixa no OpenAlex para 2016-2025 (~10 artigos).
# Apenas o VLDB é coletado aqui; metadados do SBBD vêm dos PDFs.
CONFERENCES = {
    "vldb": {
        "search_terms": ["Proceedings of the VLDB Endowment", "PVLDB"],
        "source_id": "S4210226185",   # confirmado manualmente
    },
}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"bibliometric-study/1.0 (mailto:{POLITE_EMAIL})"})


# ---------------------------------------------------------------------------
# Utilitários de API
# ---------------------------------------------------------------------------

def api_get(url: str, params: dict = None, retries: int = 5) -> dict:
    """GET com retry exponencial."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 429:
                wait = 2 ** attempt * 5
                print(f"    [429] Rate limit — aguardando {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def short_id(full_id: str) -> str:
    """Extrai o código curto de uma URL OpenAlex (ex: 'https://...S123' -> 'S123')."""
    return full_id.split("/")[-1] if full_id else full_id


def find_source_ids(search_terms: list[str]) -> list[tuple[str, str]]:
    """Busca todos os source_ids relevantes da conferência no OpenAlex."""
    seen, found = set(), []
    for term in search_terms:
        data = api_get(
            "https://api.openalex.org/sources",
            {"search": term, "per-page": 10, "mailto": POLITE_EMAIL},
        )
        for src in data.get("results", []):
            sid = short_id(src["id"])
            if sid not in seen:
                seen.add(sid)
                found.append((sid, src["display_name"]))
                print(f"    Encontrado: {src['display_name']} (id={sid})")
    return found


# ---------------------------------------------------------------------------
# Extração de atributos de um único trabalho
# ---------------------------------------------------------------------------

def extract_abstract(work: dict) -> str:
    """Reconstrói o abstract a partir do abstract_inverted_index."""
    aii = work.get("abstract_inverted_index")
    if not aii:
        return ""
    positions = {}
    for word, pos_list in aii.items():
        for pos in pos_list:
            positions[pos] = word
    return " ".join(positions[k] for k in sorted(positions))


def extract_work(work: dict, conference: str) -> dict:
    """Extrai todos os campos relevantes de um work OpenAlex."""
    # --- Identificadores ---
    rec = {
        "conference":        conference,
        "openalex_id":       work.get("id", ""),
        "doi":               work.get("doi", ""),
        "title":             work.get("title", ""),
        "year":              work.get("publication_year"),
        "publication_date":  work.get("publication_date", ""),
        "type":              work.get("type", ""),
        "language":          work.get("language", ""),
    }

    # --- Biblio (páginas, volume, issue) ---
    biblio = work.get("biblio", {}) or {}
    first_page = biblio.get("first_page")
    last_page  = biblio.get("last_page")
    try:
        page_count = int(last_page) - int(first_page) + 1 if first_page and last_page else None
    except (ValueError, TypeError):
        page_count = None
    rec.update({
        "volume":      biblio.get("volume"),
        "issue":       biblio.get("issue"),
        "first_page":  first_page,
        "last_page":   last_page,
        "page_count":  page_count,
    })

    # --- Impacto ---
    rec.update({
        "cited_by_count":        work.get("cited_by_count", 0),
        "referenced_works_count": work.get("referenced_works_count", 0),
        "cited_by_api_url":      work.get("cited_by_api_url", ""),
    })

    # --- Acesso aberto ---
    oa = work.get("open_access", {}) or {}
    rec.update({
        "is_oa":    oa.get("is_oa", False),
        "oa_status": oa.get("oa_status", ""),
        "oa_url":   oa.get("oa_url", ""),
    })

    # --- Source ---
    primary = work.get("primary_location", {}) or {}
    source  = primary.get("source", {}) or {}
    rec.update({
        "source_name": source.get("display_name", ""),
        "source_type": source.get("type", ""),
        "source_id":   source.get("id", ""),
    })

    # --- Autores e afiliações ---
    authorships = work.get("authorships", []) or []
    rec["author_count"] = len(authorships)

    author_names, institutions_list, countries_list, orcids = [], [], [], []
    for a in authorships:
        author = a.get("author", {}) or {}
        author_names.append(author.get("display_name", ""))
        if author.get("orcid"):
            orcids.append(author["orcid"])

        for inst in a.get("institutions", []) or []:
            inst_name = inst.get("display_name", "")
            country   = inst.get("country_code", "")
            if inst_name:
                institutions_list.append(inst_name)
            if country:
                countries_list.append(country)

    unique_countries = list(dict.fromkeys(countries_list))   # preserva ordem, sem dup
    unique_institutions = list(dict.fromkeys(institutions_list))

    rec.update({
        "authors":           " | ".join(author_names),
        "orcid_count":       len(orcids),
        "institutions":      " | ".join(unique_institutions),
        "countries":         " | ".join(unique_countries),
        "country_count":     len(unique_countries),
        "is_international":  len(unique_countries) > 1,
    })

    # --- Concepts (OpenAlex legado) ---
    concepts = work.get("concepts", []) or []
    top_concepts = [c["display_name"] for c in sorted(
        concepts, key=lambda x: x.get("score", 0), reverse=True
    )[:5]]
    rec["concepts"] = " | ".join(top_concepts)

    # --- Topics (OpenAlex novo) ---
    topics = work.get("topics", []) or []
    top_topics = [t["display_name"] for t in topics[:3]]
    rec["topics_openalex"] = " | ".join(top_topics)

    # --- Keywords ---
    keywords = work.get("keywords", []) or []
    rec["keywords"] = " | ".join(k.get("display_name", "") for k in keywords[:10])

    # --- Abstract ---
    rec["abstract"] = extract_abstract(work)

    # --- Grants ---
    grants = work.get("grants", []) or []
    rec["grant_count"] = len(grants)
    rec["funders"] = " | ".join(
        g.get("funder_display_name", "") for g in grants if g.get("funder_display_name")
    )

    return rec


def extract_author_rows(work: dict, conference: str) -> list[dict]:
    """Gera uma linha por (artigo × autor) para a tabela de autores."""
    rows = []
    openalex_id = work.get("id", "")
    year        = work.get("publication_year")
    title       = work.get("title", "")
    for pos, a in enumerate(work.get("authorships", []) or [], start=1):
        author = a.get("author", {}) or {}
        for inst in (a.get("institutions", []) or []) or [{}]:
            rows.append({
                "conference":   conference,
                "openalex_id":  openalex_id,
                "year":         year,
                "title":        title,
                "author_pos":   pos,
                "author_name":  author.get("display_name", ""),
                "author_id":    author.get("id", ""),
                "orcid":        author.get("orcid", ""),
                "institution":  inst.get("display_name", ""),
                "institution_id": inst.get("id", ""),
                "country_code": inst.get("country_code", ""),
                "institution_type": inst.get("type", ""),
            })
        if not (a.get("institutions") or []):
            rows.append({
                "conference":   conference,
                "openalex_id":  openalex_id,
                "year":         year,
                "title":        title,
                "author_pos":   pos,
                "author_name":  author.get("display_name", ""),
                "author_id":    author.get("id", ""),
                "orcid":        author.get("orcid", ""),
                "institution":  "",
                "institution_id": "",
                "country_code": "",
                "institution_type": "",
            })
    return rows


# ---------------------------------------------------------------------------
# Paginação completa de works de uma fonte
# ---------------------------------------------------------------------------

def fetch_all_works(source_ids: list[tuple[str,str]], conference: str) -> tuple[list[dict], list[dict]]:
    """Busca todos os works de uma ou mais fontes para o período definido."""
    works_rows, author_rows = [], []

    id_filter = "|".join(sid for sid, _ in source_ids)

    cursor = "*"
    page   = 0
    total  = None

    print(f"  Buscando works de {conference.upper()} (fontes: {len(source_ids)})...")
    while True:
        params = {
            "filter":   f"primary_location.source.id:{id_filter},"
                        f"publication_year:{YEAR_FILTER}",
            "per-page": 200,
            "cursor":   cursor,
            "select":   ",".join([
                "id", "doi", "title", "publication_year", "publication_date",
                "type", "language", "biblio", "cited_by_count",
                "referenced_works_count", "cited_by_api_url",
                "open_access", "primary_location", "authorships",
                "concepts", "topics", "keywords",
                "abstract_inverted_index",
            ]),
            "mailto": POLITE_EMAIL,
        }

        data = api_get("https://api.openalex.org/works", params)
        meta    = data.get("meta", {})
        results = data.get("results", [])

        if total is None:
            total = meta.get("count", "?")
            print(f"    Total na API: {total} works")

        page += 1
        print(f"    Página {page} — {len(results)} works | acumulado: {len(works_rows)}", end="\r")

        for w in results:
            works_rows.append(extract_work(w, conference))
            author_rows.extend(extract_author_rows(w, conference))

        cursor = meta.get("next_cursor")
        if not cursor or not results:
            break

        time.sleep(0.15)   # respeita rate limit do polite pool

    print(f"\n    Concluído: {len(works_rows)} works extraídos")
    return works_rows, author_rows


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def main():
    all_works, all_authors = [], []

    for name, cfg in CONFERENCES.items():
        print(f"\n{'='*60}")
        print(f"Conferência: {name.upper()}")
        print(f"{'='*60}")

        print("  Localizando fontes no OpenAlex...")
        source_ids = find_source_ids(cfg["search_terms"])
        if not source_ids:
            print(f"  [ERRO] Nenhuma fonte encontrada para {name}. Abortando.")
            continue

        works, authors = fetch_all_works(source_ids, name)
        all_works.extend(works)
        all_authors.extend(authors)

        # Salva por conferência
        df_w = pd.DataFrame(works)
        df_w.to_csv(os.path.join(RESULTS_DIR, f"openalex_{name}.csv"), index=False)
        print(f"  Salvo: results/openalex_{name}.csv  ({len(df_w)} linhas)")

        # Estatísticas rápidas
        if not df_w.empty:
            print(f"\n  Resumo {name.upper()}:")
            print(f"    Artigos: {len(df_w)}")
            print(f"    Com DOI: {df_w['doi'].notna().sum()} ({df_w['doi'].notna().mean()*100:.0f}%)")
            print(f"    Com abstract: {(df_w['abstract'].str.len() > 0).sum()}")
            print(f"    Citações médias: {df_w['cited_by_count'].mean():.1f}")
            print(f"    Autores médios: {df_w['author_count'].mean():.1f}")
            if 'page_count' in df_w:
                valid_pages = df_w['page_count'].dropna()
                if not valid_pages.empty:
                    print(f"    Páginas médias: {valid_pages.mean():.1f}")
            print(f"    OA: {df_w['is_oa'].sum()} ({df_w['is_oa'].mean()*100:.0f}%)")
            print(f"    Internacionais: {df_w['is_international'].sum()} ({df_w['is_international'].mean()*100:.0f}%)")
            by_year = df_w.groupby("year").agg(
                papers=("openalex_id", "count"),
                avg_citations=("cited_by_count", "mean"),
                avg_authors=("author_count", "mean"),
            ).round(2)
            print(f"\n  Por ano:\n{by_year.to_string()}")

    # Salva tabela de autores consolidada
    df_a = pd.DataFrame(all_authors)
    df_a.to_csv(os.path.join(RESULTS_DIR, "openalex_authors.csv"), index=False)
    print(f"\nSalvo: results/openalex_authors.csv  ({len(df_a)} linhas)")

    # Salva consolidado
    df_all = pd.DataFrame(all_works)
    df_all.to_csv(os.path.join(RESULTS_DIR, "openalex_all.csv"), index=False)
    print(f"Salvo: results/openalex_all.csv  ({len(df_all)} linhas)")

    print(f"\n=== Coleta concluída em {datetime.now().strftime('%H:%M:%S')} ===")


if __name__ == "__main__":
    main()
