
from langchain_postgres import PGEngine, PGVectorStore
from langchain_core.embeddings import Embeddings


class PGIndexer:

    def __init__(
        self,
        postgres_auth: dict,
        vector_size: int,
        embedding: Embeddings
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

        table_name = postgres_auth["POSTGRES_TABLE"]

        # Create the vector table if it does not exist.
        self.engine.init_vectorstore_table(
            table_name=table_name,
            vector_size=vector_size,
            overwrite_existing=False
        )

        # Initialize the vector store.
        self.store = PGVectorStore.create_sync(
            engine=self.engine,
            table_name=table_name,
            embedding_service=embedding
        )

    def store_chunks(self, chunks: list[dict]) -> list[str]:

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        metadatas = [
            {
                "source": chunk["filename"],
                "url": chunk.get("url"),
                "title": chunk.get("title"),
                "category": chunk.get("category"),
                "document_type": chunk.get("document_type"),
                "language": chunk.get("language"),
                "section_h1": chunk["section_h1"],
                "section_h2": chunk["section_h2"],
                "section_h3": chunk["section_h3"]
            }
            for chunk in chunks
        ]

        return self.store.add_texts(
            texts=texts,
            metadatas=metadatas
        )
