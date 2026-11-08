
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from knowledge_base.src.embedders.qwen_embedder import QwenEmbedder
from retrieval_service.src.retrieval.pg_retriever import PGRetriever
from retrieval_service.src.reranking.qwen_reranker import QwenReranker


# ============================================================
# 1. PATHS AND ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

PROMPT_DIR = PROJECT_ROOT / os.getenv(
    "PROMPT_DIR",
    "retrieval_service/prompts"
)

DATASET_PATH = (
    BASE_DIR / "src/evaluations/evaluation_dataset.json"
)

OUTPUT_PATH = (
    BASE_DIR / "src/evaluations/evaluation_dataset_with_ground_truth.json"
)


# ============================================================
# 2. CONFIGURATION
# ============================================================

TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 10))

REQUEST_DELAY = 2
MAX_RETRIES = 3


# ============================================================
# 3. LOAD CONFIGURATION
# ============================================================

def resolve_project_path(path: str) -> Path:

    if not path:
        raise ValueError("A required file path is missing.")

    path = Path(path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_json_config(path: Path) -> dict:

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_prompt(filename: str) -> str:

    return (PROMPT_DIR / filename).read_text(
        encoding="utf-8"
    )


# ============================================================
# 4. INITIALIZE EMBEDDER
# ============================================================

def initialize_embedder():

    model_config_path = resolve_project_path(
        os.getenv("MODEL_CONFIG")
    )

    embedding_config = load_json_config(
        model_config_path
    )

    embedding_task = load_prompt(
        "embedding_task.txt"
    )

    return QwenEmbedder(
        model_name=os.getenv("MODEL_NAME"),
        model_kwargs=embedding_config["encode_kwargs"],
        query_kwargs=embedding_config["query_encode_kwargs"],
        task=embedding_task
    )


# ============================================================
# 5. INITIALIZE POSTGRESQL RETRIEVER
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
            "k": TOP_K
        }
    )


# ============================================================
# 6. INITIALIZE RERANKER
# ============================================================

def initialize_reranker():

    reranker_instruction = load_prompt(
        "reranker_instruction.txt"
    )

    return QwenReranker(
        model_name=os.getenv("RERANKER_MODEL_NAME"),
        top_k=int(os.getenv("RERANKER_TOP_K")),
        instruction=reranker_instruction,
        device=os.getenv("RERANKER_DEVICE"),
        batch_size=int(os.getenv("RERANKER_BATCH_SIZE"))
    )


# ============================================================
# 7. INITIALIZE LLM
# ============================================================

def initialize_llm():

    return init_chat_model(
        os.getenv("LLM_MODEL_NAME"),
        model_provider=os.getenv("LLM_MODEL_PROVIDER"),
        api_key=os.getenv("LLM_API_KEY") or None,
        base_url=os.getenv("BASE_URL"),
        temperature=float(os.getenv("LLM_TEMPERATURE"))
    )


# ============================================================
# 8. RETRIEVE AND RERANK
# ============================================================

def retrieve_and_rerank(
    question: str,
    retriever: PGRetriever,
    reranker: QwenReranker
):

    documents = retriever.retrieve(question)

    if not documents:
        return []

    return reranker.compress_documents(
        documents=documents,
        query=question
    )


# ============================================================
# 9. FORMAT CONTEXT
# ============================================================

def format_context(documents):

    return "\n\n".join(
        f"[CHUNK {index}]\n{document.page_content}"
        for index, document in enumerate(
            documents,
            start=1
        )
    )


# ============================================================
# 10. BUILD GROUND-TRUTH PROMPT
# ============================================================

def build_prompt(question: str, context: str):

    return f"""
Tu es un évaluateur expert d'un système RAG destiné aux clients
professionnels d'Orange Maroc.

Ta tâche consiste à préparer une annotation préliminaire
pour un jeu de données d'évaluation.

QUESTION :
{question}

CONTEXTE DOCUMENTAIRE :
{context}

INSTRUCTIONS :

1. Utilise exclusivement les informations présentes dans le contexte.
2. N'utilise aucune connaissance externe.
3. Détermine si le contexte contient suffisamment d'informations
   pour répondre précisément à la question.
4. Si la réponse est présente :
   - Rédige une réponse concise en français.
   - Extrais les passages qui justifient directement cette réponse.
   - Recopie chaque passage exactement comme il apparaît.
5. N'invente aucune information ni aucun passage justificatif.
6. Si le contexte est insuffisant, ne devine pas la réponse.
7. L'absence d'une information dans les passages récupérés ne prouve
   PAS son absence dans toute la base de connaissances.
8. Ne classe une question comme "supported" que si les passages
   récupérés permettent réellement de répondre.

Retourne uniquement un JSON valide :

{{
    "assessment": "supported",
    "expected_answer": "Réponse en français",
    "reference_evidence": [
        "Passage exact extrait du contexte"
    ],
    "reason": "Explication concise en français"
}}

assessment doit être l'une de ces valeurs :

- "supported" : le contexte permet de répondre.
- "uncertain" : le contexte ne fournit pas suffisamment de preuves.

Pour une question incertaine :

{{
    "assessment": "uncertain",
    "expected_answer": "",
    "reference_evidence": [],
    "reason": "Explication de l'insuffisance du contexte"
}}

N'utilise pas de blocs Markdown.
"""


# ============================================================
# 11. PARSE LLM RESPONSE
# ============================================================

def parse_llm_response(response):

    content = response.content

    if isinstance(content, list):

        content = "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    content = str(content).strip()

    # Remove Markdown code fences if present.
    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE
    )

    start = content.find("{")

    if start == -1:
        raise ValueError(
            "No JSON object found in LLM response."
        )

    parsed, _ = json.JSONDecoder().raw_decode(
        content[start:]
    )

    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object.")

    if parsed.get("assessment") not in (
        "supported",
        "uncertain"
    ):
        raise ValueError("Invalid assessment value.")

    if not isinstance(
        parsed.get("expected_answer"),
        str
    ):
        raise ValueError("Invalid expected_answer.")

    if not isinstance(
        parsed.get("reference_evidence"),
        list
    ):
        raise ValueError("Invalid reference_evidence.")

    return parsed


# ============================================================
# 12. VALIDATE GENERATED EVIDENCE
# ============================================================

def validate_annotation(annotation, documents):

    if annotation["assessment"] != "supported":
        return False

    expected_answer = annotation["expected_answer"]
    evidence = annotation["reference_evidence"]

    if not expected_answer.strip():
        return False

    if not evidence:
        return False

    retrieved_chunks = [
        document.page_content
        for document in documents
    ]

    for passage in evidence:

        if not isinstance(passage, str):
            return False

        if not passage.strip():
            return False

        if not any(
            passage in chunk
            for chunk in retrieved_chunks
        ):
            return False

    return True


# ============================================================
# 13. LLM RETRY MECHANISM
# ============================================================

def invoke_llm_with_retry(
    llm,
    prompt: str,
    max_retries: int = MAX_RETRIES
):

    for attempt in range(max_retries + 1):

        try:

            return llm.invoke(prompt)

        except Exception as error:

            if attempt == max_retries:
                raise

            delay = 2 ** (attempt + 1)

            print(
                f"LLM request failed: {error}"
            )

            print(
                f"Retrying in {delay} seconds "
                f"({attempt + 1}/{max_retries})..."
            )

            time.sleep(delay)


# ============================================================
# 14. SAVE DATASET
# ============================================================

def save_dataset(dataset):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            dataset,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# 15. PROCESS QUESTIONS
# ============================================================

def generate_ground_truth():

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        dataset = json.load(file)

    print(f"Dataset questions: {len(dataset)}")

    # Initialize all components once.
    embedder = initialize_embedder()
    retriever = initialize_retriever(embedder)
    reranker = initialize_reranker()
    llm = initialize_llm()

    for index, item in enumerate(
        dataset,
        start=1
    ):

        question_id = item["id"]
        question = item["question"]

        print(f"\n[{index}/{len(dataset)}] {question_id}")
        print(f"Question: {question}")

        # Skip manually verified records.
        if item.get("status") == "verified":

            print("Already verified. Skipping.")
            continue

        try:

            # Retrieve and rerank.
            documents = retrieve_and_rerank(
                question,
                retriever,
                reranker
            )

            print(
                f"Reranked documents: {len(documents)}"
            )

            if not documents:

                annotation = {
                    "assessment": "uncertain",
                    "expected_answer": "",
                    "reference_evidence": [],
                    "reason": (
                        "Aucun document n'a été récupéré."
                    )
                }

            else:

                context = format_context(documents)

                prompt = build_prompt(
                    question,
                    context
                )

                response = invoke_llm_with_retry(
                    llm,
                    prompt
                )

                annotation = parse_llm_response(
                    response
                )

            assessment = annotation["assessment"]

            if (
                assessment == "supported"
                and validate_annotation(
                    annotation,
                    documents
                )
            ):

                # Do not overwrite manually verified
                # unanswerable classifications.
                if item.get("is_answerable") is not False:

                    item["is_answerable"] = True

                    item["expected_answer"] = annotation[
                        "expected_answer"
                    ]

                    item["reference_evidence"] = annotation[
                        "reference_evidence"
                    ]

                print("Assessment: Supported")

            else:

                # Preserve existing answers and evidence.
                # Insufficient retrieval is not proof
                # that the question is unanswerable.

                print(
                    "Assessment: Uncertain / needs review"
                )

            item["generation_assessment"] = assessment

            item["generation_reason"] = annotation.get(
                "reason",
                ""
            )

            item["status"] = "needs_review"

        except Exception as error:

            print(
                f"Error processing {question_id}: {error}"
            )

            item["generation_assessment"] = "error"

            item["generation_reason"] = str(error)

            item["status"] = "needs_review"

        finally:

            # Save after every question.
            save_dataset(dataset)

        # Delay between questions.
        if index < len(dataset):
            time.sleep(REQUEST_DELAY)

    print("\n========================================")
    print("Ground-truth generation completed.")
    print(f"Output file: {OUTPUT_PATH}")
    print("========================================")


# ============================================================
# 16. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    generate_ground_truth()
