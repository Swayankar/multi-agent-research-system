# Multi-Agent AI Research System

A FastAPI web app that runs a four-step AI research pipeline:

1. Search the web for relevant sources.
2. Scrape readable content from selected result URLs.
3. Write a structured research report.
4. Critique the report and provide feedback.

The browser UI streams live progress over a WebSocket while the synchronous research pipeline runs in a background executor.

## Project Structure

```text
.
|-- app.py                  # FastAPI app, static/template setup, WebSocket endpoint
|-- agents.py               # LLM setup, LangChain agents, writer chain, critic chain
|-- pipeline.py             # Search -> scrape -> write -> critique orchestration
|-- tools.py                # Tavily web search tool and URL scraping tool
|-- requirements.txt        # Python dependencies
|-- templates/
|   `-- index.html          # Main web UI
`-- static/
    |-- script.js           # Frontend WebSocket and UI state logic
    |-- style.css           # Frontend styling
    |-- marked.min.js       # Markdown rendering in browser
    `-- purify.min.js       # Sanitizes rendered markdown
```

## Requirements

- Python 3.11 or newer
- Tavily API key for web search
- LLM provider API key for the model configured in `agents.py`

The current code uses OpenRouter by default:

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
TAVILY_API_KEY=your_tavily_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Example if any other API kets are used
GOOGLE_API_KEY=your_google_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

Only the keys for the tools/providers you actually use are required. With the current default OpenRouter model, you need `TAVILY_API_KEY` and `OPENROUTER_API_KEY`.

## Run the Web App

From the project root:

```powershell
.\.venv\Scripts\activate
python -m uvicorn app:app --reload
```

Open:

```text
http://localhost:8000
```

Enter a research topic and click **Run pipeline**. The UI will show live status for all four stages and display the final report plus critique.

## Run the Pipeline in the Terminal

You can also run the pipeline directly without the web UI:

```powershell
.\.venv\Scripts\activate
python pipeline.py
```

Then enter a topic when prompted.

## How It Works

`app.py` serves the UI and exposes:

```text
GET /
WS  /ws/research
```

When the browser opens a WebSocket connection, it sends the research topic to `/ws/research`. The app runs `run_research_pipeline()` from `pipeline.py` in a background executor and forwards each progress update back to the browser.

The pipeline stages are:

- `search`: builds a search agent and calls the Tavily-powered `web_search` tool.
- `scrape`: extracts URLs from search results and scrapes up to a configured number of pages.
- `write`: sends search and scraped content to the writer chain.
- `critique`: sends the report to the critic chain for scoring and feedback.

## Current Limits

Search result count is controlled in `tools.py`:

```python
results = tavily.search(query=query, max_results=5)
```

Scraped page count is controlled in `pipeline.py`:

```python
state["scraped_content"] = scrape_working_urls(reader_agent, state["search_results"], max_pages=3)
```

Increase these values if you want deeper research, but expect longer run times and higher API usage.

## Switching LLM Providers

Edit `agents.py` to change the active model/provider.

Examples already present in the file:

```python
# llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
```

Make sure the matching API key is present in `.env`.

## Troubleshooting

If you see `Internal Server Error` at `/`, make sure you are running the current app entry point:

```powershell
python -m uvicorn app:app --reload
```

If the page loads but the run fails, check the terminal where Uvicorn is running. Common causes are:

- Missing `.env` file
- Missing or invalid API key
- Provider package not installed
- Tavily quota or rate limit
- A selected website blocking scraping

If dependencies look out of sync, reinstall them:

```powershell
pip install -r requirements.txt
```

## Security Notes

Do not commit real API keys. Keep `.env` local and private. If an API key is ever shared publicly, rotate it in the provider dashboard.
