"""tool: searches SEC EDGAR full-text search for a company's recent filings, and fetches the raw text of one filing.

Acts as the source material for the RAG pipeline in module 3. The agent calls 'search_filings' to find a filing, then 'fetch_filing_text' to pull it before chunking + embedding."""

from __future__ import annotations

import requests

SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
# ponytail: SEC requires a real contact string in the User-Agent or requests get 403'd.
# Swap in your own contact email before running this live.
HEADERS = {"User-Agent": "FinScout research-agent contact@example.com"}

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

    results = []
    for hit in hits[:limit]:
        src = hit.get("_source", {})
        cik=(src.get("cik") or "").lstrip("0")
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

def fetch_filing_text(url: str, max_chars:int = 50_000) -> str:
    """fetches the raw text of a filing doc at 'url', then truncates to 'max_chars'.
    
    truncation exists bc filings can run 500k+ chars and the RAG chunker needs a bounded input, not the whole document dumped in here."""

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text[:max_chars]
    except Exception as exc:
        return f"error: failed to fetch filing - {exc}"