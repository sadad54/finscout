import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { researchStream } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

function mockResponse(chunks) {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
      controller.close();
    },
  }));
  return () => { globalThis.fetch = original; };
}

async function collect() {
  const events = [];
  for await (const event of researchStream('AAPL', 'Apple')) events.push(event);
  return events;
}

test('fragmented SSE frames preserve final response', async () => {
  const restore = mockResponse(['data: {"type":"sta', 'ge","stage":"news","status":"start"}\n\n',
    'data: {"type":"final","markdown":"fixture report"}\n\n']);
  try { assert.equal((await collect()).at(-1).markdown, 'fixture report'); }
  finally { restore(); }
});

test('provider error is delivered to the UI', async () => {
  const restore = mockResponse(['data: {"type":"error","detail":"provider unavailable"}\n\n']);
  try { assert.equal((await collect())[0].detail, 'provider unavailable'); }
  finally { restore(); }
});

test('truncated streams reject instead of silently completing', async () => {
  const restore = mockResponse(['data: {"type":"stage","stage":"news","status":"start"}\n\n']);
  try { await assert.rejects(collect, /ended before completion/); }
  finally { restore(); }
});
