
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from knowledge_base.src.embedders.qwen_embedder import QwenEmbedder
from retrieval_service.src.retrieval.pg_retriever import PGRetriever
from retrieval_service.src.reranking.qwen_reranker import QwenReranker


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

DATASET_PATH = (
    BASE_DIR
    / "src"
    / "evaluations"
    / "evaluation_dataset_with_ground_truth.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "src"
    / "evaluations"
    / "retrieval_inspection_results_top10.json"
)

PROMPT_DIR = PROJECT_ROOT / os.getenv(
    "PROMPT_DIR",
    "retrieval_service/prompts"
)

RETRIEVAL_TOP_K = 15
RERANKER_TOP_K = 10

REQUEST_DELAY = 0.5


# ============================================================
# 2. UTILITY FUNCTIONS
# ============================================================

def resolve_project_path(path: str) -> Path:
    path = Path(path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_json_config(path: str) -> dict:
    config_path = resolve_project_path(path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_prompt(filename: str) -> str:
    prompt_path = PROMPT_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8")


def save_results(results: list) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# 3. INITIALIZE EMBEDDER
# ============================================================

def initialize_embedder():

    model_config = load_json_config(
        os.getenv("MODEL_CONFIG")
    )

    embedding_task = load_prompt(
        "embedding_task.txt"
    )

    return QwenEmbedder(
        model_name=os.getenv("MODEL_NAME"),
        model_kwargs=model_config["encode_kwargs"],
        query_kwargs=model_config["query_encode_kwargs"],
        task=embedding_task
    )


# ============================================================
# 4. INITIALIZE POSTGRES RETRIEVER
# ============================================================

def initialize_retriever(embedder):

    postgres_config = {
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "POSTGRES_PORT": int(os.getenv("POSTGRES_PORT")),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_TABLE": os.getenv("POSTGRES_TABLE")
    }

    return PGRetriever(
        embedding=embedder,
        postgres_auth=postgres_config,
        search_criterion=os.getenv(
            "RETRIEVAL_SEARCH_CRITERION"
        ),
        search_kwargs={
            "k": RETRIEVAL_TOP_K
        }
    )


# ============================================================
# 5. INITIALIZE QWEN RERANKER
# ============================================================

def initialize_reranker():

    reranker_instruction = load_prompt(
        "reranker_instruction.txt"
    )

    return QwenReranker(
        model_name=os.getenv("RERANKER_MODEL_NAME"),
        top_k=RERANKER_TOP_K,
        instruction=reranker_instruction,
        device=os.getenv("RERANKER_DEVICE"),
        batch_size=int(
            os.getenv("RERANKER_BATCH_SIZE")
        )
    )


# ============================================================
# 6. RETRIEVE AND RERANK
# ============================================================

def retrieve_and_rerank(
    question: str,
    retriever,
    reranker
):

    # Retrieve the initial candidates from PostgreSQL.
    documents = retriever.retrieve(question)

    if not documents:
        return []

    # Rerank the retrieved candidates.
    reranked_documents = reranker.compress_documents(
        documents=documents,
        query=question
    )

    return reranked_documents


# ============================================================
# 7. SERIALIZE DOCUMENTS
# ============================================================

def serialize_documents(documents: list) -> list:

    serialized = []

    for rank, document in enumerate(
        documents,
        start=1
    ):

        serialized.append({
            "rank": rank,
            "content": document.page_content,
            "metadata": document.metadata
        })

    return serialized


# ============================================================
# 8. PROCESS ONE QUESTION
# ============================================================

def process_question(
    item: dict,
    retriever,
    reranker
):

    question_id = item["id"]
    question = item["question"]

    print("\n" + "=" * 65)
    print(f"Question: {question_id}")
    print(question)

    documents = retrieve_and_rerank(
        question=question,
        retriever=retriever,
        reranker=reranker
    )

    serialized_documents = serialize_documents(
        documents
    )

    print(
        f"Documents retrieved after reranking: "
        f"{len(serialized_documents)}"
    )

    for document in serialized_documents:

        print(
            f"\n--- RANK {document['rank']} ---"
        )

        print(
            document["content"][:500]
        )

    return {
        "id": question_id,
        "category": item.get("category"),
        "question": question,
        "retrieval_status": (
            "success" if documents else "no_documents"
        ),
        "retrieved_documents": serialized_documents
    }


# ============================================================
# 9. MAIN PIPELINE
# ============================================================

def run_inspection():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        dataset = json.load(file)

    print(f"Dataset questions: {len(dataset)}")

    print("\nInitializing embedding model...")
    embedder = initialize_embedder()

    print("\nInitializing PostgreSQL retriever...")
    retriever = initialize_retriever(embedder)

    print("\nInitializing Qwen reranker...")
    reranker = initialize_reranker()

    results = []

    for index, item in enumerate(
        dataset,
        start=1
    ):

        print(
            f"\nProcessing question {index}/{len(dataset)}"
        )

        try:

            result = process_question(
                item=item,
                retriever=retriever,
                reranker=reranker
            )

        except Exception as error:

            print(
                f"Error processing {item['id']}: {error}"
            )

            result = {
                "id": item["id"],
                "category": item.get("category"),
                "question": item["question"],
                "retrieval_status": "error",
                "error": str(error),
                "retrieved_documents": []
            }

        results.append(result)

        # Save progress after every question.
        save_results(results)

        if index < len(dataset):
            time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 65)
    print("RETRIEVAL INSPECTION COMPLETED")
    print(f"Questions processed: {len(results)}")
    print(f"Results saved to: {OUTPUT_PATH}")


# ============================================================
# 10. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_inspection()
