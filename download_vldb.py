#!/usr/bin/env python3
"""
Baixa todos os artigos do VLDB (volumes 9-18, anos 2016-2025).
Organiza em vldb_pdfs/<ano>/
"""

import os
import re
import time
import urllib.request
from urllib.error import URLError, HTTPError

# PVLDB volumes e anos correspondentes ao VLDB conference
VOLUMES = {
    9:  2016,
    10: 2017,
    11: 2018,
    12: 2019,
    13: 2020,
    14: 2021,
    15: 2022,
    16: 2023,
    17: 2024,
    18: 2025,
}

BASE_PDF_URL = "https://vldb.org/pvldb/vol{vol}/{filename}"
VOL_INDEX_URL = "https://vldb.org/pvldb/vol{vol}/"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "vldb_pdfs")

HEADERS = {"User-Agent": "Mozilla/5.0 (research/academic use)"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def get_pdf_filenames(vol):
    """Extrai nomes dos PDFs da página de índice do volume."""
    url = VOL_INDEX_URL.format(vol=vol)
    html = fetch(url)
    # Padrão: p<número>-<nome>.pdf
    filenames = re.findall(r'(p\d+-[a-zA-Z0-9_\-]+\.pdf)', html)
    # Remove duplicatas mantendo ordem
    seen = set()
    result = []
    for f in filenames:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def download_pdf(vol, filename, dest_path):
    url = BASE_PDF_URL.format(vol=vol, filename=filename)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 1000:
            return False
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except (HTTPError, URLError) as e:
        print(f"  [ERRO] {url}: {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_ok = total_fail = 0

    for vol, year in sorted(VOLUMES.items()):
        year_dir = os.path.join(OUTPUT_DIR, str(year))
        os.makedirs(year_dir, exist_ok=True)

        print(f"\n=== Vol {vol} / {year} ===", flush=True)
        try:
            filenames = get_pdf_filenames(vol)
        except Exception as e:
            print(f"  [ERRO] Falha ao obter índice: {e}")
            continue

        print(f"  {len(filenames)} PDFs encontrados", flush=True)

        for i, fname in enumerate(filenames, 1):
            dest = os.path.join(year_dir, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                print(f"  [{i}/{len(filenames)}] Já existe: {fname}")
                total_ok += 1
                continue

            print(f"  [{i}/{len(filenames)}] {fname}...", end=" ", flush=True)
            ok = download_pdf(vol, fname, dest)
            if ok:
                size_kb = os.path.getsize(dest) // 1024
                print(f"OK ({size_kb} KB)")
                total_ok += 1
            else:
                print("FALHOU")
                total_fail += 1
            time.sleep(0.3)

    print(f"\n=== Concluído: {total_ok} baixados, {total_fail} falhas ===")


if __name__ == "__main__":
    main()
