import ReactMarkdown from "react-markdown";

export function MarkdownPanel({ content }: { content: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none rounded-md border border-t-2 border-border border-t-accent-green/30 bg-card p-4">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
