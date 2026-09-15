"""tool: searches SEC EDGAR full-text search for a company's recent filings, and fetches the raw text of one filing.

Acts as the source material for the RAG pipeline in module 3. The agent calls 'search_filings' to find a filing, then 'fetch_filing_text' to pull it before chunking + embedding."""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser

import os
import requests

SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
# ponytail: SEC requires a real contact string in the User-Agent or requests get 403'd.
# Swap in your own contact email before running this live.
HEADERS = {"User-Agent": os.environ.get("SEC_USER_AGENT", "FinScout research-agent contact@example.com")}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _company_matches(company: str, display_names: list[str]) -> bool:
    """EDGAR's `q` param is a free-text search over filing contents, not a
    company filter - a filing that just mentions `company` in passing (e.g.
    a competitor) can match. Require the company name to actually appear in
    the filer's own display name before treating a hit as theirs."""
    needle = _normalize(company)
    return any(needle in _normalize(name) for name in display_names)

def search_filings(company: str, form_type: str ="10-K", limit: int = 5)-> list[dict]:
    """Search EDGAR full-text search for `company`'s filings of `form_type`.

    Returns a list of dicts: {company, form_type, filing_date, accession_no, url}.
    On failure, returns a single-item list with an "error" key.
    """
    params = {"q": company, "forms": form_type}
    try:
        resp = requests.get(SEC_SEARCH_URL, params=params, headers=HEADERS, timeout =10)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
    except Exception as exc:
        return [{"error": f"EDGAR search failed: {exc}"}]

    # Full-text search indexes every document in a filing (exhibits
    # included) and ranks by text relevance, not by which doc is the
    # primary filing, how recent it is, or even whether it's the queried
    # company's own filing. Without filtering, the top hit can be an
    # exhibit (e.g. EX-21.1), a stale filing, or another company's filing
    # that merely mentions `company` in its text.
    primary_hits = [
        h for h in hits
        if h.get("_source", {}).get("file_type") == form_type
        and _company_matches(company, h.get("_source", {}).get("display_names") or [])
    ]
    primary_hits.sort(key=lambda h: h.get("_source", {}).get("file_date", ""), reverse=True)

    results = []
    for hit in primary_hits[:limit]:
        src = hit.get("_source", {})
        ciks = src.get("ciks") or []
        cik = (ciks[0] if ciks else "").lstrip("0")
        raw_id = hit.get("_id","")
        accession_no = raw_id.split(":")[0].replace("-","")
        filename = raw_id.split(":")[-1]
        results.append({
            "company": (src.get("display_names") or [company])[0],
            "form_type":src.get("form"),
            "filing_date": src.get("file_date"),
            "accession_no": accession_no,
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no}/{filename}"
        })
    return results

# Tags whose content is never meant to be read: script/style are the usual
# suspects, and modern SEC filings are inline XBRL, where <ix:header> holds
# a large block of tagged facts hidden from the rendered page (browsers
# skip it via CSS) - a plain tag-stripper would otherwise include it, and
# it can run past 100k characters before any real filing prose appears.
_SKIP_TAGS = {"script", "style", "ix:header"}


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)


def _html_to_text(markup: str) -> str:
    parser = _VisibleTextExtractor()
    parser.feed(markup)
    return " ".join(parser.parts)


def fetch_filing_text(url: str, max_chars: int = 50_000) -> str:
    """Fetches a filing doc at `url`, strips it down to visible text, then
    truncates to `max_chars`.

    SEC filings are HTML/inline-XBRL, not plain text - fetching `resp.text`
    directly returns markup and hidden XBRL tagging, not prose. Stripping
    first means `max_chars` budgets for actual filing content instead of
    being burned on tags before any real text is reached.

    truncation exists bc filings can run 500k+ chars and the RAG chunker
    needs a bounded input, not the whole document dumped in here."""

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return _html_to_text(resp.text)[:max_chars]
    except Exception as exc:
        return f"error: failed to fetch filing - {exc}"