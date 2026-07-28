import os, json, re, urllib.parse, urllib.request
from agents.base_agent import BaseAgent

class SearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "search_agent",
            "Search the web, fetch web pages, extract information, and answer questions",
        )
        self.capabilities = ["search", "web", "google", "wiki", "wikipedia", "lookup", "find", "question"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "wikipedia" in t or "wiki" in t:
            query = self._extract_query(task, ["wikipedia", "wiki"])
            return self._search_wikipedia(query)

        if "search" in t or "google" in t:
            query = self._extract_query(task, ["search", "google", "for"])
            return self._web_search(query)

        if "url" in t or "http" in t or "fetch" in t:
            url = self._extract_url(task)
            if url:
                return self._fetch_page(url)
            return "SearchAgent: No URL found in message"

        if "news" in t:
            return "SearchAgent: Web search is simulated. For real results, use: curl https://news.google.com"

        return (f"SearchAgent: Available commands:\n"
                f"  wikipedia <query> - Search Wikipedia\n"
                f"  search <query> - Web search\n"
                f"  fetch <url> - Fetch a web page\n"
                f"  news - Latest news headlines")

    def _extract_query(self, task, keywords):
        result = task
        for kw in keywords:
            result = re.sub(r'\b' + kw + r'\b', '', result, flags=re.IGNORECASE)
        result = result.strip().strip('"').strip("'")
        return result or "web os operating system"

    def _extract_url(self, task):
        urls = re.findall(r'https?://[^\s]+', task)
        return urls[0] if urls else None

    def _search_wikipedia(self, query):
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "WebOS/2.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            result = f"SearchAgent: Wikipedia - {data.get('title', query)}\n\n"
            result += data.get("extract", "No summary available")[:1000]
            if "thumbnail" in data:
                result += f"\n\nImage: {data['thumbnail'].get('source', 'N/A')}"
            return result
        except urllib.error.HTTPError as e:
            return f"SearchAgent: Wikipedia page not found ({e.code})"
        except Exception as e:
            return f"SearchAgent: Wikipedia search failed: {e}"

    def _web_search(self, query):
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8", errors="replace")
            titles = re.findall(r'class="result__title">(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'class="result__snippet">(.*?)</(?:a|div)', html, re.DOTALL)
            links = re.findall(r'class="result__url"[^>]*href="(https?://[^"]+)"', html)
            results = []
            for i in range(min(5, len(titles))):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                link = links[i] if i < len(links) else ""
                results.append(f"  {i+1}. {title}\n     {snippet[:150]}")
            if results:
                return f"SearchAgent: Results for '{query}'\n\n" + "\n\n".join(results)
            return f"SearchAgent: No results found for '{query}'"
        except Exception as e:
            return f"SearchAgent: Search failed: {e}"

    def _fetch_page(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode("utf-8", errors="replace")
            title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "No title"
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()[:2000]
            return f"SearchAgent: Fetched {url}\nTitle: {title}\n\n{text[:1000]}"
        except Exception as e:
            return f"SearchAgent: Fetch failed: {e}"
