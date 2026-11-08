import json
import os
import re
from pathlib import Path
from collections import Counter

from dotenv import load_dotenv

from knowledge_base.src.embedders.qwen_embedder import QwenEmbedder
from retrieval_service.src.retrieval.pg_retriever import PGRetriever


# This file is expected at retrieval_service/src/evaluation/evaluate_retrieval.py
BASE_DIR = Path(__file__).resolve().parents[2]  # retrieval_service
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tokenize(text: str) -> set[str]:
    # Simple lexical matching; this is an initial diagnostic, not a semantic metric.
    return set(re.findall(r"\w+", text.lower(), flags=re.UNICODE))


def evidence_recall(evidence: str, chunk: str) -> float:
    evidence_tokens = tokenize(evidence)
    if not evidence_tokens:
        return 0.0
    return len(evidence_tokens & tokenize(chunk)) / len(evidence_tokens)


def is_relevant(chunk: str, evidence_items: list[str], threshold: float) -> bool:
    return any(evidence_recall(evidence, chunk) >= threshold for evidence in evidence_items)


def load_dataset(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("The evaluation dataset must be a JSON array.")
    return data


def build_retriever() -> PGRetriever:
    model_config_path = PROJECT_ROOT / os.environ["MODEL_CONFIG"]
    with model_config_path.open("r", encoding="utf-8") as file:
        model_config = json.load(file)

    prompt_dir = PROJECT_ROOT / os.getenv(
        "PROMPT_DIR", "retrieval_service/src/prompts"
    )
    embedding_task = read_text(prompt_dir / "embedding_task.txt")

    embedding = QwenEmbedder(
        model_name=os.environ["MODEL_NAME"],
        model_kwargs=model_config["encode_kwargs"],
        query_kwargs=model_config["query_encode_kwargs"],
        task=embedding_task,
    )

    postgres_auth = {
        "POSTGRES_USER": os.environ["POSTGRES_USER"],
        "POSTGRES_PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "POSTGRES_HOST": os.environ["POSTGRES_HOST"],
        "POSTGRES_PORT": os.environ["POSTGRES_PORT"],
        "POSTGRES_DB": os.environ["POSTGRES_DB"],
        "POSTGRES_TABLE": os.environ["POSTGRES_TABLE"],
    }

    search_kwargs = {"k": int(os.getenv("RETRIEVAL_TOP_K", "10"))}

    return PGRetriever(
        postgres_auth=postgres_auth,
        embedding=embedding,
        search_criterion=os.getenv("RETRIEVAL_SEARCH_CRITERION", "similarity"),
        search_kwargs=search_kwargs,
    )


def evaluate_question(retriever, item: dict, k: int, threshold: float) -> dict:
    question = item["question"]
    evidence_items = item.get("reference_evidence", [])

    results = retriever.retrieve_with_scores(question)
    results = results[:k]

    relevant_ranks = [
        rank
        for rank, (doc, _) in enumerate(results, start=1)
        if is_relevant(doc.page_content, evidence_items, threshold)
    ]

    # Evidence recall: proportion of reference evidence passages represented
    # in at least one retrieved chunk.
    matched_evidence = 0
    for evidence in evidence_items:
        if any(
            evidence_recall(evidence, doc.page_content) >= threshold
            for doc, _ in results
        ):
            matched_evidence += 1

    evidence_recall_at_k = (
        matched_evidence / len(evidence_items) if evidence_items else 0.0
    )
    precision_at_k = len(relevant_ranks) / len(results) if results else 0.0
    reciprocal_rank = 1 / relevant_ranks[0] if relevant_ranks else 0.0

    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "retrieved_count": len(results),
        "evidence_recall_at_k": evidence_recall_at_k,
        "precision_at_k": precision_at_k,
        "reciprocal_rank": reciprocal_rank,
        "results": results,
    }


def main():
    dataset_path = Path(__file__).with_name("evaluation_dataset.json")
    output_path = Path(__file__).with_name("retrieval_evaluation_results.json")

    k = int(os.getenv("RETRIEVAL_TOP_K", "10"))
    threshold = float(os.getenv("EVAL_EVIDENCE_RECALL_THRESHOLD", "0.65"))

    dataset = load_dataset(dataset_path)

    # Only score answerable questions with manually verified evidence.
    ready = [
        item for item in dataset
        if item.get("is_answerable") is True
        and item.get("reference_evidence")
        and item.get("question")
    ]

    pending = len(dataset) - len(ready)
    print(f"Dataset questions: {len(dataset)}")
    print(f"Ready for retrieval evaluation: {len(ready)}")
    print(f"Pending ground truth / unanswerable checks: {pending}")

    if not ready:
        print(
            "\nNo questions are ready yet. For each answerable question, "
            "verify it against the source documents, set is_answerable=true, "
            "and add one or more exact reference_evidence passages."
        )
        return

    retriever = build_retriever()
    evaluations = []

    for index, item in enumerate(ready, start=1):
        print(f"\n[{index}/{len(ready)}] {item['id']}: {item['question']}")
        result = evaluate_question(retriever, item, k, threshold)
        evaluations.append(result)

        print(
            f"Evidence Recall@{k}: {result['evidence_recall_at_k']:.3f} | "
            f"Precision@{k}: {result['precision_at_k']:.3f} | "
            f"RR: {result['reciprocal_rank']:.3f}"
        )

        for rank, (doc, score) in enumerate(result["results"], start=1):
            preview = doc.page_content.replace("\n", " ")[:350]
            print(f"\n  Rank {rank} | score={score}")
            print(f"  {preview}")

    count = len(evaluations)
    summary = {
        "evaluated_questions": count,
        f"mean_evidence_recall@{k}": sum(
            x["evidence_recall_at_k"] for x in evaluations
        ) / count,
        f"mean_precision@{k}": sum(
            x["precision_at_k"] for x in evaluations
        ) / count,
        f"mrr@{k}": sum(
            x["reciprocal_rank"] for x in evaluations
        ) / count,
        "evidence_match_threshold": threshold,
        "note": (
            "Evidence matching uses token overlap against manually supplied "
            "reference passages. Treat these as diagnostic lexical metrics, "
            "not a substitute for human relevance judgments."
        ),
    }

    serializable = {
        "summary": summary,
        "questions": [
            {
                key: value
                for key, value in result.items()
                if key != "results"
            }
            | {
                "retrieved": [
                    {
                        "rank": rank,
                        "score": float(score),
                        "content": doc.page_content,
                    }
                    for rank, (doc, score) in enumerate(
                        result["results"], start=1
                    )
                ]
            }
            for result in evaluations
        ],
    }

    output_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print("\n========== SUMMARY ==========")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
