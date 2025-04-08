import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from datetime import datetime
from collections import defaultdict
import logging
from typing import Set, Dict, List, Optional
import tkinter as tk
from tkinter import simpledialog, messagebox
from tqdm import tqdm
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sitemap_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Website Sitemap</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; -webkit-font-smoothing: antialiased; }}
        h1 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .depth {{ margin-left: 20px; margin-bottom: 20px; }}
        .url {{ margin: 5px 0; color: #0066cc; word-break: break-all; }}
        .stats {{ padding: 10px; background: #f5f5f5; border-radius: 5px; margin-bottom: 20px; }}
        .error {{ color: #d9534f; }}
    </style>
</head>
<body>
    <h1>Sitemap for {domain}</h1>
    <div class="stats">
        <p>Generated on: {date}</p>
        <p>Total URLs: {total_urls}</p>
        <p>Max Depth: {max_depth}</p>
    </div>
    {content}
    {error_content}
</body>
</html>"""


class SitemapGenerator:
    def __init__(
            self,
            max_depth: int = 3,
            exclude_extensions: Optional[List[str]] = None,
            max_concurrency: int = 5,
            request_timeout: int = 30000,
            max_retries: int = 2
    ):
        self.max_depth = max_depth
        self.exclude_extensions = exclude_extensions or [".pdf", ".jpg", ".png", ".zip"]
        self.max_concurrency = max_concurrency
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}
        self.domain: str = ""
        self.sitemap: Dict[int, List[str]] = defaultdict(list)
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.progress_bar = None

    async def get_links(self, page, url: str, retry_count: int = 0) -> List[str]:
        try:
            async with self.semaphore:
                await page.goto(url, timeout=self.request_timeout)
                await page.wait_for_load_state("networkidle", timeout=self.request_timeout)

                links = await page.eval_on_selector_all(
                    "a",
                    "elements => elements.map(a => a.href)"
                )

                return [
                    urljoin(url, link)
                    for link in links
                    if link and not link.startswith(("javascript:", "mailto:", "#", "tel:"))
                ]
        except Exception as e:
            if retry_count < self.max_retries:
                logger.warning(f"Retrying ({retry_count + 1}/{self.max_retries}) for {url}")
                return await self.get_links(page, url, retry_count + 1)
            else:
                self.failed_urls[url] = str(e)
                logger.error(f"Failed to fetch {url} after {self.max_retries} retries: {str(e)}")
                return []

    def is_valid_url(self, url: str) -> bool:
        """验证URL是否有效"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            if any(url.lower().endswith(ext) for ext in self.exclude_extensions):
                return False

            if parsed.netloc != self.domain:
                return False

            if not re.match(r'^https?://', url):
                return False

            return True
        except:
            return False

    async def crawl(self, url: str, depth: int = 0) -> None:
        if (depth > self.max_depth or
                url in self.visited_urls or
                not self.is_valid_url(url)):
            return

        self.visited_urls.add(url)
        self.sitemap[depth].append(url)

        if self.progress_bar:
            self.progress_bar.set_description(f"Processing: {url[:50]}...")
            self.progress_bar.update(1)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                timeout=60000
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )

            try:
                page = await context.new_page()
                links = await self.get_links(page, url)

                tasks = [self.crawl(link, depth + 1) for link in links if self.is_valid_url(link)]
                for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"Depth {depth}"):
                    await f
            finally:
                await context.close()
                await browser.close()

    def generate_html(self, output_file: str = "sitemap.html") -> None:
        try:
            content = []
            for depth, urls in sorted(self.sitemap.items()):
                content.append(f"<h2>Depth {depth} ({len(urls)} URLs)</h2>")
                content.append('<div class="depth">')
                content.extend(
                    f'<div class="url"><a href="{url}" target="_blank">{url}</a></div>'
                    for url in sorted(urls)
                )
                content.append("</div>")

            error_content = ""
            if self.failed_urls:
                error_content = "<h2 class='error'>Failed URLs</h2><div class='depth'>"
                error_content += "".join(
                    f'<div class="url error">{url} - {error}</div>'
                    for url, error in self.failed_urls.items()
                )
                error_content += "</div>"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(HTML_TEMPLATE.format(
                    domain=self.domain,
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    total_urls=len(self.visited_urls),
                    max_depth=self.max_depth,
                    content="\n".join(content),
                    error_content=error_content
                ))

            logger.info(f"Sitemap generated successfully: {output_file}")
        except Exception as e:
            logger.error(f"Failed to generate HTML: {str(e)}")
            raise

    async def run(self, start_url: str) -> None:
        parsed_url = urlparse(start_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")

        self.domain = parsed_url.netloc

        logger.info(f"Starting crawl for {start_url} (max depth: {self.max_depth})")

        try:
            with tqdm(total=1, desc="Crawling progress") as self.progress_bar:
                await self.crawl(start_url)

            self.generate_html()
        except Exception as e:
            logger.error(f"Crawling failed: {str(e)}")
            raise


async def main():
    root = tk.Tk()
    root.withdraw()

    class ConfigDialog(simpledialog.Dialog):
        def body(self, master):
            tk.Label(master, text="URL:").grid(row=0)
            tk.Label(master, text="Max Depth:").grid(row=1)

            self.url_entry = tk.Entry(master, width=40)
            self.depth_entry = tk.Entry(master, width=5)

            self.url_entry.grid(row=0, column=1)
            self.depth_entry.grid(row=1, column=1)

            self.url_entry.insert(0, "https://")
            self.depth_entry.insert(0, "3")

            return self.url_entry

        def apply(self):
            self.result = (
                self.url_entry.get(),
                int(self.depth_entry.get())
            )

    try:
        config = ConfigDialog(root, "Sitemap Generator Configuration")
        if not config.result:
            return

        start_url, max_depth = config.result

        generator = SitemapGenerator(
            max_depth=max_depth,
            max_concurrency=1
        )

        await generator.run(start_url)
        messagebox.showinfo("Success", "Sitemap generated successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate sitemap: {str(e)}")
        logger.exception("Sitemap generation failed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
