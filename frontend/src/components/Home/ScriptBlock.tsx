import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check, Code } from 'lucide-react';

interface ScriptBlockProps {
  payload: Record<string, any> | any;
}

export const ScriptBlock: React.FC<ScriptBlockProps> = ({ payload }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!payload) return null;

  const jsonString = typeof payload === 'string' 
    ? payload 
    : JSON.stringify(payload, null, 2);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      setCopied(false);
    }
  };

  return (
    <div className="w-full my-2 rounded-[16px] bg-[#FAFAFB] border border-black/[0.08] shadow-2xs overflow-hidden select-none">
      {/* Header Bar */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-black/[0.02] transition-colors cursor-pointer"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-[#111113]">
          <Code className="w-4 h-4 text-[#6C5CFF]" />
          <span>Animation Script (JSON)</span>
          <span className="text-[10px] font-mono font-normal text-[#8A8A90] px-1.5 py-0.5 rounded bg-black/[0.04]">
            video_payload
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isOpen && (
            <button
              type="button"
              onClick={handleCopy}
              title="Copy JSON"
              aria-label="Copy JSON"
              className="p-1 rounded-md text-[#6B6B73] hover:text-[#111113] hover:bg-black/[0.06] transition-colors flex items-center gap-1 text-[11px] font-medium"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-600">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}

          <div className="text-[#8A8A90]">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
        </div>
      </button>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="border-t border-black/[0.06] bg-[#16161A] p-3.5 max-h-[340px] overflow-auto select-text">
          <pre className="font-mono text-xs text-[#E2E2E7] leading-relaxed whitespace-pre overflow-x-auto">
            {jsonString}
          </pre>
        </div>
      )}
    </div>
  );
};
