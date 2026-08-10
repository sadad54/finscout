"use client";

import { useState } from "react";
import { researchStream, type ResearchEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PipelineTracker } from "@/components/research/pipeline-tracker";
import { StatTile } from "@/components/research/stat-tile";
import { MarkdownPanel } from "@/components/markdown-panel";

type MarketData = {
  ticker: string;
  price?: number;
  currency?: string;
  market_cap?: number;
  pe_ratio?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  sector?: string;
  error?: string;
};

export default function ResearchPage() {
  const [ticker, setTicker] = useState("");
  const [company, setCompany] = useState("");
  const [doneStages, setDoneStages] = useState<Set<string>>(new Set());
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function applyEvent(event: ResearchEvent) {
    if (event.type === "stage" && event.status === "done") {
      setDoneStages((prev) => new Set(prev).add(event.stage));
      if (event.stage === "market_data") setMarketData(event.result as MarketData);
    } else if (event.type === "final") {
      setMarkdown(event.markdown);
    } else if (event.type === "error") {
      setError(event.detail);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim() || !company.trim() || loading) return;

    setDoneStages(new Set());
    setMarketData(null);
    setMarkdown(null);
    setError(null);
    setLoading(true);

    try {
      for await (const event of researchStream(ticker, company)) {
        applyEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-10">
      <h1 className="text-lg font-semibold">Research Brief</h1>
      <p className="text-sm text-muted-foreground">
        Ticker + company in, a structured cited research brief out.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="Ticker, e.g. AAPL"
          disabled={loading}
        />
        <Input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="Company, e.g. Apple Inc."
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Researching…" : "Generate"}
        </Button>
      </form>

      {(loading || doneStages.size > 0) && <PipelineTracker done={doneStages} />}

      {marketData && !marketData.error && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Price"
            value={marketData.price ? `${marketData.price} ${marketData.currency ?? ""}` : "—"}
          />
          <StatTile label="P/E" value={marketData.pe_ratio ? String(marketData.pe_ratio) : "—"} />
          <StatTile
            label="Market cap"
            value={marketData.market_cap ? marketData.market_cap.toLocaleString() : "—"}
          />
          <StatTile
            label="52w range"
            value={
              marketData.fifty_two_week_low && marketData.fifty_two_week_high
                ? `${marketData.fifty_two_week_low}–${marketData.fifty_two_week_high}`
                : "—"
            }
          />
        </div>
      )}
      {marketData?.error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {marketData.error}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {error}
        </div>
      )}

      {markdown && <MarkdownPanel content={markdown} />}
    </main>
  );
}
