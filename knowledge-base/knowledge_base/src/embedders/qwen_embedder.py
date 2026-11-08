from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings


class QwenEmbedder(Embeddings):

    def __init__(
        self,
        model_name: str,
        model_kwargs: dict,
        query_kwargs: dict,
        task: str
    ) -> None:

        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs=model_kwargs,
            query_encode_kwargs=query_kwargs
        )

        self.task: str = task

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)

    def embed_query(self, query: str) -> list[float]:
        prompt = f"Instruct: {self.task}\nQuery: {query}"
        return self.model.embed_query(prompt)