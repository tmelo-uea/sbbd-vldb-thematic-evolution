#!/usr/bin/env python3
"""
Refina os nomes dos tópicos gerados pelo BERTopic usando a API da Anthropic.
Para cada tópico, envia palavras-chave + documentos representativos ao Claude
e recebe um nome temático conciso em inglês.
"""

import os
import json
import time
import pandas as pd
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "chaves.env"))

BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CORPUS_FILES = {
    "sbbd": os.path.join(BASE_DIR, "corpus.jsonl"),
    "vldb": os.path.join(BASE_DIR, "vldb_corpus.jsonl"),
}

client = anthropic.Anthropic()

PROMPT_TEMPLATE = """You are a database research expert. Below are the top keywords and representative excerpts from a topic cluster found in a corpus of database research papers.

Top keywords: {keywords}

Representative excerpts:
{excerpts}

Based on these, provide a concise topic label (3-6 words) in English that best captures the research theme.
Reply with ONLY the label, nothing else."""


def load_corpus(path: str) -> list[str]:
    texts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            texts.append(json.loads(line)["text"])
    return texts


def get_topic_label(keywords: str, excerpts: list[str]) -> str:
    excerpt_text = "\n---\n".join(
        e[:500] for e in excerpts[:3]
    )
    prompt = PROMPT_TEMPLATE.format(
        keywords=keywords,
        excerpts=excerpt_text,
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=32,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def refine_conference(name: str):
    print(f"\n=== Refinando tópicos: {name.upper()} ===")

    topic_info = pd.read_csv(os.path.join(RESULTS_DIR, name, "topic_info.csv"))
    docs_topics = pd.read_csv(os.path.join(RESULTS_DIR, name, "docs_topics.csv"))
    texts = load_corpus(CORPUS_FILES[name])

    topics = topic_info[topic_info["Topic"] != -1].copy()
    refined_labels = {}

    for _, row in topics.iterrows():
        topic_id = row["Topic"]
        keywords = row["Name"]

        # Documentos representativos deste tópico
        doc_indices = docs_topics[docs_topics["topic"] == topic_id].index.tolist()
        excerpts = [texts[i] for i in doc_indices[:3] if i < len(texts)]

        print(f"  Tópico {topic_id} ({row['Count']} docs)...", end=" ", flush=True)
        try:
            label = get_topic_label(keywords, excerpts)
            refined_labels[topic_id] = label
            print(f'"{label}"')
        except Exception as e:
            refined_labels[topic_id] = keywords
            print(f"ERRO: {e}")

        time.sleep(0.3)

    # Salva mapeamento
    output = os.path.join(RESULTS_DIR, name, "refined_labels.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(refined_labels, f, ensure_ascii=False, indent=2)

    # Atualiza topic_info com os novos labels
    topic_info["RefinedName"] = topic_info["Topic"].map(
        lambda t: refined_labels.get(t, row["Name"] if t != -1 else "Outliers")
    )
    topic_info.to_csv(
        os.path.join(RESULTS_DIR, name, "topic_info.csv"), index=False
    )

    print(f"  Salvo em: {output}")


def main():
    for name in ["sbbd", "vldb"]:
        refine_conference(name)
    print("\n=== Refinamento concluído ===")


if __name__ == "__main__":
    main()
