import re
from urllib.parse import urlparse
from langchain_core.messages import ToolMessage
from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain

SKIP_SCRAPE_DOMAINS = {
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
}

def extract_text(content) -> str:
    """Normalize provider-specific content blocks into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(text)
            else:
                parts.append(str(block))
        return "\n".join(parts)

    return str(content)

def get_tool_outputs(agent_result: dict) -> str:
    """Return the actual tool output messages from a LangChain agent run."""
    outputs = [
        extract_text(message.content)
        for message in agent_result.get("messages", [])
        if isinstance(message, ToolMessage)
    ]
    return "\n\n".join(outputs)

def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"URL:\s*(https?://\S+)", text)
    return [url.rstrip(").,]") for url in urls]

def should_skip_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in SKIP_SCRAPE_DOMAINS)

def scrape_with_reader_agent(reader_agent, url: str) -> str:
    reader_result = reader_agent.invoke({
        "messages": [("user", f"Scrape this exact URL for deeper research content: {url}")]
    })
    return (
        get_tool_outputs(reader_result)
        or extract_text(reader_result["messages"][-1].content)
    )

def scrape_working_urls(reader_agent, search_results: str, max_pages: int = 3) -> str:
    scraped_pages = []

    for url in extract_urls(search_results):
        if should_skip_url(url):
            continue

        scraped = scrape_with_reader_agent(reader_agent, url)
        if scraped and not scraped.startswith("Could not scrape URL:"):
            scraped_pages.append(f"Source: {url}\n\n{scraped}")

        if len(scraped_pages) >= max_pages:
            break

    if scraped_pages:
        return "\n\n----\n\n".join(scraped_pages)

    return "Could not scrape any search result URL. Using search snippets only."


def run_research_pipeline(topic: str, progress_callback=None) -> dict:
    """
    Run the full search -> scrape -> write -> critique pipeline.

    progress_callback, if provided, is called as:
        progress_callback(step_key: str, status: str, data: str | None)

    where step_key is one of "search", "scrape", "write", "critique",
    status is one of "running", "done", and data is the step's output
    (only passed when status == "done").
    """

    def notify(step_key: str, status: str, data: str | None = None) -> None:
        if progress_callback:
            progress_callback(step_key, status, data)

    state = {}

    # ---- Step 1: Search Agent ----
    # This is only to check the results in the console, the actual results are sent to the browser via websocket.
    print("\n" + " ="*50)
    print("Step 1: Search Agent is Working...")
    print("=" *50)
    notify("search", "running")

    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent reliable and detailed information about: {topic}")]
    })
    state["search_results"] = (
        get_tool_outputs(search_result)
        or extract_text(search_result["messages"][-1].content)
    )

    print("\n Search result \n", state['search_results'])
    notify("search", "done", state["search_results"])

    # ---- Step 2: Reader Agent ----
    print("\n" + " ="*50)
    print("Step 2: Reader Agent is Scraping top resources...")
    print("=" *50)
    notify("scrape", "running")

    reader_agent = build_reader_agent()
    state['scraped_content'] = scrape_working_urls(reader_agent, state['search_results'], max_pages=3)

    print("\n Scraped content: \n", state['scraped_content'])
    notify("scrape", "done", state["scraped_content"])

    # ---- Step 3: Writer Chain ----
    print("\n" + " ="*50)
    print("Step 3: Writer is Drafting the report...")
    print("=" *50)
    notify("write", "running")

    research_combined = (
        f"SEARCH RESULTS: \n {state['search_results']} \n\n"
        f"DEATAILED SCRAPED CONTENT: \n {state['scraped_content']}"
    )

    state['report'] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\n Final Report: \n", state['report'])
    notify("write", "done", state["report"])

    # ---- Step 4: Critic Chain ----
    print("\n" + " ="*50)
    print("Step 4: Critic is Reviewing the report...")
    print("=" *50)
    notify("critique", "running")

    state['feedback'] = critic_chain.invoke({
        "report": state['report']
    })

    print("\n Critic Report: \n", state['feedback'])
    notify("critique", "done", state["feedback"])

    return state

if __name__ == "__main__":
    topic = input("\n Enter a research topic: ")
    run_research_pipeline(topic)