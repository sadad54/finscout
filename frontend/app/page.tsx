"use client";

import { useState } from "react";
import { askStream, type AskEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToolStep } from "@/components/chat/tool-step";
import { MarkdownPanel } from "@/components/markdown-panel";

type Step = { tool: string; args: Record<string, unknown>; done: boolean };

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function applyEvent(event: AskEvent) {
    if (event.type === "tool_call") {
      setSteps((prev) => [...prev, { tool: event.tool, args: event.args, done: false }]);
    } else if (event.type === "tool_result") {
      setSteps((prev) => {
        const next = [...prev];
        const idx = next.map((s) => s.done).lastIndexOf(false);
        if (idx !== -1) next[idx] = { ...next[idx], done: true };
        return next;
      });
    } else if (event.type === "final") {
      setAnswer(event.content);
    } else if (event.type === "error") {
      setError(event.detail);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setSteps([]);
    setAnswer(null);
    setError(null);
    setLoading(true);

    try {
      for await (const event of askStream(question)) {
        applyEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-10">
      <h1 className="text-lg font-semibold">Ask FinScout</h1>
      <p className="text-sm text-muted-foreground">
        Open-ended research questions — the agent decides which tools to call.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What's NVDA trading at, and what's its P/E?"
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Thinking…" : "Ask"}
        </Button>
      </form>

      <div className="flex flex-col gap-2">
        {steps.map((step, i) => (
          <ToolStep key={i} tool={step.tool} args={step.args} done={step.done} />
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {error}
        </div>
      )}

      {answer && <MarkdownPanel content={answer} />}
    </main>
  );
}
