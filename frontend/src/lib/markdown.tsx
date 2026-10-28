import React, { useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MarkdownProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownProps> = ({ content }) => {
  // Parse markdown content into structured blocks
  const blocks = useMemo(() => parseMarkdownBlocks(content), [content]);

  return (
    <div className="w-full text-[14.5px] leading-relaxed text-[#1F1F24] space-y-3 font-normal selection:bg-[#6C5CFF]/20">
      {blocks.map((block, idx) => {
        if (block.type === 'code') {
          return (
            <CodeBlock
              key={`code-${idx}`}
              language={block.language || 'code'}
              code={block.content}
            />
          );
        }

        if (block.type === 'h3') {
          return (
            <h3
              key={`h3-${idx}`}
              className="text-[17px] font-semibold text-[#111113] tracking-tight pt-2 border-b border-black/[0.05] pb-1"
            >
              <InlineText text={block.content} />
            </h3>
          );
        }

        if (block.type === 'h4') {
          return (
            <h4
              key={`h4-${idx}`}
              className="text-[15px] font-semibold text-[#111113] tracking-tight pt-1"
            >
              <InlineText text={block.content} />
            </h4>
          );
        }

        if (block.type === 'bullet') {
          return (
            <ul key={`ul-${idx}`} className="space-y-1.5 pl-4 list-disc marker:text-[#6C5CFF]">
              {block.items.map((item, itemIdx) => (
                <li key={`li-${itemIdx}`} className="text-[#333339]">
                  <InlineText text={item} />
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === 'table') {
          return (
            <div key={`tbl-${idx}`} className="overflow-x-auto my-2 rounded-xl border border-black/[0.06]">
              <table className="w-full text-left text-xs border-collapse bg-white/60">
                <thead>
                  <tr className="border-b border-black/[0.08] bg-black/[0.02]">
                    {block.headers.map((h, i) => (
                      <th key={i} className="p-2.5 font-semibold text-[#111113]">
                        <InlineText text={h} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((r, rIdx) => (
                    <tr
                      key={rIdx}
                      className="border-b border-black/[0.04] last:border-0 hover:bg-black/[0.01]"
                    >
                      {r.map((cell, cIdx) => (
                        <td key={cIdx} className="p-2.5 text-[#44444C]">
                          <InlineText text={cell} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        // Standard paragraph
        return (
          <p key={`p-${idx}`} className="text-[#28282E]">
            <InlineText text={block.content} />
          </p>
        );
      })}
    </div>
  );
};

// Component for rendering styled Code Block with copy button
interface CodeBlockProps {
  language: string;
  code: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    try {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback
    }
  };

  return (
    <div
      className="relative my-3 rounded-[16px] overflow-hidden shadow-[0_4px_16px_rgba(0,0,0,0.06)]"
      style={{ backgroundColor: '#FAFAFB', border: '1px solid rgba(0, 0, 0, 0.08)' }}
    >
      {/* Code Header Bar */}
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ backgroundColor: '#F1F1F4', borderBottom: '1px solid rgba(0, 0, 0, 0.06)' }}
      >
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#27C93F]/80" />
          <span
            className="text-[11px] font-mono font-medium uppercase ml-1.5 tracking-wider"
            style={{ color: '#6B6B73' }}
          >
            {language}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          data-cursor="button"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.05)', color: '#44444C' }}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-[8px] text-xs font-mono transition-all cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#3CC8FF]" />
              <span className="text-[11px]" style={{ color: '#3CC8FF' }}>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-[#6B6B73]" />
              <span className="text-[11px]" style={{ color: '#44444C' }}>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Body */}
      <div className="p-4 overflow-x-auto text-[13px] font-mono leading-relaxed selection:bg-[#6C5CFF]/20">
        <pre style={{ color: '#1B1B1F' }}>
          <code style={{ color: '#1B1B1F' }}>{code.trim()}</code>
        </pre>
      </div>
    </div>
  );
};

// Inline Text Parser (handles bold, italic, inline code)
const InlineText: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;

  // Split by code backticks first: `code`
  const parts = text.split(/(`[^`]+`)/g);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
          const rawCode = part.slice(1, -1);
          return (
            <code
              key={i}
              className="px-1.5 py-0.5 mx-0.5 rounded-[6px] bg-[#E8E8EC] text-[#5540E0] font-mono text-[12.5px] border border-[#DBDDE3] font-medium"
            >
              {rawCode}
            </code>
          );
        }

        // Process bold & italic inside normal text
        return <FormattedChunk key={i} text={part} />;
      })}
    </>
  );
};

const FormattedChunk: React.FC<{ text: string }> = ({ text }) => {
  // Regex for **bold** or *italic*
  const chunks = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);

  return (
    <>
      {chunks.map((chunk, j) => {
        if (chunk.startsWith('**') && chunk.endsWith('**') && chunk.length >= 4) {
          return (
            <strong key={j} className="font-semibold text-[#111113]">
              {chunk.slice(2, -2)}
            </strong>
          );
        }
        if (chunk.startsWith('*') && chunk.endsWith('*') && chunk.length >= 2) {
          return (
            <em key={j} className="italic text-[#222228]">
              {chunk.slice(1, -1)}
            </em>
          );
        }
        return <span key={j}>{chunk}</span>;
      })}
    </>
  );
};

// Parsing engine for markdown blocks
// Parsing engine for markdown blocks
type ParsedBlock =
  | { type: 'code'; language: string; content: string }
  | { type: 'h3'; content: string }
  | { type: 'h4'; content: string }
  | { type: 'bullet'; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'p'; content: string };

// "###", "#### ", "### Title" all match; "###hey" does not (it's plain text)
const HEADING_RE = /^(#{1,6})(?:\s+(.*))?$/;

function isBlockStart(t: string): boolean {
  return (
    t.startsWith('```') ||
    HEADING_RE.test(t) ||
    t.startsWith('- ') ||
    t.startsWith('* ') ||
    t.startsWith('|')
  );
}

function parseMarkdownBlocks(raw: string): ParsedBlock[] {
  const lines = raw.split('\n');
  const blocks: ParsedBlock[] = [];

  let i = 0;
  let guard = 0;
  const maxIterations = lines.length * 4 + 20; // safety net: can never hang

  while (i < lines.length && guard++ < maxIterations) {
    const trimmed = lines[i].trim();

    // Empty line
    if (trimmed.length === 0) {
      i++;
      continue;
    }

    // 1. Fenced code block (an unclosed fence while streaming is fine)
    if (trimmed.startsWith('```')) {
      const language = trimmed.replace(/^```/, '').trim() || 'code';
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: 'code', language, content: codeLines.join('\n') });
      i++;
      continue;
    }

    // 2. Headings (a heading with no text yet, e.g. "####" mid-stream, is skipped)
    const heading = HEADING_RE.exec(trimmed);
    if (heading) {
      const text = (heading[2] ?? '').trim();
      if (text) {
        blocks.push({ type: heading[1].length <= 3 ? 'h3' : 'h4', content: text });
      }
      i++;
      continue;
    }

    // 3. Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const items: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!(t.startsWith('- ') || t.startsWith('* '))) break;
        items.push(t.replace(/^[-*]\s+/, ''));
        i++;
      }
      blocks.push({ type: 'bullet', items });
      continue;
    }

    // 4. Tables
    if (trimmed.startsWith('|')) {
      const start = i;
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }
      if (tableLines.length >= 2) {
        const splitRow = (l: string) =>
          l.split('|').slice(1, -1).map((c) => c.trim());
        blocks.push({
          type: 'table',
          headers: splitRow(tableLines[0]),
          rows: tableLines.slice(2).map(splitRow),
        });
        continue;
      }
      i = start; // not a real table yet (still streaming): treat as a paragraph
    }

    // 5. Paragraph: ALWAYS consume the current line first (guarantees progress)
    const pLines: string[] = [trimmed];
    i++;
    while (i < lines.length) {
      const t = lines[i].trim();
      if (t.length === 0 || isBlockStart(t)) break;
      pLines.push(t);
      i++;
    }
    blocks.push({ type: 'p', content: pLines.join(' ') });
  }

  return blocks;
}