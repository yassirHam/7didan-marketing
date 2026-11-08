import json
import os
import threading
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda
)
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

PROMPT_DIR = PROJECT_ROOT / os.getenv(
    "PROMPT_DIR",
    "retrieval_service/prompts"
)


def load_prompt(filename: str) -> str:
    return (PROMPT_DIR / filename).read_text(encoding="utf-8")


# Prompt templates are cheap (small text files) and are loaded eagerly.
system_template = PromptTemplate.from_file(
    PROMPT_DIR / "system_prompt.txt",
    encoding="utf-8"
)

user_template = PromptTemplate.from_file(
    PROMPT_DIR / "user_prompt.txt",
    encoding="utf-8"
)

embedding_task = load_prompt("embedding_task.txt")
reranker_instruction = load_prompt("reranker_instruction.txt")


class SuggestedService(BaseModel):

    service_interest: str = Field(
        description="The Orange Maroc Business service identified."
    )

    service_category: Literal[
        "connectivity",
        "mobile",
        "cloud",
        "cybersecurity",
        "collaboration",
        "other"
    ]


class ConversationIntent(BaseModel):

    offer_qualification: bool = Field(
        description=(
            "True if the customer expresses clear commercial intent, "
            "such as requesting a quotation, wanting to subscribe, "
            "or asking to be contacted."
        )
    )

    suggested_service: SuggestedService | None = Field(
        description="The identified service, or null if none is identified."
    )


# ============================================================
# CONVERSATION INTELLIGENCE
# ============================================================

conversation_intelligence_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a conversation intelligence component for Orange Maroc Business.

Analyze the customer's message and extract:

1. Commercial qualification intent.
2. The Orange Maroc Business service of interest.

QUALIFICATION RULES:

Set offer_qualification to true when the customer:
- Wants to subscribe to a service.
- Wants to purchase a solution.
- Requests a quotation or commercial proposal.
- Explicitly asks to be contacted by a sales representative.

Set offer_qualification to false when the customer:
- Only asks informational questions.
- Asks about prices without expressing purchase intent.
- Asks about technical specifications or features.
- Greets the assistant.
- Asks unrelated questions.

SERVICE IDENTIFICATION:

Identify the relevant service using these categories:
- connectivity
- mobile
- cloud
- cybersecurity
- collaboration
- other

Examples:

Message: "What are the available Business Fibre offers?"
Qualification: false
Service: Business Fibre / connectivity

Message: "I want to subscribe to Business Fibre."
Qualification: true
Service: Business Fibre / connectivity

Message: "What cybersecurity solutions do you provide?"
Qualification: false
Service: Cybersecurity / cybersecurity

Message: "Hello, how can you help me?"
Qualification: false
Service: null

IMPORTANT:
- Analyze only the supplied customer message.
- Never invent customer information.
- Do not confuse informational interest with purchase intent.
"""
    ),
    (
        "human",
        "Customer message:\n{message}"
    )
])


# ============================================================
# LAZY COMPONENTS
# ============================================================
# Heavy resources (LLM client, embedding model, PG connection, reranker
# weights) are built on first use instead of at import time, so importing
# this module (e.g. from the FastAPI app) stays fast and /api/health does
# not load hundreds of MB of models.

_lazy_lock = threading.RLock()
_lazy_cache: dict = {}


def _build_llm():
    return init_chat_model(
        os.getenv("LLM_MODEL_NAME"),
        model_provider=os.getenv("LLM_MODEL_PROVIDER"),
        api_key=os.getenv("LLM_API_KEY") or None,
        base_url=os.getenv("BASE_URL") or None,
        temperature=float(os.getenv("LLM_TEMPERATURE"))
    )


def _build_conversation_intelligence_chain():
    return (
        conversation_intelligence_prompt
        | __getattr__("llm").with_structured_output(ConversationIntent)
    )


def _build_embedder():
    # Imported here so the heavy ML stack is only loaded on first use.
    from knowledge_base.src.embedders.qwen_embedder import QwenEmbedder

    with open(os.getenv("MODEL_CONFIG"), "r") as f:
        embedding_config = json.load(f)

    return QwenEmbedder(
        model_name=os.getenv("MODEL_NAME"),
        model_kwargs=embedding_config["encode_kwargs"],
        query_kwargs=embedding_config["query_encode_kwargs"],
        task=embedding_task
    )


def _build_retriever():
    from retrieval_service.src.retrieval.pg_retriever import PGRetriever

    postgres_config = {
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "POSTGRES_PORT": int(os.getenv("POSTGRES_PORT")),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_TABLE": os.getenv("POSTGRES_TABLE")
    }

    return PGRetriever(
        embedding=__getattr__("embedder"),
        postgres_auth=postgres_config,
        search_criterion=os.getenv("RETRIEVAL_SEARCH_CRITERION"),
        search_kwargs={
            "k": int(os.getenv("RETRIEVAL_TOP_K"))
        }
    )


def _build_reranker():
    from retrieval_service.src.reranking.qwen_reranker import QwenReranker

    return QwenReranker(
        model_name=os.getenv("RERANKER_MODEL_NAME"),
        top_k=int(os.getenv("RERANKER_TOP_K")),
        instruction=reranker_instruction,
        device=os.getenv("RERANKER_DEVICE"),
        batch_size=int(os.getenv("RERANKER_BATCH_SIZE"))
    )


def _build_input_guardrail():
    from retrieval_service.src.guardrails.input_guardrail import InputGuardrail

    return InputGuardrail(
        __getattr__("llm"),
        PROMPT_DIR / "input_guardrail.txt"
    )


def _build_answer_evaluator():
    from retrieval_service.src.evaluators.evaluator import LayaAnswerEvaluator

    return LayaAnswerEvaluator(
        threshold=float(os.getenv("LAYA_EVALUATOR_THRESHOLD", "0.5"))
    )


def _build_generation_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template.template),
        ("human", user_template.template)
    ])

    return (
        prompt
        | __getattr__("llm")
        | StrOutputParser()
    )


def _build_rag_chain():
    return (

        RunnableParallel({
            "question": RunnablePassthrough(),
            "documents": RunnableLambda(retrieve_and_rerank)
        })

        | RunnableLambda(
            lambda data: {
                "question": data["question"],
                "documents": data["documents"],
                "context": format_context(data["documents"])
            }
        )

        | RunnablePassthrough.assign(
            answer=__getattr__("generation_chain")
        )

        | RunnableLambda(evaluate_generated_answer)

    )


_LAZY_BUILDERS = {
    "llm": _build_llm,
    "conversation_intelligence_chain": _build_conversation_intelligence_chain,
    "embedder": _build_embedder,
    "retriever": _build_retriever,
    "reranker": _build_reranker,
    "input_guardrail": _build_input_guardrail,
    "answer_evaluator": _build_answer_evaluator,
    "generation_chain": _build_generation_chain,
    "rag_chain": _build_rag_chain,
}


def __getattr__(name: str):
    """Build heavy components lazily on first attribute access (PEP 562)."""
    builder = _LAZY_BUILDERS.get(name)

    if builder is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )

    if name not in _lazy_cache:
        with _lazy_lock:
            if name not in _lazy_cache:
                _lazy_cache[name] = builder()

    return _lazy_cache[name]


def extract_conversation_intelligence(message: str) -> dict:

    try:
        result = __getattr__("conversation_intelligence_chain").invoke({
            "message": message
        })

        return result.model_dump()

    except Exception as e:

        print(f"Conversation intelligence failed: {e}")

        return {
            "offer_qualification": False,
            "suggested_service": None
        }


# ============================================================
# RETRIEVAL AND RERANKING
# ============================================================

def retrieve_and_rerank(question: str):

    documents = __getattr__("retriever").retrieve(question)

    print("Retrieval Done")

    documents = __getattr__("reranker").compress_documents(
        documents=documents,
        query=question
    )

    print("Reranking Done")

    return documents


def format_context(documents):

    return "\n\n".join(
        document.page_content
        for document in documents
    )


# ============================================================
# ANSWER EVALUATION AND RESULT ASSEMBLY
# ============================================================

def evaluate_generated_answer(data: dict):

    question = data["question"]
    context = data["context"]
    documents = data["documents"]
    raw_answer = data["answer"]

    # Extract conversation intelligence once.
    intent = extract_conversation_intelligence(question)

    # Extract generation status.
    if raw_answer.startswith("[ANSWERED]"):

        status = "answered"
        answer = raw_answer.removeprefix("[ANSWERED]").strip()

    elif raw_answer.startswith("[ABSTAINED]"):

        status = "abstained"
        answer = raw_answer.removeprefix("[ABSTAINED]").strip()

    else:

        print("Missing or invalid answer status marker.")

        return {
            "answer": "Je ne peux pas vérifier la fiabilité de ma réponse pour le moment.",
            "status": "abstained",
            "documents": [],
            "evaluation": None,
            **intent
        }

    try:

        evaluation = __getattr__("answer_evaluator").evaluate(
            question=question,
            context=context,
            answer=answer
        )

        print("\nAnswer Evaluation:")
        print(f"Score: {evaluation['score']}")
        print(f"Valid: {evaluation['is_valid']}")

        if not evaluation["is_valid"]:

            return {
                "answer": (
                    "Je ne dispose pas d'informations suffisamment "
                    "fiables pour répondre précisément à votre question."
                ),
                "status": "abstained",
                "documents": [],
                "evaluation": evaluation,
                **intent
            }

        return {
            "answer": answer,
            "status": status,
            "documents": documents if status == "answered" else [],
            "evaluation": evaluation,
            **intent
        }

    except Exception as e:

        print(f"Answer evaluation failed: {e}")

        return {
            "answer": "Je ne peux pas vérifier la fiabilité de ma réponse pour le moment.",
            "status": "abstained",
            "documents": [],
            "evaluation": None,
            **intent
        }


# ============================================================
# GUARDED RAG CHAIN
# ============================================================

def guarded_rag_chain(question: str):

    is_allowed = __getattr__("input_guardrail").validate(question)

    if not is_allowed:

        return {
            "answer": (
                "Je peux uniquement vous aider concernant les produits, "
                "services, solutions et offres commerciales d’Orange Maroc Business."
            ),
            "status": "abstained",
            "documents": [],
            "evaluation": None,
            "offer_qualification": False,
            "suggested_service": None
        }

    return __getattr__("rag_chain").invoke(question)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    question = (
        "I want to subscribe to Business Fibre. "
        "Can you send me a quotation?"
    )

    response = guarded_rag_chain(question)
    intent = extract_conversation_intelligence(question)
    print("\n========== CONVERSATION INTELLIGENCE ==========")
    print("Offer qualification:", intent["offer_qualification"])
    print("Suggested service:", intent["suggested_service"])
    print("================================================\n")

    print("\nFINAL RESULT:")
    print("Status:", response["status"])
    print("Answer:", response["answer"])
    print("Documents:", len(response["documents"]))
    print("Evaluation:", response["evaluation"])
    print("Offer qualification:", response["offer_qualification"])
    print("Suggested service:", response["suggested_service"])
