#!/usr/bin/env python3
"""
Recupera títulos e DOIs dos artigos SBBD diretamente do SOL (SBC Open Library).

Estratégia:
  - Extrai o SOL article ID do filename (padrão: {sub}_{sol_id}.pdf)
  - Faz GET em https://sol.sbc.org.br/index.php/sbbd/article/view/{sol_id}
  - Parseia título e DOI do HTML

Saída: results/sol_titles.csv  (filename, sol_id, sol_title, sol_doi)
"""

import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIR    = os.path.dirname(__file__)
RESULTS     = os.path.join(BASE_DIR, "results")
OUT_PATH    = os.path.join(RESULTS, "sol_titles.csv")

SOL_BASE    = "https://sol.sbc.org.br/index.php/sbbd/article/view/{}"
REQ_DELAY   = 0.5   # segundos entre requisições

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "sbbd-bibliometric-study/1.0 (academic research)"
})


def sol_id_from_filename(filename: str) -> str | None:
    """Extrai o SOL article ID do padrão '{sol_id}_{other}.pdf'."""
    m = re.match(r"(\d+)_\d+\.pdf", filename)
    return m.group(1) if m else None


def fetch_sol_metadata(sol_id: str) -> dict:
    url = SOL_BASE.format(sol_id)
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code != 200:
            return {"sol_title": "", "sol_doi": "", "sol_status": r.status_code}

        soup = BeautifulSoup(r.text, "html.parser")

        # Título: <meta name="citation_title"> (mais limpo) ou <title>
        title = ""
        meta_ct = soup.find("meta", attrs={"name": "citation_title"})
        if meta_ct:
            title = meta_ct.get("content", "").strip()
        if not title:
            tag = soup.find("title")
            if tag:
                # Remove sufixo " | Anais do ..."
                title = tag.get_text(strip=True).split("|")[0].strip()

        # DOI: <meta name="DC.Identifier.DOI"> ou link com doi.org
        doi = ""
        meta_doi = soup.find("meta", attrs={"name": "DC.Identifier.DOI"})
        if meta_doi:
            doi = meta_doi.get("content", "").strip()
        if not doi:
            a = soup.find("a", href=re.compile(r"doi\.org"))
            if a:
                doi = re.sub(r"https?://doi\.org/", "", a["href"]).strip()

        return {"sol_title": title, "sol_doi": doi, "sol_status": 200}

    except requests.RequestException as e:
        return {"sol_title": "", "sol_doi": "", "sol_status": str(e)}


def main():
    s2 = pd.read_csv(os.path.join(RESULTS, "s2_sbbd.csv"))

    # Retomada
    done = set()
    rows = []
    if os.path.exists(OUT_PATH):
        prev = pd.read_csv(OUT_PATH)
        rows = prev.to_dict("records")
        done = set(prev["filename"].tolist())
        print(f"  Retomando: {len(done)} já processados")

    pending = s2[~s2["filename"].isin(done)]
    total   = len(s2)

    print(f"Buscando títulos no SOL para {len(pending)} artigos...")
    for i, (_, rec) in enumerate(pending.iterrows(), len(done) + 1):
        fname  = rec["filename"]
        sol_id = sol_id_from_filename(fname)

        if not sol_id:
            rows.append({"filename": fname, "sol_id": "", "sol_title": "", "sol_doi": "", "sol_status": "no_id"})
            print(f"  [{i:3d}/{total}] {fname} — sem ID")
            continue

        meta = fetch_sol_metadata(sol_id)
        rows.append({"filename": fname, "sol_id": sol_id, **meta})

        status = "✓" if meta["sol_title"] else "✗"
        print(f"  [{i:3d}/{total}] {fname} — {status} {meta['sol_title'][:70]}")

        time.sleep(REQ_DELAY)

        if i % 50 == 0:
            pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
            print(f"  [checkpoint] {i}/{total}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)

    found = df[df["sol_title"] != ""]
    print(f"\n=== SOL Titles ===")
    print(f"  Recuperados: {len(found)}/{total} ({len(found)/total*100:.0f}%)")
    print(f"  Com DOI:     {(df['sol_doi'] != '').sum()}")
    print(f"  Salvo: {OUT_PATH}")


if __name__ == "__main__":
    main()
