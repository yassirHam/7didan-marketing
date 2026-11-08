
from dotenv import load_dotenv
import os
import asyncio
import json

from argparse import ArgumentParser

from src.ingestions.ingest import ingest
from src.preprocessing.structured_cleaning import Cleaner
from src.chunkers.markdown_chunker import MarkdownChunker
from src.embedders.qwen_embedder import QwenEmbedder
from src.indexers.pg_indexer import PGIndexer


load_dotenv()

arg_parser = ArgumentParser(
    description="7didan Knowledge Base Ingestion Pipeline"
)

arg_parser.add_argument(
    "-c", "--crawl",
    action="store_true",
    help="Crawl web pages."
)

arg_parser.add_argument(
    "-p", "--parse",
    action="store_true",
    help="Parse PDF documents."
)


async def main():

    args = arg_parser.parse_args()

    # 1. Configure ingestion
    crawl_config = {
        "config_path": os.getenv("CRAWLER_URLS"),
        "output_dir": os.getenv("RAW_DATA_PATH")
    } if args.crawl else None

    if args.parse:
        with open(os.getenv("PARSER_CONFIG"), "r", encoding="utf-8") as file:
            parser_config = json.load(file)

        parser_config.update({
            "source_dir": os.getenv("PDF_DATA_PATH"),
            "output_dir": os.getenv("RAW_DATA_PATH")
        })
    else:
        parser_config = None

    # 2. Run ingestion
    await ingest(
        scrape_web=args.crawl,
        parse_pdf=args.parse,
        crawler_config=crawl_config,
        parser_config=parser_config
    )

    # 3. Clean documents
    cleaner = Cleaner(
        pool_num=int(os.getenv("NUM_WORKER"))
    )

    cleaned_documents = cleaner.clean_documents(
        os.getenv("RAW_DATA_PATH")
    )

    print(f"Cleaned documents: {len(cleaned_documents)}")

    # 4. Chunk documents
    chunker = MarkdownChunker(
        chunk_size=int(os.getenv("CHUNK_SIZE")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP"))
    )

    chunks = chunker.chunk(cleaned_documents)

    print(f"Generated chunks: {len(chunks)}")

    if not chunks:
        print("No chunks generated. Ingestion stopped.")
        return

    # 5. Load embedding configuration
    with open(os.getenv("MODEL_CONFIG"), "r", encoding="utf-8") as file:
        model_config = json.load(file)

    embedding = QwenEmbedder(
        model_name=os.getenv("MODEL_NAME"),
        model_kwargs=model_config["encode_kwargs"],
        query_kwargs=model_config.get("query_encode_kwargs", {}),
        task=""
    )

    # 6. PostgreSQL configuration
    postgres_auth = {
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_TABLE": os.getenv("POSTGRES_TABLE")
    }

    # 7. Initialize indexer
    indexer = PGIndexer(
        postgres_auth=postgres_auth,
        vector_size=int(os.getenv("VECTOR_SIZE")),
        embedding=embedding
    )

    # 8. Store chunks
    stored_ids = indexer.store_chunks(chunks)

    print(f"Successfully indexed {len(stored_ids)} chunks.")
    print("Knowledge base ingestion completed.")


if __name__ == "__main__":
    asyncio.run(main())
