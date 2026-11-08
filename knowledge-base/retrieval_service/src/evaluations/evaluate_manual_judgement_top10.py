
import json
import math
from pathlib import Path


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "retrieval_inspection_results_top10.json"
JUDGMENTS_FILE = BASE_DIR / "retrieval_judgments_top10.json"
METRICS_FILE = BASE_DIR / "retrieval_metrics_top10.json"

K = 10

UNANSWERABLE_IDS = {"Q018", "Q019", "Q020"}

RELEVANCE_SCORES = {
    "relevant": 2,
    "partially_relevant": 1,
    "irrelevant": 0
}


# ============================================================
# 2. METRIC FUNCTIONS
# ============================================================

def precision_at_k(labels, k=K):
    """Only fully relevant documents count."""

    top_k = labels[:k]

    if not top_k:
        return 0.0

    return sum(
        label == "relevant" for label in top_k
    ) / len(top_k)


def partial_precision_at_k(labels, k=K):
    """Relevant and partially relevant documents count."""

    top_k = labels[:k]

    if not top_k:
        return 0.0

    return sum(
        label in {"relevant", "partially_relevant"}
        for label in top_k
    ) / len(top_k)


def mrr_at_k(labels, k=K):
    """Reciprocal rank of the first fully relevant document."""

    for rank, label in enumerate(labels[:k], start=1):
        if label == "relevant":
            return 1.0 / rank

    return 0.0


def dcg_at_k(labels, k=K):

    dcg = 0.0

    for rank, label in enumerate(labels[:k], start=1):

        gain = RELEVANCE_SCORES[label]
        dcg += gain / math.log2(rank + 1)

    return dcg


def ndcg_at_k(labels, k=K):

    actual_dcg = dcg_at_k(labels, k)

    ideal_labels = sorted(
        labels[:k],
        key=lambda label: RELEVANCE_SCORES[label],
        reverse=True
    )

    ideal_dcg = dcg_at_k(ideal_labels, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


# ============================================================
# 3. LOAD INSPECTION RESULTS
# ============================================================

def load_results():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Inspection results not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# 4. EXTRACT EXISTING JUDGMENTS
# ============================================================

def extract_judgments(results):

    judgments_output = []

    for item in results:

        question_id = item["id"]
        documents = item.get("retrieved_documents", [])

        if len(documents) < K:
            raise ValueError(
                f"{question_id}: expected at least {K} documents, "
                f"but found {len(documents)}."
            )

        annotated_documents = []

        for document in documents[:K]:

            if "label" not in document:
                raise ValueError(
                    f"{question_id}, rank {document.get('rank')}: "
                    "missing 'relevance' label in inspection JSON."
                )

            label = document["label"]

            if label not in RELEVANCE_SCORES:
                raise ValueError(
                    f"Invalid relevance label '{label}' "
                    f"for question {question_id}."
                )

            annotated_document = document.copy()

            annotated_document["relevance_score"] = (
                RELEVANCE_SCORES[label]
            )

            annotated_documents.append(annotated_document)

        judgments_output.append({
            "id": question_id,
            "category": item.get("category"),
            "question": item.get("question"),
            "is_unanswerable_test": (
                question_id in UNANSWERABLE_IDS
            ),
            "retrieved_documents": annotated_documents
        })

    with open(JUDGMENTS_FILE, "w", encoding="utf-8") as file:

        json.dump(
            judgments_output,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"Judgments saved to: {JUDGMENTS_FILE}")

    return judgments_output


# ============================================================
# 5. CALCULATE METRICS
# ============================================================

def calculate_metrics(judgments):

    answerable_results = []
    unanswerable_diagnostics = []

    for item in judgments:

        question_id = item["id"]

        labels = [
            document["label"]
            for document in item["retrieved_documents"]
        ]

        metrics = {
            "id": question_id,

            "precision_at_10": round(
                precision_at_k(labels), 4
            ),

            "partial_precision_at_10": round(
                partial_precision_at_k(labels), 4
            ),

            "mrr_at_10": round(
                mrr_at_k(labels), 4
            ),

            "ndcg_at_10": round(
                ndcg_at_k(labels), 4
            )
        }

        if question_id not in UNANSWERABLE_IDS:
            answerable_results.append(metrics)

        else:
            unanswerable_diagnostics.append({
                "id": question_id,

                "retrieved_fully_relevant_documents": (
                    labels.count("relevant")
                ),

                "retrieved_partially_relevant_documents": (
                    labels.count("partially_relevant")
                ),

                "retrieved_irrelevant_documents": (
                    labels.count("irrelevant")
                ),

                "no_fully_relevant_document_retrieved": (
                    "relevant" not in labels
                )
            })

    # --------------------------------------------------------
    # Aggregate answerable-question metrics
    # --------------------------------------------------------

    def average_metric(results, metric_name):

        if not results:
            return 0.0

        return round(
            sum(item[metric_name] for item in results)
            / len(results),
            4
        )

    overall_metrics = {
        "number_of_answerable_questions": len(answerable_results),

        "precision_at_10": average_metric(
            answerable_results,
            "precision_at_10"
        ),

        "partial_precision_at_10": average_metric(
            answerable_results,
            "partial_precision_at_10"
        ),

        "mrr_at_10": average_metric(
            answerable_results,
            "mrr_at_10"
        ),

        "ndcg_at_10": average_metric(
            answerable_results,
            "ndcg_at_10"
        )
    }

    # --------------------------------------------------------
    # Unanswerable-question diagnostic
    # --------------------------------------------------------

    no_fully_relevant_count = sum(
        item["no_fully_relevant_document_retrieved"]
        for item in unanswerable_diagnostics
    )

    unanswerable_count = len(unanswerable_diagnostics)

    abstention_diagnostic = {
        "number_of_unanswerable_questions": unanswerable_count,

        "questions_without_fully_relevant_retrieved_documents": (
            no_fully_relevant_count
        ),

        "diagnostic_rate": round(
            no_fully_relevant_count / unanswerable_count,
            4
        ) if unanswerable_count else 0.0,

        "per_question": unanswerable_diagnostics
    }

    return {
        "evaluation_k": K,
        "overall_retrieval_metrics": overall_metrics,

        "per_question_metrics": (
            answerable_results
            + [
                {
                    "id": item["id"],
                    "precision_at_10": round(
                        precision_at_k([
                            doc["label"]
                            for doc in next(
                                j for j in judgments
                                if j["id"] == item["id"]
                            )["retrieved_documents"]
                        ]), 4
                    ),
                    "partial_precision_at_10": round(
                        partial_precision_at_k([
                            doc["label"]
                            for doc in next(
                                j for j in judgments
                                if j["id"] == item["id"]
                            )["retrieved_documents"]
                        ]), 4
                    ),
                    "mrr_at_10": round(
                        mrr_at_k([
                            doc["label"]
                            for doc in next(
                                j for j in judgments
                                if j["id"] == item["id"]
                            )["retrieved_documents"]
                        ]), 4
                    ),
                    "ndcg_at_10": round(
                        ndcg_at_k([
                            doc["label"]
                            for doc in next(
                                j for j in judgments
                                if j["id"] == item["id"]
                            )["retrieved_documents"]
                        ]), 4
                    )
                }
                for item in unanswerable_diagnostics
            ]
        ),

        "unanswerable_question_diagnostics": abstention_diagnostic
    }


# ============================================================
# 6. DISPLAY RESULTS
# ============================================================

def display_metrics(metrics):

    overall = metrics["overall_retrieval_metrics"]

    print("\n" + "=" * 55)
    print("          TOP-10 RETRIEVAL EVALUATION")
    print("=" * 55)

    print(
        f"\nAnswerable questions: "
        f"{overall['number_of_answerable_questions']}"
    )

    print("\nOverall metrics:")

    print(
        f"Precision@10:         "
        f"{overall['precision_at_10']:.4f}"
    )

    print(
        f"Partial Precision@10: "
        f"{overall['partial_precision_at_10']:.4f}"
    )

    print(
        f"MRR@10:               "
        f"{overall['mrr_at_10']:.4f}"
    )

    print(
        f"nDCG@10:              "
        f"{overall['ndcg_at_10']:.4f}"
    )

    print("\nPer-question metrics:")

    print(
        f"{'ID':<8} {'P@10':<10} "
        f"{'MRR@10':<10} {'nDCG@10':<10}"
    )

    print("-" * 45)

    for item in metrics["per_question_metrics"]:

        print(
            f"{item['id']:<8} "
            f"{item['precision_at_10']:<10.4f} "
            f"{item['mrr_at_10']:<10.4f} "
            f"{item['ndcg_at_10']:<10.4f}"
        )

    abstention = metrics["unanswerable_question_diagnostics"]

    print("\nUnanswerable-question diagnostics:")

    print(
        f"Questions: "
        f"{abstention['number_of_unanswerable_questions']}"
    )

    print(
        f"Without fully relevant documents: "
        f"{abstention['questions_without_fully_relevant_retrieved_documents']}"
    )

    print(
        f"Diagnostic rate: "
        f"{abstention['diagnostic_rate']:.4f}"
    )

    print("\n" + "=" * 55)


# ============================================================
# 7. MAIN
# ============================================================

def main():

    print("Loading Top-10 inspection results...")

    results = load_results()

    print(f"Loaded {len(results)} questions.")

    print("\nExtracting existing relevance judgments...")

    judgments = extract_judgments(results)

    print("\nCalculating Top-10 metrics...")

    metrics = calculate_metrics(judgments)

    with open(METRICS_FILE, "w", encoding="utf-8") as file:

        json.dump(
            metrics,
            file,
            ensure_ascii=False,
            indent=4
        )

    display_metrics(metrics)

    print(f"\nMetrics saved to: {METRICS_FILE}")


if __name__ == "__main__":
    main()
