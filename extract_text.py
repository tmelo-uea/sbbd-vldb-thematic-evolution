#!/usr/bin/env python3
"""
Extrai texto dos PDFs do SBBD (2016-2025) e gera:
  - corpus.jsonl  : um JSON por linha com {year, filename, text}
  - corpus_stats.txt : estatísticas da extração

PDFs com texto nativo são extraídos diretamente via pymupdf.
PDFs de imagem (escaneados) passam por OCR via Tesseract.
"""

import os
import re
import json
import io
import fitz  # pymupdf
import pytesseract
from PIL import Image

PDFS_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "corpus.jsonl")
STATS_FILE = os.path.join(os.path.dirname(__file__), "corpus_stats.txt")

# Padrões para remover ruído comum em PDFs acadêmicos
NOISE_PATTERNS = [
    r'\n{3,}',                          # Múltiplas quebras de linha
    r'(?i)anais do\s+\w+\s+simpósio.*', # Cabeçalho dos anais
    r'(?i)proceedings of.*',            # Cabeçalho em inglês
    r'(?i)issn\s+[\d\-]+',             # ISSN
    r'(?i)doi:\s*\S+',                 # DOI inline
    r'http\S+',                         # URLs
    r'\x0c',                            # Form feed (quebra de página)
]


def clean_text(text: str) -> str:
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, ' ', text)
    # Normaliza espaços
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    text = text.strip()
    return text


def extract_pdf(path: str) -> tuple[str, str]:
    """
    Extrai texto de um PDF.
    Retorna (texto, método) onde método é 'native' ou 'ocr'.
    """
    try:
        doc = fitz.open(path)
        pages_text = [page.get_text("text") for page in doc]
        full_text = "\n".join(pages_text)

        if len(full_text.strip()) >= 200:
            doc.close()
            return full_text, "native"

        # PDF de imagem — aplica OCR
        ocr_pages = []
        mat = fitz.Matrix(2, 2)  # zoom 2x para melhor qualidade
        for page in doc:
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_pages.append(pytesseract.image_to_string(img, lang="eng"))
        doc.close()
        return "\n".join(ocr_pages), "ocr"
    except Exception as e:
        return "", "error"


def main():
    years = sorted(
        int(d) for d in os.listdir(PDFS_DIR)
        if os.path.isdir(os.path.join(PDFS_DIR, d)) and d.isdigit()
    )

    stats = []
    total_ok = 0
    total_fail = 0
    total_chars = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for year in years:
            year_dir = os.path.join(PDFS_DIR, str(year))
            pdfs = sorted(f for f in os.listdir(year_dir) if f.endswith(".pdf"))
            ok = fail = 0

            print(f"\n{year}: {len(pdfs)} PDFs", flush=True)

            for fname in pdfs:
                fpath = os.path.join(year_dir, fname)
                raw, method = extract_pdf(fpath)
                text = clean_text(raw)

                if len(text) < 200:
                    print(f"  [VAZIO] {fname}", flush=True)
                    fail += 1
                    total_fail += 1
                    continue

                record = {"year": year, "filename": fname, "method": method, "text": text}
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                ok += 1
                total_ok += 1
                total_chars += len(text)

            year_stat = f"{year}: {ok} ok, {fail} falhas"
            stats.append(year_stat)
            print(f"  => {year_stat}", flush=True)

    avg_chars = total_chars // total_ok if total_ok else 0
    summary = (
        f"Total: {total_ok} artigos extraídos, {total_fail} falhas\n"
        f"Caracteres totais: {total_chars:,}\n"
        f"Média por artigo: {avg_chars:,} caracteres\n\n"
        + "\n".join(stats)
    )

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\n=== {summary} ===")
    print(f"Corpus salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
