#!/usr/bin/env python3
"""
Análise comparativa entre SBBD e VLDB:
- Alinhamento semântico de tópicos entre os dois corpora
- Defasagem temporal (lag) de absorção de tópicos
- Tópicos exclusivos de cada conferência
- Gráficos comparativos
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

YEARS = list(range(2016, 2026))
SIMILARITY_THRESHOLD = 0.60  # limiar para considerar tópicos equivalentes


def load_evolution(name: str) -> pd.DataFrame:
    return pd.read_csv(
        os.path.join(RESULTS_DIR, name, "topic_evolution.csv"), index_col=0
    )


def load_labels(name: str) -> dict:
    with open(os.path.join(RESULTS_DIR, name, "refined_labels.json")) as f:
        return {int(k): v for k, v in json.load(f).items()}


def align_topics(sbbd_labels: list, vldb_labels: list, model) -> pd.DataFrame:
    """Calcula similaridade semântica entre todos os pares de tópicos SBBD x VLDB."""
    sbbd_emb = model.encode(sbbd_labels)
    vldb_emb = model.encode(vldb_labels)
    sim_matrix = cosine_similarity(sbbd_emb, vldb_emb)
    df = pd.DataFrame(sim_matrix, index=sbbd_labels, columns=vldb_labels)
    return df


def find_best_matches(sim_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Para cada tópico SBBD, encontra o melhor par no VLDB acima do limiar."""
    matches = []
    for sbbd_topic in sim_df.index:
        best_vldb = sim_df.loc[sbbd_topic].idxmax()
        best_sim = sim_df.loc[sbbd_topic].max()
        matches.append({
            "sbbd_topic": sbbd_topic,
            "vldb_topic": best_vldb,
            "similarity": best_sim,
            "matched": best_sim >= threshold,
        })
    return pd.DataFrame(matches).sort_values("similarity", ascending=False)


def compute_lag(sbbd_ev: pd.DataFrame, vldb_ev: pd.DataFrame,
                sbbd_topic: str, vldb_topic: str) -> int:
    """
    Estima a defasagem temporal (anos) entre a emergência de um tópico no VLDB
    e sua aparição no SBBD. Usa o ano de maior crescimento como proxy.
    """
    if sbbd_topic not in sbbd_ev.index or vldb_topic not in vldb_ev.index:
        return None
    sbbd_row = sbbd_ev.loc[sbbd_topic]
    vldb_row = vldb_ev.loc[vldb_topic]
    sbbd_peak = sbbd_row.idxmax()
    vldb_peak = vldb_row.idxmax()
    return int(sbbd_peak) - int(vldb_peak)


def plot_alignment_heatmap(sim_df: pd.DataFrame):
    """Heatmap de similaridade semântica SBBD x VLDB."""
    fig, ax = plt.subplots(figsize=(16, 10))
    im = ax.imshow(sim_df.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(sim_df.columns)))
    ax.set_xticklabels(sim_df.columns, rotation=90, fontsize=6)
    ax.set_yticks(range(len(sim_df.index)))
    ax.set_yticklabels(sim_df.index, fontsize=7)
    plt.colorbar(im, ax=ax, label="Similaridade semântica")
    ax.set_title("Alinhamento Semântico de Tópicos: SBBD x VLDB")
    ax.set_xlabel("Tópicos VLDB")
    ax.set_ylabel("Tópicos SBBD")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "alignment_heatmap.pdf")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {path}")


def plot_matched_evolution(matches: pd.DataFrame,
                           sbbd_ev: pd.DataFrame, vldb_ev: pd.DataFrame,
                           top_n: int = 6):
    """Para os top N pares alinhados, plota evolução SBBD vs VLDB lado a lado."""
    matched = matches[matches["matched"]].head(top_n)
    fig, axes = plt.subplots(top_n, 1, figsize=(12, top_n * 2.5), sharex=True)

    for ax, (_, row) in zip(axes, matched.iterrows()):
        st, vt = row["sbbd_topic"], row["vldb_topic"]
        if st in sbbd_ev.index:
            ax.plot(YEARS, sbbd_ev.loc[st].values, "o-", color="tab:blue",
                    label="SBBD", linewidth=2)
        if vt in vldb_ev.index:
            ax.plot(YEARS, vldb_ev.loc[vt].values, "s--", color="tab:orange",
                    label="VLDB", linewidth=2)
        ax.set_ylabel("% artigos", fontsize=8)
        ax.set_title(f'SBBD: "{st}"\nVLDB: "{vt}" (sim={row["similarity"]:.2f})',
                     fontsize=8)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(YEARS)

    axes[-1].set_xlabel("Ano")
    plt.suptitle("Evolução Comparativa: Tópicos Alinhados SBBD x VLDB", fontsize=11)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "matched_evolution.pdf")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {path}")


def plot_exclusive_topics(matches: pd.DataFrame,
                          sbbd_ev: pd.DataFrame, vldb_ev: pd.DataFrame):
    """Evolução dos tópicos exclusivos de cada conferência (sem par semântico)."""
    unmatched_sbbd = matches[~matches["matched"]]["sbbd_topic"].tolist()
    matched_vldb = matches[matches["matched"]]["vldb_topic"].tolist()
    unmatched_vldb = [t for t in vldb_ev.index if t not in matched_vldb]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # SBBD exclusivos
    colors = plt.cm.tab10(np.linspace(0, 1, len(unmatched_sbbd)))
    for topic, color in zip(unmatched_sbbd, colors):
        if topic in sbbd_ev.index:
            ax1.plot(YEARS, sbbd_ev.loc[topic].values, "o-",
                     label=topic, color=color, linewidth=1.5)
    ax1.set_title("Tópicos exclusivos do SBBD\n(sem par semântico no VLDB)")
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("% artigos no ano")
    ax1.legend(fontsize=6, bbox_to_anchor=(1.05, 1), loc="upper left")
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(YEARS)
    ax1.tick_params(axis='x', rotation=45)

    # VLDB exclusivos (top 10 por volume)
    vldb_top_excl = [t for t in unmatched_vldb if t in vldb_ev.index]
    vldb_top_excl = sorted(vldb_top_excl,
                           key=lambda t: vldb_ev.loc[t].sum(), reverse=True)[:10]
    colors2 = plt.cm.tab10(np.linspace(0, 1, len(vldb_top_excl)))
    for topic, color in zip(vldb_top_excl, colors2):
        ax2.plot(YEARS, vldb_ev.loc[topic].values, "s--",
                 label=topic, color=color, linewidth=1.5)
    ax2.set_title("Tópicos exclusivos do VLDB\n(sem par semântico no SBBD) — Top 10")
    ax2.set_xlabel("Ano")
    ax2.legend(fontsize=6, bbox_to_anchor=(1.05, 1), loc="upper left")
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(YEARS)
    ax2.tick_params(axis='x', rotation=45)

    plt.suptitle("Tópicos Exclusivos por Conferência", fontsize=12)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "exclusive_topics.pdf")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {path}")


def main():
    print("Carregando dados...")
    sbbd_ev = load_evolution("sbbd")
    vldb_ev = load_evolution("vldb")
    sbbd_labels = list(sbbd_ev.index)
    vldb_labels = list(vldb_ev.index)

    print("Calculando alinhamento semântico...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    sim_df = align_topics(sbbd_labels, vldb_labels, model)

    print("Identificando pares alinhados...")
    matches = find_best_matches(sim_df, SIMILARITY_THRESHOLD)
    matches_path = os.path.join(RESULTS_DIR, "topic_matches.csv")
    matches.to_csv(matches_path, index=False)

    print("\n=== Tópicos SBBD com par no VLDB ===")
    matched = matches[matches["matched"]]
    for _, r in matched.iterrows():
        lag = compute_lag(sbbd_ev, vldb_ev, r["sbbd_topic"], r["vldb_topic"])
        lag_str = f"lag={lag:+d} anos" if lag is not None else ""
        print(f"  [{r['similarity']:.2f}] {r['sbbd_topic']}\n"
              f"         => {r['vldb_topic']} {lag_str}")

    print(f"\n=== Tópicos SBBD SEM par no VLDB ===")
    unmatched = matches[~matches["matched"]]
    for _, r in unmatched.iterrows():
        print(f"  [{r['similarity']:.2f}] {r['sbbd_topic']}")

    print("\nGerando visualizações...")
    plot_alignment_heatmap(sim_df)
    plot_matched_evolution(matches, sbbd_ev, vldb_ev)
    plot_exclusive_topics(matches, sbbd_ev, vldb_ev)

    print(f"\n=== Resumo ===")
    print(f"  Tópicos SBBD: {len(sbbd_labels)}")
    print(f"  Tópicos VLDB: {len(vldb_labels)}")
    print(f"  Pares alinhados (sim >= {SIMILARITY_THRESHOLD}): {len(matched)}")
    print(f"  Tópicos SBBD sem par: {len(unmatched)}")
    print(f"  Resultados em: {RESULTS_DIR}/topic_matches.csv")


if __name__ == "__main__":
    main()
