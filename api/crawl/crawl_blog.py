import requests
from bs4 import BeautifulSoup
import re
import os
import time
import string

# Base URL for the blog page
BLOG_URL = "https://blog.movementlabs.xyz/"
BASE_URL = "https://blog.movementlabs.xyz/"

# Headers to mimic a browser (optional but sometimes useful)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/90.0.4430.93 Safari/537.36"
}


def sanitize_filename(title):
    """
    Create a safe filename from the title by keeping only alphanumeric characters, dashes and underscores.
    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in title if c in valid_chars)
    filename = filename.replace(" ", "_")
    return filename.strip("_") + ".txt"


def get_article_links(blog_url):
    """
    Get all article links from the blog page.
    Assumes that article links have '/article/' in their URL.
    """
    print(f"Fetching blog page: {blog_url}")
    response = requests.get(blog_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags that contain '/article/' in their href.
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Check if it looks like an article URL.
        if re.search(r"/article/", href):
            # Ensure that we have an absolute URL.
            if not href.startswith("http"):
                href = BASE_URL + href
            links.add(href)
    print(f"Found {len(links)} article links.")
    return list(links)


def extract_article_content(article_url):
    """
    Given an article URL, fetch the page and extract the title and main content.
    This function attempts to skip headers, footers, and buttons by selecting the main article content.
    """
    print(f"Fetching article: {article_url}")
    response = requests.get(article_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Get the title. Try to use <h1> if available.
    title_tag = soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        # Fallback to <title> tag from the head
        title = soup.title.string if soup.title else "untitled_article"
    print(f"Article title: {title}")

    # Try to find the main article content.
    # This example assumes the content is wrapped in an <article> tag.
    content_container = soup.find("article")
    # if not content_container:
    #     # If there is no <article> tag, try common alternatives.
    #     content_container = soup.find("div", class_=re.compile(r"(content|article)"))

    if content_container:
        # Remove unwanted elements from the content if needed.
        for unwanted in content_container.find_all(['header', 'footer', 'nav', 'button']):
            unwanted.decompose()
        # Extract text with a bit of spacing.
        content = content_container.get_text(separator="\n", strip=True)
    else:
        # If no container found, fallback to getting all paragraph texts.
        paragraphs = soup.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs)

    return title, content


def save_article(title, content, output_dir="articles"):
    """
    Save the article content to a file with a sanitized filename.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = sanitize_filename(title)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved article to {filepath}")


def main():
    # article_links = get_article_links(BLOG_URL)
    # article_links = [
    #     'https://blog.movementlabs.xyz/article/securing-smart-contracts-a-devs-guide-part-i',
    #     "https://blog.movementlabs.xyz/article/binance-labs-backs-movement-labs-mission-to-bring-move-everywhere",
    #     "https://blog.movementlabs.xyz/article/securing-smart-contracts-a-devs-guide-part-ii",
    #     "https://blog.movementlabs.xyz/article/movement-sdk-unifying-the-blockchain-universe-2",
    #     "https://blog.movementlabs.xyz/article/brkt-brings-gamblefi-to-the-masses-on-movement",
    #     "https://blog.movementlabs.xyz/article/superchain-gives-movement-devs-a-powerful-multichain-indexer",
    #     "https://blog.movementlabs.xyz/article/vcred-unites-ai-and-liquidity-management-on-movement",
    #     "https://blog.movementlabs.xyz/article/community-vs-insiders-can-they-both-win",
    #     "https://blog.movementlabs.xyz/article/tutorial-eigenlayer-avs-movement-network",
    #     "https://blog.movementlabs.xyz/article/movements-battle-of-olympus-calls-for-heroes",
    #     "https://blog.movementlabs.xyz/article/what-is-movement-move-blockchain",
    #     "https://blog.movementlabs.xyz/article/movement-testnet-movedrop-parthenon-how-to-use",
    #     "https://blog.movementlabs.xyz/article/frax-movement-defi-blockc",
    #     "https://blog.movementlabs.xyz/article/security-and-fast-finality-settlement",
    #     "https://blog.movementlabs.xyz/article/postconfirmations-L2s-rollups-blockchain-movement",
    #     "https://blog.movementlabs.xyz/article/dag-sequencing-decentralized-sequencer-blockchain",
    #     "https://blog.movementlabs.xyz/article/battle-of-olympus-hackathon-winners-movement",
    #     "https://blog.movementlabs.xyz/article/move-best-language-smart-contracts-blockchain-development",
    #     "https://blog.movementlabs.xyz/article/Movement-Gaming-Blockchain-Games",
    #     "https://blog.movementlabs.xyz/article/movement-depin-blockchain-applications"
    # ]
    article_links =[
        "https://developer.movementnetwork.xyz/movement-mainia",
        "https://www.movementnetwork.xyz/movedrop"
    ]
    # Process each article link
    for url in article_links:
        try:
            title, content = extract_article_content(url)
            save_article(title, content)
            # Be polite with a small delay between requests.
            time.sleep(1)
        except Exception as e:
            print(f"Error processing {url}: {e}")


if __name__ == "__main__":
    main()
