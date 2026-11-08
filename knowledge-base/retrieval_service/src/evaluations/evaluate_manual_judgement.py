import json
import math
from pathlib import Path
from collections import defaultdict


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "retrieval_inspection_results_top10.json"
JUDGMENTS_FILE = BASE_DIR / "retrieval_judgments_top10.json"
METRICS_FILE = BASE_DIR / "retrieval_metrics_top10.json"

K = 15


# ============================================================
# 2. VALIDATED MANUAL JUDGMENTS
#
# Each list corresponds to ranks 1, 2, 3, 4, 5.
# These are the labels you approved.
# ============================================================

JUDGMENTS = {

    "Q001": [
        "relevant",
        "partially_relevant",
        "relevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q002": [
        "relevant",
        "relevant",
        "relevant",
        "relevant",
        "partially_relevant"
    ],

    "Q003": [
        "relevant",
        "relevant",
        "relevant",
        "partially_relevant",
        "partially_relevant"
    ],

    "Q004": [
        "relevant",
        "partially_relevant",
        "relevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q005": [
        "relevant",
        "relevant",
        "relevant",
        "irrelevant",
        "partially_relevant"
    ],

    "Q006": [
        "irrelevant",
        "partially_relevant",
        "partially_relevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q007": [
        "relevant",
        "relevant",
        "relevant",
        "relevant",
        "relevant"
    ],

    "Q008": [
        "relevant",
        "partially_relevant",
        "relevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q009": [
        "relevant",
        "irrelevant",
        "irrelevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q010": [
        "partially_relevant",
        "irrelevant",
        "irrelevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q011": [
        "relevant",
        "partially_relevant",
        "irrelevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q012": [
        "irrelevant",
        "relevant",
        "irrelevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q013": [
        "irrelevant",
        "partially_relevant",
        "partially_relevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q014": [
        "irrelevant",
        "irrelevant",
        "irrelevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q015": [
        "relevant",
        "relevant",
        "partially_relevant",
        "relevant",
        "irrelevant"
    ],

    "Q016": [
        "irrelevant",
        "partially_relevant",
        "relevant",
        "irrelevant",
        "partially_relevant"
    ],

    "Q017": [
        "irrelevant",
        "irrelevant",
        "irrelevant",
        "partially_relevant",
        "irrelevant"
    ],

    "Q018": [
        "irrelevant",
        "partially_relevant",
        "partially_relevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q019": [
        "partially_relevant",
        "irrelevant",
        "irrelevant",
        "irrelevant",
        "irrelevant"
    ],

    "Q020": [
        "irrelevant",
        "irrelevant",
        "partially_relevant",
        "irrelevant",
        "irrelevant"
    ]
}


# Questions designed to test abstention
UNANSWERABLE_IDS = {"Q018", "Q019", "Q020"}


# ============================================================
# 3. RELEVANCE SCORES
# ============================================================

RELEVANCE_SCORES = {
    "relevant": 2,
    "partially_relevant": 1,
    "irrelevant": 0
}


# ============================================================
# 4. METRIC FUNCTIONS
# ============================================================

def precision_at_k(labels, k=5):
    """
    Strict Precision@K:
    Only fully relevant documents count.
    """

    top_k = labels[:k]

    if not top_k:
        return 0.0

    relevant_count = sum(
        1 for label in top_k
        if label == "relevant"
    )

    return relevant_count / len(top_k)


def mrr_at_k(labels, k=5):
    """
    Mean Reciprocal Rank contribution for one query.

    Only fully relevant documents count.
    """

    for rank, label in enumerate(labels[:k], start=1):

        if label == "relevant":
            return 1.0 / rank

    return 0.0


def dcg_at_k(labels, k=5):
    """
    Discounted Cumulative Gain using graded relevance.

    Gain:
        relevant = 2
        partially_relevant = 1
        irrelevant = 0
    """

    dcg = 0.0

    for rank, label in enumerate(labels[:k], start=1):

        gain = RELEVANCE_SCORES[label]

        dcg += gain / math.log2(rank + 1)

    return dcg


def ndcg_at_k(labels, k=5):
    """
    Normalized Discounted Cumulative Gain.
    """

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


def partial_precision_at_k(labels, k=5):
    """
    Optional diagnostic:
    Counts both relevant and partially relevant documents.
    """

    top_k = labels[:k]

    if not top_k:
        return 0.0

    useful_count = sum(
        1 for label in top_k
        if label in {"relevant", "partially_relevant"}
    )

    return useful_count / len(top_k)


# ============================================================
# 5. LOAD RETRIEVAL RESULTS
# ============================================================

def load_results():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Retrieval results not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        results = json.load(file)

    return results


# ============================================================
# 6. VALIDATE AND SAVE JUDGMENTS
# ============================================================

def create_judgments(results):

    judgments_output = []

    result_ids = {
        item["id"] for item in results
    }

    missing_ids = set(JUDGMENTS) - result_ids
    extra_ids = result_ids - set(JUDGMENTS)

    if missing_ids:
        raise ValueError(
            f"Missing questions in retrieval results: {missing_ids}"
        )

    if extra_ids:
        print(f"Warning: unexpected question IDs: {extra_ids}")

    for item in results:

        question_id = item["id"]

        if question_id not in JUDGMENTS:
            continue

        documents = item.get("retrieved_documents", [])
        labels = JUDGMENTS[question_id]

        if len(documents) != len(labels):
            raise ValueError(
                f"{question_id}: expected {len(labels)} documents "
                f"but found {len(documents)}."
            )

        annotated_documents = []

        for document, label in zip(documents, labels):

            annotated_document = document.copy()

            annotated_document["relevance"] = label
            annotated_document["relevance_score"] = (
                RELEVANCE_SCORES[label]
            )

            annotated_documents.append(annotated_document)

        judgments_output.append({
            "id": question_id,
            "category": item.get("category"),
            "question": item.get("question"),
            "is_unanswerable_test": question_id in UNANSWERABLE_IDS,
            "retrieved_documents": annotated_documents
        })

    with open(JUDGMENTS_FILE, "w", encoding="utf-8") as file:

        json.dump(
            judgments_output,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"\nJudgments saved to: {JUDGMENTS_FILE}")

    return judgments_output


# ============================================================
# 7. CALCULATE METRICS
# ============================================================

def calculate_metrics(judgments):

    answerable_results = []
    unanswerable_results = []

    for item in judgments:

        question_id = item["id"]

        labels = [
            document["relevance"]
            for document in item["retrieved_documents"]
        ]

        metrics = {
            "id": question_id,
            "precision_at_5": round(
                precision_at_k(labels, K), 4
            ),
            "partial_precision_at_5": round(
                partial_precision_at_k(labels, K), 4
            ),
            "mrr_at_5": round(
                mrr_at_k(labels, K), 4
            ),
            "ndcg_at_5": round(
                ndcg_at_k(labels, K), 4
            )
        }

        if question_id in UNANSWERABLE_IDS:
            unanswerable_results.append(metrics)
        else:
            answerable_results.append(metrics)

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

        "precision_at_5": average_metric(
            answerable_results, "precision_at_5"
        ),

        "partial_precision_at_5": average_metric(
            answerable_results, "partial_precision_at_5"
        ),

        "mrr_at_5": average_metric(
            answerable_results, "mrr_at_5"
        ),

        "ndcg_at_5": average_metric(
            answerable_results, "ndcg_at_5"
        )
    }

    # --------------------------------------------------------
    # Unanswerable-question diagnostic
    # --------------------------------------------------------

    unanswerable_diagnostics = []

    for item in unanswerable_results:

        question_id = item["id"]

        original = next(
            q for q in judgments if q["id"] == question_id
        )

        labels = [
            doc["relevance"]
            for doc in original["retrieved_documents"]
        ]

        unanswerable_diagnostics.append({
            "id": question_id,
            "retrieved_fully_relevant_documents": labels.count(
                "relevant"
            ),
            "retrieved_partially_relevant_documents": labels.count(
                "partially_relevant"
            ),
            "retrieved_irrelevant_documents": labels.count(
                "irrelevant"
            ),
            "no_fully_relevant_document_retrieved": (
                "relevant" not in labels
            )
        })

    no_fully_relevant_count = sum(
        1 for item in unanswerable_diagnostics
        if item["no_fully_relevant_document_retrieved"]
    )

    abstention_diagnostic = {
        "number_of_unanswerable_questions": len(
            unanswerable_results
        ),
        "questions_without_fully_relevant_retrieved_documents": (
            no_fully_relevant_count
        ),
        "diagnostic_rate": round(
            no_fully_relevant_count / len(unanswerable_results), 4
        ) if unanswerable_results else 0.0,
        "per_question": unanswerable_diagnostics
    }

    return {
        "overall_retrieval_metrics": overall_metrics,
        "per_question_metrics": (
            answerable_results + unanswerable_results
        ),
        "unanswerable_question_diagnostics": abstention_diagnostic
    }


# ============================================================
# 8. DISPLAY RESULTS
# ============================================================

def display_metrics(metrics):

    overall = metrics["overall_retrieval_metrics"]

    print("\n" + "=" * 55)
    print("          RETRIEVAL EVALUATION RESULTS")
    print("=" * 55)

    print(
        f"\nAnswerable questions: "
        f"{overall['number_of_answerable_questions']}"
    )

    print("\nOverall metrics:")

    print(
        f"Precision@5:         {overall['precision_at_5']:.4f}"
    )

    print(
        f"Partial Precision@5: {overall['partial_precision_at_5']:.4f}"
    )

    print(
        f"MRR@5:               {overall['mrr_at_5']:.4f}"
    )

    print(
        f"nDCG@5:              {overall['ndcg_at_5']:.4f}"
    )

    print("\nPer-question metrics:")

    print(
        f"{'ID':<8} {'P@5':<10} {'MRR@5':<10} {'nDCG@5':<10}"
    )

    print("-" * 42)

    for item in metrics["per_question_metrics"]:

        print(
            f"{item['id']:<8} "
            f"{item['precision_at_5']:<10.4f} "
            f"{item['mrr_at_5']:<10.4f} "
            f"{item['ndcg_at_5']:<10.4f}"
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
# 9. MAIN
# ============================================================

def main():

    print("Loading retrieval results...")

    results = load_results()

    print(f"Loaded {len(results)} questions.")

    print("\nCreating validated relevance judgments...")

    judgments = create_judgments(results)

    print("\nCalculating retrieval metrics...")

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