#!/usr/bin/env python3
"""
Análise bibliométrica comparativa SBBD x VLDB (2016–2025).

Gera gráficos e estatísticas a partir de:
  - results/bibliometrics_comparison.csv  (tabela principal por ano)
  - results/s2_sbbd.csv                   (metadados S2 por artigo SBBD)
  - results/openalex_vldb.csv             (metadados OpenAlex por artigo VLDB)

Saída (plots/):
  bib_growth.pdf          — crescimento do número de artigos por ano
  bib_citations.pdf       — citações médias por ano
  bib_authors.pdf         — média de autores por artigo
  bib_intl.pdf            — % de colaboração internacional
  bib_pages.pdf           — média de páginas por artigo
  bib_oa.pdf              — % open access
  bib_overview.pdf        — painel 2×3 com todas as métricas
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

BASE_DIR   = os.path.dirname(__file__)
RESULTS    = os.path.join(BASE_DIR, "results")
PLOTS      = os.path.join(BASE_DIR, "plots")
os.makedirs(PLOTS, exist_ok=True)

YEARS = list(range(2016, 2026))
BLUE  = "#1f77b4"   # SBBD
ORANGE = "#ff7f0e"  # VLDB

# ---------------------------------------------------------------------------
# Carrega dados
# ---------------------------------------------------------------------------
bib = pd.read_csv(os.path.join(RESULTS, "bibliometrics_comparison.csv"))
bib = bib.set_index("Ano").reindex(YEARS)

s2  = pd.read_csv(os.path.join(RESULTS, "s2_sbbd.csv"))
oa  = pd.read_csv(os.path.join(RESULTS, "openalex_vldb.csv"))


def savefig(name: str):
    path = os.path.join(PLOTS, name)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    # Salva também em PNG com alta resolução
    png_path = os.path.join(PLOTS, name.replace(".pdf", ".png"))
    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  {path}")
    print(f"  {png_path}")


# ---------------------------------------------------------------------------
# 1. Crescimento — número de artigos
# ---------------------------------------------------------------------------
def plot_growth():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(YEARS, bib["SBBD_artigos"], "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, bib["VLDB_artigos"], "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Número de artigos")
    ax.set_title("Crescimento do número de artigos (2016–2025)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_growth.pdf")


# ---------------------------------------------------------------------------
# 2. Citações médias por ano
# ---------------------------------------------------------------------------
def plot_citations():
    fig, ax = plt.subplots(figsize=(8, 4))
    sbbd_cit = bib["SBBD_citacoes_media"]
    vldb_cit = bib["VLDB_citacoes_media"]
    ax.plot(YEARS, sbbd_cit, "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, vldb_cit, "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Citações médias por artigo")
    ax.set_title("Citações médias por artigo (2016–2025)\n"
                 "(anos recentes têm menos citações por serem mais novos)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_citations.pdf")


# ---------------------------------------------------------------------------
# 3. Média de autores por artigo
# ---------------------------------------------------------------------------
def plot_authors():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(YEARS, bib["SBBD_autores"], "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, bib["VLDB_autores"], "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Média de autores por artigo")
    ax.set_title("Média de autores por artigo (2016–2025)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_authors.pdf")


# ---------------------------------------------------------------------------
# 4. % colaboração internacional
# ---------------------------------------------------------------------------
def plot_intl():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(YEARS, bib["SBBD_pct_intl"], "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, bib["VLDB_pct_intl"], "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("% artigos com colaboração internacional")
    ax.set_title("Colaboração internacional (2016–2025)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_intl.pdf")


# ---------------------------------------------------------------------------
# 5. Média de páginas
# ---------------------------------------------------------------------------
def plot_pages():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(YEARS, bib["SBBD_paginas"], "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, bib["VLDB_paginas"], "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Média de páginas por artigo")
    ax.set_title("Média de páginas por artigo (2016–2025)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_pages.pdf")


# ---------------------------------------------------------------------------
# 6. % Open Access
# ---------------------------------------------------------------------------
def plot_oa():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(YEARS, bib["SBBD_pct_oa"], "o-", color=BLUE,   label="SBBD", linewidth=2)
    ax.plot(YEARS, bib["VLDB_pct_oa"], "s--", color=ORANGE, label="VLDB", linewidth=2)
    ax.set_xlabel("Ano")
    ax.set_ylabel("% artigos Open Access")
    ax.set_title("Taxa de Open Access (2016–2025)\n"
                 "(SBBD 100% via SBC Open Library; VLDB: variável)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    savefig("bib_oa.pdf")


# ---------------------------------------------------------------------------
# 7. Painel geral (2×3)
# ---------------------------------------------------------------------------
def plot_overview():
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    axes = axes.flatten()

    panels = [
        ("SBBD_artigos",        "VLDB_artigos",        "Papers per year"),
        ("SBBD_citacoes_media", "VLDB_citacoes_media", "Avg. citations per paper"),
        ("SBBD_autores",        "VLDB_autores",        "Avg. authors per paper"),
        ("SBBD_paginas",        "VLDB_paginas",        "Avg. pages per paper"),
        ("SBBD_pct_intl",       "VLDB_pct_intl",       "Intl. collaboration (%)"),
        ("SBBD_pct_oa",         "VLDB_pct_oa",         "Open Access (%)"),
    ]

    for ax, (sc, vc, title) in zip(axes, panels):
        ax.plot(YEARS, bib[sc], "o-", color=BLUE,   label="SBBD", linewidth=1.8)
        ax.plot(YEARS, bib[vc], "s--", color=ORANGE, label="VLDB", linewidth=1.8)
        ax.set_title(title, fontsize=16)
        ax.set_xticks(YEARS)
        ax.tick_params(axis="x", rotation=45, labelsize=14)
        ax.tick_params(axis="y", labelsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=14)
    plt.tight_layout()
    savefig("bib_overview.pdf")


# ---------------------------------------------------------------------------
# 8. Estatísticas resumidas
# ---------------------------------------------------------------------------
def print_summary():
    print("\n=== Médias da década (2016–2025) ===")
    metrics = [
        ("Artigos/ano",          "SBBD_artigos",        "VLDB_artigos"),
        ("Citações médias",      "SBBD_citacoes_media", "VLDB_citacoes_media"),
        ("Autores/artigo",       "SBBD_autores",        "VLDB_autores"),
        ("Páginas/artigo",       "SBBD_paginas",        "VLDB_paginas"),
        ("% Intl.",              "SBBD_pct_intl",       "VLDB_pct_intl"),
        ("% OA",                 "SBBD_pct_oa",         "VLDB_pct_oa"),
    ]
    for label, sc, vc in metrics:
        sm = bib[sc].mean()
        vm = bib[vc].mean()
        print(f"  {label:<20} SBBD={sm:6.2f}  VLDB={vm:6.2f}  "
              f"ratio={sm/vm:.2f}" if vm else f"  {label:<20} SBBD={sm:6.2f}  VLDB=N/A")

    # Crescimento SBBD: CAGR 2016→2025
    y0, y1 = bib.loc[2016, "SBBD_artigos"], bib.loc[2025, "SBBD_artigos"]
    cagr = (y1 / y0) ** (1/9) - 1
    print(f"\n  CAGR artigos SBBD (2016→2025): {cagr*100:.1f}%/ano")

    y0, y1 = bib.loc[2016, "VLDB_artigos"], bib.loc[2025, "VLDB_artigos"]
    cagr = (y1 / y0) ** (1/9) - 1
    print(f"  CAGR artigos VLDB (2016→2025): {cagr*100:.1f}%/ano")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Gerando gráficos bibliométricos...")
    plot_growth()
    plot_citations()
    plot_authors()
    plot_intl()
    plot_pages()
    plot_oa()
    plot_overview()
    print_summary()
    print("\nConcluído.")
