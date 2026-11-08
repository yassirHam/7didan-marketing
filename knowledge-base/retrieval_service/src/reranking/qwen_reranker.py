
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor



# Reranker base class is BaseDocumentCompressor
class QwenReranker(BaseDocumentCompressor):

    model_name: str
    top_k: int
    instruction: str
    device: str = "cpu"
    batch_size: int = 2

    def __init__(
        self,
        model_name: str,
        top_k: int,
        instruction: str,
        device: str = "cpu",
        batch_size: int = 2,
        **kwargs
    ):
        super().__init__(
            model_name=model_name,
            top_k=top_k,
            instruction=instruction,
            device=device,
            batch_size=batch_size,
            **kwargs
        )

        object.__setattr__(
            self,
            "model",
            CrossEncoder(
                self.model_name,
                device=self.device,
                prompts={"query": self.instruction},
                default_prompt_name="query"
            )
        )

    def compress_documents_with_scores(
        self,
        documents: list[Document],
        query: str
    ) -> list[dict]:

        if not documents:
            return []

        pairs = [
            (query, document.page_content)
            for document in documents
        ]

        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False
        )

        ranked_documents = sorted(
            zip(documents, scores),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            {
                "document": document,
                "score": float(score)
            }
            for document, score in ranked_documents[:self.top_k]
        ]

    def compress_documents(
        self,
        documents: list[Document],
        query: str,
        callbacks=None
    ) -> list[Document]:

        ranked = self.compress_documents_with_scores(
            documents=documents,
            query=query
        )

        print("Reranking Done")

        return [
            item["document"]
            for item in ranked
        ]
