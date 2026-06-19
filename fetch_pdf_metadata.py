#!/usr/bin/env python3
"""
Extrai metadados bibliométricos dos PDFs de SBBD e VLDB:
  - Número de páginas
  - Número de autores (parsing da 1ª página)
  - Afiliações e países inferidos do texto
  - Presença de referências bibliográficas

Saída: results/pdf_metadata_{sbbd,vldb}.csv
"""

import os
import re
import json
import fitz   # pymupdf
import pandas as pd
from pathlib import Path

BASE_DIR    = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

PDFS = {
    "sbbd": os.path.join(BASE_DIR, "pdfs"),
    "vldb": os.path.join(BASE_DIR, "vldb_pdfs"),
}
CORPORA = {
    "sbbd": os.path.join(BASE_DIR, "corpus.jsonl"),
    "vldb": os.path.join(BASE_DIR, "vldb_corpus.jsonl"),
}

# Padrão de e-mail (proxy forte para afiliação)
RE_EMAIL = re.compile(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", re.IGNORECASE)

# Indicadores de país nas afiliações (lista compacta, extensível)
COUNTRY_PATTERNS = {
    "BR": re.compile(r"\bBrasil\b|\bBrazil\b|\bBR\b", re.IGNORECASE),
    "US": re.compile(r"\bUSA\b|\bUnited States\b|\bU\.S\.A\b", re.IGNORECASE),
    "CN": re.compile(r"\bChina\b|\bChinese\b|\bBeijing\b|\bShanghai\b", re.IGNORECASE),
    "DE": re.compile(r"\bGermany\b|\bDeutschland\b|\bBerlin\b|\bMunich\b", re.IGNORECASE),
    "FR": re.compile(r"\bFrance\b|\bFrench\b|\bParis\b|\bINRIA\b", re.IGNORECASE),
    "GB": re.compile(r"\bUnited Kingdom\b|\bEngland\b|\bLondon\b|\bOxford\b|\bCambridge\b", re.IGNORECASE),
    "AU": re.compile(r"\bAustralia\b|\bSydney\b|\bMelbourne\b", re.IGNORECASE),
    "CA": re.compile(r"\bCanada\b|\bToronto\b|\bMontreal\b|\bVancouver\b", re.IGNORECASE),
    "IN": re.compile(r"\bIndia\b|\bIndian\b|\bIIT\b|\bIISc\b", re.IGNORECASE),
    "CH": re.compile(r"\bSwitzerland\b|\bETH\b|\bEPFL\b|\bZürich\b", re.IGNORECASE),
    "NL": re.compile(r"\bNetherlands\b|\bAmsterdam\b|\bCWI\b", re.IGNORECASE),
    "IT": re.compile(r"\bItaly\b|\bItalian\b|\bRome\b|\bMilan\b", re.IGNORECASE),
    "JP": re.compile(r"\bJapan\b|\bJapanese\b|\bTokyo\b|\bOsaka\b", re.IGNORECASE),
    "KR": re.compile(r"\bKorea\b|\bKorean\b|\bSeoul\b|\bKAIST\b", re.IGNORECASE),
    "SG": re.compile(r"\bSingapore\b|\bNUS\b|\bNTU\b", re.IGNORECASE),
    "ES": re.compile(r"\bSpain\b|\bSpanish\b|\bMadrid\b|\bBarcelona\b", re.IGNORECASE),
    "PT": re.compile(r"\bPortugal\b|\bPortuguese\b|\bLisbon\b|\bPorto\b", re.IGNORECASE),
    "AT": re.compile(r"\bAustria\b|\bVienna\b|\bWien\b", re.IGNORECASE),
    "SE": re.compile(r"\bSweden\b|\bStockholm\b|\bKTH\b", re.IGNORECASE),
    "IL": re.compile(r"\bIsrael\b|\bTechnion\b|\bTel Aviv\b", re.IGNORECASE),
    "SA": re.compile(r"\bSaudi Arabia\b|\bKAUST\b|\bRiyadh\b", re.IGNORECASE),
    "QA": re.compile(r"\bQatar\b|\bDoha\b", re.IGNORECASE),
    "HK": re.compile(r"\bHong Kong\b|\bHKUST\b|\bHKU\b", re.IGNORECASE),
}

# Palavras que indicam linha de afiliação (não é nome de autor)
RE_AFFIL_HINT = re.compile(
    r"university|universidade|instituto|institute|college|dept\.|department|"
    r"laboratory|lab\b|federal|escola|faculdade|center|centre|research|"
    r"usp|ufrj|unicamp|ufrgs|ufmg|puc|uea|ufam|ufc|ufpe|ufba|ufscar|ufpr|"
    r"ibm|google|microsoft|amazon|oracle|intel|facebook|meta|baidu|alibaba",
    re.IGNORECASE,
)

# Separadores de autor comuns em cabeçalhos de artigos científicos
RE_AUTHOR_SEP = re.compile(r",\s*|\s+and\s+|\s*;\s*|\s*&\s*", re.IGNORECASE)

# Linhas que claramente NÃO são autores
RE_NOT_AUTHOR = re.compile(
    r"abstract|introduction|keywords|resumo|palavras|copyright|@|"
    r"http|www\.|doi:|proceedings|pvldb|sbbd|vol\.|pp\.|fig\.|table|"
    r"^\d+$|^\s*$",
    re.IGNORECASE,
)


def extract_first_page_text(pdf_path: str) -> str:
    """Retorna o texto das primeiras 2 páginas do PDF."""
    try:
        doc  = fitz.open(pdf_path)
        pages = min(2, len(doc))
        text = "\n".join(doc[i].get_text("text") for i in range(pages))
        doc.close()
        return text
    except Exception:
        return ""


def count_pages(pdf_path: str) -> int | None:
    try:
        doc = fitz.open(pdf_path)
        n   = len(doc)
        doc.close()
        return n
    except Exception:
        return None


def detect_countries(text: str) -> list[str]:
    return [code for code, pat in COUNTRY_PATTERNS.items() if pat.search(text)]


def count_references(text: str) -> int:
    """Conta linhas com padrão de referência bibliográfica."""
    ref_pat = re.compile(r"^\s*\[\d+\]|\s+\(\d{4}\)\.", re.MULTILINE)
    return len(ref_pat.findall(text))


def estimate_authors_from_text(text: str) -> int:
    """
    Heurística: conta e-mails únicos como proxy de autores.
    Fallback: conta separadores em linha logo abaixo do título.
    """
    emails = set(RE_EMAIL.findall(text))
    if emails:
        return len(emails)

    # Tenta encontrar linha de autores (logo após título, antes de afiliação)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines[:30]):
        if RE_NOT_AUTHOR.search(line):
            continue
        if RE_AFFIL_HINT.search(line):
            continue
        # Linha candidata a autores: tem vírgula ou 'and'
        if "," in line or " and " in line.lower():
            parts = [p.strip() for p in RE_AUTHOR_SEP.split(line) if p.strip()]
            # Filtra partes muito longas (provavelmente não são nomes)
            names = [p for p in parts if len(p.split()) <= 5 and len(p) < 50]
            if 2 <= len(names) <= 20:
                return len(names)
    return 1   # mínimo


def process_conference(name: str) -> pd.DataFrame:
    pdfs_root = PDFS[name]
    corpus_path = CORPORA[name]

    # Carrega lista de arquivos do corpus para associar year <-> filename
    file_year = {}
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            file_year[rec["filename"]] = rec["year"]

    records = []
    year_dirs = sorted(
        int(d) for d in os.listdir(pdfs_root)
        if os.path.isdir(os.path.join(pdfs_root, d)) and d.isdigit()
    )

    for year in year_dirs:
        year_dir = os.path.join(pdfs_root, str(year))
        pdfs = sorted(f for f in os.listdir(year_dir) if f.endswith(".pdf"))
        print(f"  {year}: {len(pdfs)} PDFs", end=" ", flush=True)
        ok = 0
        for fname in pdfs:
            path = os.path.join(year_dir, fname)
            text = extract_first_page_text(path)

            pages      = count_pages(path)
            authors    = estimate_authors_from_text(text)
            countries  = detect_countries(text)
            refs       = count_references(text)
            has_email  = bool(RE_EMAIL.search(text))

            records.append({
                "conference":    name,
                "year":          year,
                "filename":      fname,
                "page_count":    pages,
                "author_count":  authors,
                "countries":     "|".join(countries),
                "country_count": len(countries),
                "is_international": len(countries) > 1,
                "ref_count":     refs,
                "has_email":     has_email,
                "char_count":    len(text),
            })
            ok += 1
        print(f"✓", flush=True)

    df = pd.DataFrame(records)
    out = os.path.join(RESULTS_DIR, f"pdf_metadata_{name}.csv")
    df.to_csv(out, index=False)
    print(f"  Salvo: {out}  ({len(df)} linhas)")
    return df


def print_summary(df: pd.DataFrame, name: str):
    print(f"\n  === {name.upper()} — resumo por ano ===")
    summary = df.groupby("year").agg(
        papers=("filename", "count"),
        avg_pages=("page_count", "mean"),
        avg_authors=("author_count", "mean"),
        pct_international=("is_international", "mean"),
        avg_refs=("ref_count", "mean"),
    ).round(2)
    print(summary.to_string())


def main():
    for name in ["sbbd", "vldb"]:
        print(f"\n{'='*60}")
        print(f"Extraindo metadados dos PDFs: {name.upper()}")
        print(f"{'='*60}")
        df = process_conference(name)
        print_summary(df, name)

    print("\n=== Extração de PDFs concluída ===")


if __name__ == "__main__":
    main()
