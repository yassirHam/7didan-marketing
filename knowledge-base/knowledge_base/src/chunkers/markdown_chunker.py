
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


# Metadata fields copied from the source document into every chunk.
DOCUMENT_METADATA_FIELDS = (
    "url",
    "title",
    "category",
    "document_type",
    "language",
)


class MarkdownChunker:

    def __init__(self, chunk_size: int, chunk_overlap: int):

        self.size_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk(self, documents: list[dict]) -> list[dict]:

        chunk_list = []

        for document in documents:

            filename = document["filename"]
            text = document["content"]

            # Carry the document-level metadata (url, title, ...) into chunks.
            doc_metadata = {
                field: document.get(field)
                for field in DOCUMENT_METADATA_FIELDS
            }

            # Track the Markdown heading hierarchy.
            headings = []
            sections = []
            current_section = None

            for line in text.splitlines():

                line = line.strip()

                if not line:
                    if current_section is not None:
                        current_section["content"].append("")
                    continue

                # Detect Markdown headings (H1 to H6).
                match = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)

                if match:

                    level = len(match.group(1))
                    heading_text = match.group(2).strip()

                    # Keep only the parent headings.
                    headings = headings[:level - 1]

                    # Add the current heading.
                    headings.append(heading_text)

                    # Start a new section.
                    current_section = {
                        "headings": headings.copy(),
                        "content": []
                    }

                    sections.append(current_section)
                    continue

                # Preserve content appearing before the first heading.
                if current_section is None:

                    current_section = {
                        "headings": [],
                        "content": []
                    }

                    sections.append(current_section)

                current_section["content"].append(line)

            # Split each section into chunks.
            for section in sections:

                content = "\n".join(section["content"]).strip()

                if not content:
                    continue

                heading_path = section["headings"]

                # Build the heading context.
                context = "\n".join(
                    f"{'#' * (i + 1)} {heading}"
                    for i, heading in enumerate(heading_path)
                )

                chunks = self.size_splitter.split_text(content)

                for chunk in chunks:

                    contextual_chunk = (
                        f"{context}\n\n{chunk}"
                        if context
                        else chunk
                    )

                    chunk_list.append({
                        "filename": filename,
                        "content": contextual_chunk.strip(),
                        "headings": heading_path,
                        "section": " > ".join(heading_path),
                        "section_h1": heading_path[0] if len(heading_path) > 0 else None,
                        "section_h2": heading_path[1] if len(heading_path) > 1 else None,
                        "section_h3": heading_path[2] if len(heading_path) > 2 else None,
                        **doc_metadata,
                    })

        return chunk_list
