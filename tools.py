from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from rich import print
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns Title, URLs, and snippets."""
    results = tavily.search(query=query, max_results=5)

    out = []

    for r in results['results']:
        out.append(
            f"Title': {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}\n"
        )

    return "\n----\n".join(out)

@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code >= 400:
            return f"Could not scrape URL: HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        blocked_phrases = [
            "access denied",
            "temporarily unavailable",
            "you do not have access",
            "error reference number",
            "enable javascript",
            "captcha",
        ]
        if any(phrase in text.lower() for phrase in blocked_phrases):
            return "Could not scrape URL: page blocked access or requires browser verification"

        return text[:3000]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"

