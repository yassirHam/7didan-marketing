import json

from pathlib import Path

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BrowserConfig
)

from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher


def load_pages(config_path: str) -> list[dict]:
    """Load and validate crawler configuration."""

    if not config_path:
        raise ValueError("CRAWLER_URLS is not defined in .env")

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    pages = config.get("pages", [])

    unique_pages = []
    seen_urls = set()
    seen_filenames = set()

    for page in pages:
        url = page.get("url", "").strip()
        filename = page.get("file", "").strip()

        if not url or not filename:
            continue

        if Path(filename).name != filename:
            print(f"[SKIPPED] Invalid filename: {filename}")
            continue

        if Path(filename).suffix.lower() != ".md":
            print(f"[SKIPPED] Invalid Markdown filename: {filename}")
            continue

        if url in seen_urls:
            print(f"[SKIPPED] Duplicate URL: {url}")
            continue

        if filename in seen_filenames:
            print(f"[SKIPPED] Duplicate filename: {filename}")
            continue

        seen_urls.add(url)
        seen_filenames.add(filename)

        unique_pages.append({
            "url": url,
            "file": filename,
            "category": page.get("category", "other"),
            "document_type": page.get("document_type", "unknown"),
            "language": page.get("language", "fr")
        })

    return unique_pages


def get_browser_config():

    return BrowserConfig(
        headless=True,
        verbose=False,
        text_mode=True,
        light_mode=True
    )


def get_crawler_config():

    return CrawlerRunConfig(
        stream=True,
        excluded_tags=["header", "footer"],

        js_code="""
            (async () => {

                const buttons = [
                    ...document.querySelectorAll(
                        'button[aria-controls]'
                    )
                ];

                for (const button of buttons) {

                    if (
                        button.getAttribute('aria-expanded') === 'false'
                    ) {
                        button.click();

                        await new Promise(resolve =>
                            setTimeout(resolve, 300)
                        );
                    }
                }

            })();
        """,

        delay_before_return_html=3
    )


async def crawl_web(output_dir: str, config_path: str):

    pages = load_pages(config_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pages:
        print("No URLs to crawl.")
        return

    url_to_page = {
        page["url"]: page
        for page in pages
    }

    urls = list(url_to_page.keys())

    browser_config = get_browser_config()
    crawl_config = get_crawler_config()

    dispatcher = MemoryAdaptiveDispatcher(
        max_session_permit=1,
        memory_threshold_percent=85.0,
        check_interval=1.0
    )

    successful = 0
    failed = 0

    async with AsyncWebCrawler(config=browser_config) as crawler:

        results = await crawler.arun_many(
            urls,
            config=crawl_config,
            dispatcher=dispatcher
        )

        async for result in results:

            page = url_to_page.get(result.url)

            if not result.success:
                failed += 1
                print(f"[FAILED] {result.url}")
                print(f"Reason: {result.error_message}")
                continue

            if not page:
                failed += 1
                print(f"[WARNING] No configuration for: {result.url}")
                continue

            filename = page["file"]
            markdown = result.markdown

            output_path = output_dir / filename

            metadata = {
                "title": Path(filename).stem.replace("_", " ").title(),
                "source": filename,
                "source_url": page["url"],
                "category": page["category"],
                "document_type": page["document_type"],
                "language": page["language"]
            }

            metadata_path = output_path.with_suffix(".json")

            try:

                output_path.write_text(
                    markdown,
                    encoding="utf-8"
                )

                metadata_path.write_text(
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        indent=4
                    ),
                    encoding="utf-8"
                )

                successful += 1

                print(f"[SAVED] {filename}")
                print(f"[SAVED] {metadata_path.name}")

            except Exception as ex:

                failed += 1
                print(f"[ERROR] Saving {filename}: {ex}")

    print(f"Total URLs: {len(pages)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")