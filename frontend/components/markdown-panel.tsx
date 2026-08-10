import ReactMarkdown from "react-markdown";

export function MarkdownPanel({ content }: { content: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none rounded-md border border-border bg-card p-4">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
