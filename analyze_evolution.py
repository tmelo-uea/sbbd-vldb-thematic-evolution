#!/usr/bin/env python3
"""
Analisa a evolução temporal dos tópicos por conferência e gera:
- Tabelas de frequência relativa por ano
- Gráficos de evolução temporal
- Análise comparativa SBBD x VLDB
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

YEARS = list(range(2016, 2026))


def load_data(name: str):
    topic_info = pd.read_csv(os.path.join(RESULTS_DIR, name, "topic_info.csv"))
    docs_topics = pd.read_csv(os.path.join(RESULTS_DIR, name, "docs_topics.csv"))
    with open(os.path.join(RESULTS_DIR, name, "refined_labels.json")) as f:
        labels = {int(k): v for k, v in json.load(f).items()}
    # Mapeia id -> label refinado
    topic_info["Label"] = topic_info["Topic"].map(
        lambda t: labels.get(t, "Outliers")
    )
    return topic_info, docs_topics, labels


def build_frequency_table(docs_topics: pd.DataFrame, labels: dict) -> pd.DataFrame:
    """Frequência relativa de cada tópico por ano (% dos docs daquele ano)."""
    df = docs_topics[docs_topics["topic"] != -1].copy()
    df["label"] = df["topic"].map(labels)

    # Contagem por ano e tópico
    counts = df.groupby(["year", "label"]).size().reset_index(name="count")
    totals = df.groupby("year").size().reset_index(name="total")
    counts = counts.merge(totals, on="year")
    counts["freq"] = counts["count"] / counts["total"] * 100

    # Pivot
    pivot = counts.pivot(index="label", columns="year", values="freq").fillna(0)
    # Garante todos os anos
    for y in YEARS:
        if y not in pivot.columns:
            pivot[y] = 0
    return pivot[YEARS]


def plot_heatmap(pivot: pd.DataFrame, name: str, title: str):
    """Heatmap de frequência relativa tópico x ano."""
    fig, ax = plt.subplots(figsize=(14, max(8, len(pivot) * 0.4)))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels(YEARS, rotation=45)
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    plt.colorbar(im, ax=ax, label="% de artigos no ano")
    ax.set_title(title)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"{name}_heatmap.pdf")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {path}")


def plot_top_evolution(pivot: pd.DataFrame, name: str, title: str, top_n: int = 12):
    """Evolução temporal dos top N tópicos mais frequentes."""
    top_topics = pivot.sum(axis=1).nlargest(top_n).index
    subset = pivot.loc[top_topics]

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = cm.tab20(np.linspace(0, 1, top_n))
    for i, (topic, row) in enumerate(subset.iterrows()):
        ax.plot(YEARS, row.values, marker="o", label=topic, color=colors[i], linewidth=2)

    ax.set_xlabel("Ano")
    ax.set_ylabel("% de artigos no ano")
    ax.set_title(title)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=7)
    ax.set_xticks(YEARS)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"{name}_evolution.pdf")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {path}")


def compute_trends(pivot: pd.DataFrame) -> pd.DataFrame:
    """Calcula tendência (slope linear) de cada tópico ao longo dos anos."""
    trends = []
    x = np.array(YEARS) - YEARS[0]
    for topic, row in pivot.iterrows():
        y = row.values.astype(float)
        slope = np.polyfit(x, y, 1)[0]
        mean = y.mean()
        trends.append({"topic": topic, "mean_freq": mean, "trend": slope})
    return pd.DataFrame(trends).sort_values("trend", ascending=False)


def save_csv(pivot: pd.DataFrame, name: str):
    path = os.path.join(RESULTS_DIR, name, "topic_evolution.csv")
    pivot.to_csv(path)
    print(f"  Salvo: {path}")


def main():
    for name, conf_name in [("sbbd", "SBBD"), ("vldb", "VLDB")]:
        print(f"\n=== {conf_name} ===")
        topic_info, docs_topics, labels = load_data(name)

        pivot = build_frequency_table(docs_topics, labels)
        save_csv(pivot, name)

        plot_heatmap(pivot, name, f"{conf_name} — Frequência de Tópicos por Ano (%)")
        plot_top_evolution(pivot, name, f"{conf_name} — Evolução dos Top 12 Tópicos")

        trends = compute_trends(pivot)
        trends.to_csv(os.path.join(RESULTS_DIR, name, "topic_trends.csv"), index=False)

        print(f"\n  Tópicos em crescimento:")
        print(trends.head(5).to_string(index=False))
        print(f"\n  Tópicos em declínio:")
        print(trends.tail(5).to_string(index=False))

    print(f"\n=== Análise concluída. Gráficos em: {PLOTS_DIR} ===")


if __name__ == "__main__":
    main()
