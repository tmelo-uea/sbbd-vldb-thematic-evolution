#!/usr/bin/env python3
"""
Baixa todos os artigos em PDF do SBBD (2016-2025) da SBC Open Library.
Organiza os arquivos em subpastas por ano dentro de pdfs/.
"""

import os
import re
import time
import urllib.request
from urllib.error import URLError, HTTPError

BASE_URL = "https://sol.sbc.org.br/index.php/sbbd"

ISSUES = {
    2025: 1577,
    2024: 1371,
    2023: 1145,
    2022: 987,
    2021: 843,
    2020: 682,
    2019: 484,
    2018: 1005,
    2017: 1092,
    2016: 1093,
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_pdf_links(issue_id):
    """Retorna lista de (article_id, pdf_id) da página do volume."""
    url = f"{BASE_URL}/issue/view/{issue_id}"
    html = fetch_html(url)
    # Links no formato /article/view/ARTICLE_ID/PDF_ID
    pairs = re.findall(r'/article/view/(\d+)/(\d+)', html)
    # Remove duplicatas mantendo ordem
    seen = set()
    result = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            result.append(pair)
    return result


def download_pdf(article_id, pdf_id, dest_path):
    """Baixa o PDF e salva em dest_path. Retorna True se bem-sucedido."""
    url = f"{BASE_URL}/article/download/{article_id}/{pdf_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
        if b"%PDF" not in data[:10] and "pdf" not in content_type.lower():
            print(f"  [AVISO] Resposta não é PDF: {content_type}")
            return False
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except (HTTPError, URLError) as e:
        print(f"  [ERRO] {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_ok = 0
    total_fail = 0

    for year in sorted(ISSUES.keys()):
        issue_id = ISSUES[year]
        year_dir = os.path.join(OUTPUT_DIR, str(year))
        os.makedirs(year_dir, exist_ok=True)

        print(f"\n=== {year} (issue {issue_id}) ===")
        try:
            pairs = get_pdf_links(issue_id)
        except Exception as e:
            print(f"  [ERRO] Falha ao obter links: {e}")
            continue

        print(f"  {len(pairs)} artigos encontrados")

        for i, (article_id, pdf_id) in enumerate(pairs, 1):
            filename = f"{article_id}_{pdf_id}.pdf"
            dest = os.path.join(year_dir, filename)

            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                print(f"  [{i}/{len(pairs)}] Já existe: {filename}")
                total_ok += 1
                continue

            print(f"  [{i}/{len(pairs)}] Baixando {article_id}/{pdf_id}...", end=" ")
            ok = download_pdf(article_id, pdf_id, dest)
            if ok:
                size_kb = os.path.getsize(dest) // 1024
                print(f"OK ({size_kb} KB)")
                total_ok += 1
            else:
                total_fail += 1
            time.sleep(0.5)  # Evita sobrecarregar o servidor

    print(f"\n=== Concluído: {total_ok} baixados, {total_fail} falhas ===")


if __name__ == "__main__":
    main()
