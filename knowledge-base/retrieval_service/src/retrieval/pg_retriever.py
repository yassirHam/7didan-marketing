
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.embeddings import Embeddings


class PGRetriever:

    def __init__(
        self,
        postgres_auth: dict,
        embedding: Embeddings,
        search_criterion: str,
        search_kwargs: dict
    ):
        self.connection_string = (
            f"postgresql+asyncpg://"
            f"{postgres_auth['POSTGRES_USER']}:"
            f"{postgres_auth['POSTGRES_PASSWORD']}@"
            f"{postgres_auth['POSTGRES_HOST']}:"
            f"{postgres_auth['POSTGRES_PORT']}/"
            f"{postgres_auth['POSTGRES_DB']}"
        )

        self.engine = PGEngine.from_connection_string(
            url=self.connection_string
        )

        self.search_kwargs = search_kwargs.copy()
        table_name = postgres_auth["POSTGRES_TABLE"]

        self.store = PGVectorStore.create_sync(
            engine=self.engine,
            table_name=table_name,
            embedding_service=embedding
        )

        self.retriever = self.store.as_retriever(
            search_type=search_criterion,
            search_kwargs=self.search_kwargs
        )

    def retrieve(self, query: str):
        return self.retriever.invoke(query)

    def retrieve_with_scores(self, query: str):
        return self.store.similarity_search_with_score(
            query,
            k=self.search_kwargs["k"]
        )
