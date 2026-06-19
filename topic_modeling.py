#!/usr/bin/env python3
"""
Topic modeling com BERTopic para análise comparativa SBBD x VLDB.

Gera dois modelos (um por conferência) com análise temporal por ano.
Salva os resultados em results/sbbd/ e results/vldb/
"""

import os
import json
import numpy as np
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from bertopic.representation import KeyBERTInspired
from hdbscan import HDBSCAN
from umap import UMAP
from sklearn.feature_extraction.text import CountVectorizer

BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")

CORPORA = {
    "sbbd": os.path.join(BASE_DIR, "corpus.jsonl"),
    "vldb": os.path.join(BASE_DIR, "vldb_corpus.jsonl"),
}

# Modelo multilíngue
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Parâmetros HDBSCAN por corpus
HDBSCAN_PARAMS = {
    "sbbd": {"min_cluster_size": 5, "min_samples": 2},
    "vldb": {"min_cluster_size": 15, "min_samples": 5},
}


def load_corpus(path: str) -> tuple[list[str], list[int]]:
    """Carrega textos e anos do corpus JSONL."""
    texts, years = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            texts.append(rec["text"])
            years.append(rec["year"])
    return texts, years


def build_model(embedding_model, hdbscan_params: dict) -> BERTopic:
    """Configura e retorna um modelo BERTopic."""
    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=hdbscan_params["min_cluster_size"],
        min_samples=hdbscan_params["min_samples"],
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(
        stop_words=None,  # multilíngue — não usa stop words fixas
        min_df=2,
        ngram_range=(1, 2),
    )
    representation_model = KeyBERTInspired()

    return BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        representation_model=representation_model,
        calculate_probabilities=False,
        verbose=True,
    )


def save_results(model: BERTopic, texts, years, name: str):
    """Salva tópicos, distribuição temporal e visualizações."""
    out_dir = os.path.join(RESULTS_DIR, name)
    os.makedirs(out_dir, exist_ok=True)

    # Informações dos tópicos
    topic_info = model.get_topic_info()
    topic_info.to_csv(os.path.join(out_dir, "topic_info.csv"), index=False)
    print(f"  {len(topic_info) - 1} tópicos encontrados (excluindo outliers)")

    # Documentos com tópicos atribuídos
    topics, _ = model.transform(texts)
    docs_df = pd.DataFrame({"year": years, "topic": topics})
    docs_df.to_csv(os.path.join(out_dir, "docs_topics.csv"), index=False)

    # Distribuição de tópicos por ano
    topics_over_time = model.topics_over_time(
        texts, years, nr_bins=len(set(years))
    )
    topics_over_time.to_csv(
        os.path.join(out_dir, "topics_over_time.csv"), index=False
    )

    # Visualização HTML — tópicos ao longo do tempo
    try:
        fig_tot = model.visualize_topics_over_time(topics_over_time, top_n_topics=20)
        fig_tot.write_html(os.path.join(out_dir, "topics_over_time.html"))

        fig_topics = model.visualize_topics()
        fig_topics.write_html(os.path.join(out_dir, "topics_map.html"))

        fig_heatmap = model.visualize_heatmap()
        fig_heatmap.write_html(os.path.join(out_dir, "topics_heatmap.html"))
    except Exception as e:
        print(f"  [AVISO] Erro ao gerar visualizações: {e}")

    # Salva modelo
    model.save(
        os.path.join(out_dir, "model"),
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=EMBEDDING_MODEL,
    )

    print(f"  Resultados salvos em: {out_dir}")


def run(name: str, corpus_path: str, embedding_model):
    print(f"\n{'='*60}")
    print(f"Processando: {name.upper()}")
    print(f"{'='*60}")

    print("Carregando corpus...")
    texts, years = load_corpus(corpus_path)
    print(f"  {len(texts)} documentos, {len(set(years))} anos ({min(years)}–{max(years)})")

    embeddings_path = os.path.join(RESULTS_DIR, f"{name}_embeddings.npy")
    if os.path.exists(embeddings_path):
        print("Carregando embeddings existentes...")
        embeddings = np.load(embeddings_path)
    else:
        print("Gerando embeddings...")
        embeddings = embedding_model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            device="cuda",
        )
        np.save(embeddings_path, embeddings)
    print(f"  Embeddings shape: {embeddings.shape}")

    print("Treinando BERTopic...")
    hdbscan_params = HDBSCAN_PARAMS[name]
    print(f"  HDBSCAN params: {hdbscan_params}")
    model = build_model(embedding_model, hdbscan_params)
    topics, probs = model.fit_transform(texts, embeddings)

    print("Salvando resultados...")
    save_results(model, texts, years, name)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Carregando modelo de embeddings...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL, device="cuda")

    for name, corpus_path in CORPORA.items():
        if not os.path.exists(corpus_path):
            print(f"[AVISO] Corpus não encontrado: {corpus_path}")
            continue
        run(name, corpus_path, embedding_model)

    print("\n=== Análise concluída ===")
    print(f"Resultados em: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
