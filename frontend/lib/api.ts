export type AskEvent =
  | { type: "tool_call"; tool: string; args: Record<string, unknown> }
  | { type: "tool_result"; tool: string; result: unknown }
  | { type: "final"; content: string }
  | { type: "error"; detail: string };

export type ResearchEvent =
  | { type: "stage"; stage: string; status: "start" | "done"; result?: unknown }
  | { type: "final"; markdown: string }
  | { type: "error"; detail: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function* streamSSE<T>(path: string, body: unknown): AsyncGenerator<T> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`request to ${path} failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalReceived = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data: "));
        if (line) {
          const event = JSON.parse(line.slice("data: ".length));
          if (event.type === "final" || event.type === "error") terminalReceived = true;
          yield event as T;
        }
      }
    }
    if (!terminalReceived) throw new Error("Response stream ended before completion. Please retry.");
  } finally {
    await reader.cancel().catch(() => {});
  }
}

export function askStream(question: string) {
  return streamSSE<AskEvent>("/ask/stream", { question });
}

export function researchStream(ticker: string, company: string) {
  return streamSSE<ResearchEvent>("/research/stream", { ticker, company });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return resp.ok;
  } catch {
    return false;
  }
}
