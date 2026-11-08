
import re
import html
import json
import unicodedata
from pathlib import Path
from multiprocessing import Pool


class Cleaner:

    def __init__(self, pool_num: int = 1):
        self.pool_num = pool_num

    def clean_document(self, file: Path) -> str:

        text = file.read_text(encoding="utf-8")

        # 1. Decode HTML entities.
        text = html.unescape(text)

        # 2. Normalize Unicode.
        text = unicodedata.normalize("NFC", text)

        # 3. Normalize line endings.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Remove empty Markdown links.
        text = re.sub(r"\[\s*\]\([^)]*\)", "", text)

        # 5. Remove Accueil breadcrumbs.
        text = re.sub(
            r"(?mi)^\s*[*+-]?\s*\[Accueil\]\([^)]*\)\s*$",
            "",
            text
        )

        # 6. Remove empty Markdown headings.
        text = re.sub(
            r"(?m)^\s*#{1,6}\s*$",
            "",
            text
        )

        # 7. Remove Markdown images and their URLs.
        text = re.sub(
            r"!\[[^\]]*\]\([^)]*\)",
            "",
            text
        )

        # 8. Remove standalone image remnants.
        text = re.sub(r"(?m)^\s*!\s*$", "", text)

        # 9. Remove trailing whitespace.
        text = "\n".join(line.rstrip() for line in text.splitlines())

        # 10. Remove excessive blank lines.
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()


    def load_sidecar_metadata(self, file: Path) -> dict:
        """Load the sidecar .json written by the crawler for this .md file.

        Returns url/title/category/... or an empty dict when the file has no
        sidecar (for example PDF-parsed documents).
        """
        sidecar = file.with_suffix(".json")

        if not sidecar.exists():
            return {}

        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

        return {
            "url": data.get("source_url"),
            "title": data.get("title"),
            "category": data.get("category"),
            "document_type": data.get("document_type"),
            "language": data.get("language"),
        }


    def clean_documents(self, source_dir: str) -> list[dict]:
        source_path = Path(source_dir)
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"{source_dir} is not a folder")

        file_list = sorted(
            file for file in source_path.glob("*.md")
            if file.is_file()
            )

        with Pool(self.pool_num) as pool:
            cleaned_documents = pool.map(
                self.clean_document,
                file_list
            )

        return [
            {
                "filename": file.name,
                "content": content,
                # Sidecar metadata (source_url, title, ...) so the page URL
                # is not lost between ingestion and indexing.
                **self.load_sidecar_metadata(file),
            }

            for file, content in zip(file_list, cleaned_documents)

            ]
