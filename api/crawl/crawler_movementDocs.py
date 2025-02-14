import os
import re
import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse

BASE_URL = "https://docs.movementnetwork.xyz/devs/getstarted"
DOMAIN = "docs.movementnetwork.xyz"
OUTPUT_FILE_ALL = "movement_docs_build.txt"
OUTPUT_FOLDER = "data/movement_docs_build"

visited = set()


def ensure_output_folder_exists():
    """Create the data/movement_learning_path folder if it doesn't exist."""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)


def is_valid_url(url):
    """
    Check if the URL:
      - is on the same domain (docs.movementnetwork.xyz)
      - starts with /devs/getstarted
      - does not contain a fragment (#)
    """
    parsed = urlparse(url)

    # Must be on the same domain
    if parsed.netloc.lower() != DOMAIN.lower():
        return False

    # Must start with /devs/getstarted
    if not parsed.path.startswith("/devs/getstarted"):
        return False

    # Skip links that contain a fragment (#)
    if parsed.fragment:
        return False

    return True


def compress_newlines(text):
    """
    Replace consecutive newlines with a single newline, and strip leading/trailing.
    """
    return re.sub(r"\n+", "\n", text).strip()


def get_main_container(soup):
    """
    Find the 'main' container if it exists, otherwise fallback to <body>.
    Adjust if the docs site has a different structure.
    """
    main_tag = soup.find("main")
    if main_tag:
        return main_tag
    body_tag = soup.find("body")
    return body_tag if body_tag else soup  # fallback


def parse_content_with_indentation(main_container):
    """
    1. Find the first <h1> (the page title).
    2. Collect everything from (and including) that <h1> to the next <footer> (or end of main).
    3. For each heading <hN>, indent level = N-1 (h2 => 1 tab, h3 => 2 tabs, etc.).
    4. If 'code' is in element.name (e.g., <code>, <codeblock>), wrap text in <code>...</code>.
    5. Compress consecutive newlines.
    """
    # Locate the first <h1> in the container
    h1 = main_container.find("h1")
    if not h1:
        return ""  # No main title, return empty

    lines = []
    current_indent = 0
    start_collecting = False

    # We'll stop if we encounter <footer>
    for element in main_container.descendants:
        # Stop at <footer>
        if element.name == "footer":
            break

        # We begin collecting at <h1>
        if element == h1:
            start_collecting = True

        if not start_collecting:
            continue

        # If it's a Tag (like <h2>, <p>, <code>*, etc.)
        if element.name:
            # HEADINGS
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                # Parse the heading level (1..6)
                level = int(element.name[1])
                current_indent = max(0, level - 1)  # h1 => 0 tabs, h2 => 1 tab, etc.
                heading_text = element.get_text(separator=" ", strip=True)
                heading_text = compress_newlines(heading_text)
                if heading_text:
                    lines.append("\t" * current_indent + heading_text)

            # CODE BLOCK (change from element.name in ["pre", "code"] to "code" in element.name)
            elif "code" in element.name.lower():
                code_text = element.get_text(separator="\n").strip()
                code_text = compress_newlines(code_text)
                if code_text:
                    lines.append("\t" * current_indent + f"<code>{code_text}</code>")

            # Other tags (paragraphs, divs, lists, etc.)
            else:
                text = element.get_text(separator="\n", strip=True)
                text = compress_newlines(text)
                if text:
                    lines.append("\t" * current_indent + text)

        # If it's just a NavigableString (inline text)
        elif isinstance(element, NavigableString):
            text = element.strip()
            if text:
                lines.append("\t" * current_indent + text)

    # Join all lines, compress newlines once more
    full_text = "\n".join(lines)
    full_text = compress_newlines(full_text)
    return full_text


def generate_filename_from_url(url):
    """
    Create a filesystem-friendly filename from the URL.
    E.g., https://docs.movementnetwork.xyz/devs/getstarted/Your-first-Move-Module => devs_getstarted_Your-first-Move-Module.txt
    """
    parsed = urlparse(url)
    # Remove leading slash, replace subsequent slashes with underscore
    path = parsed.path.lstrip("/").replace("/", "_")
    if not path:
        path = "index"
    # e.g., "devs_getstarted_Your-first-Move-Module.txt"
    return path + ".txt"


def crawl(url):
    """
    Recursively crawl valid links in /devs/getstarted, extract content, write it to:
      - One master file (movement_learning_paths.txt)
      - One file per page in data/movement_learning_path/
    """
    if url in visited:
        return
    visited.add(url)

    print(f"Crawling: {url}")
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    main_container = get_main_container(soup)

    # Extract content
    page_content = parse_content_with_indentation(main_container)

    # Write content to:
    #   1) Master file (append)
    #   2) Separate file in data/movement_learning_path/
    if page_content:
        with open(OUTPUT_FILE_ALL, "a", encoding="utf-8") as f_all:
            f_all.write(f"URL: {url}\n{page_content}\n\n{'=' * 80}\n\n")

        filename = generate_filename_from_url(url)
        page_file_path = os.path.join(OUTPUT_FOLDER, filename)
        with open(page_file_path, "w", encoding="utf-8") as f_page:
            f_page.write(f"URL: {url}\n{page_content}\n")

    # Find links to follow
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        full_link = urljoin(url, href)
        if is_valid_url(full_link):
            crawl(full_link)


if __name__ == "__main__":
    # 1. Clear/create the single output file
    open(OUTPUT_FILE_ALL, "w", encoding="utf-8").close()

    # 2. Ensure the output folder exists
    ensure_output_folder_exists()

    # 3. Start crawling
    crawl(BASE_URL)

    print(f"\nDone! Combined content is in '{OUTPUT_FILE_ALL}',")
    print(f"and individual page files are in '{OUTPUT_FOLDER}/'.")
