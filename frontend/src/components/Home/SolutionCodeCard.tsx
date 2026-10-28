import React, { useState, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { CodeBlock } from '../../lib/markdown.tsx';
import { request } from '../../lib/api.ts';

export interface SolutionCodeCardProps {
  meta: {
    problem?: {
      id?: string | number;
      [key: string]: any;
    };
    solution?: {
      id?: string | number;
      language?: string;
      code?: string;
      [key: string]: any;
    };
    available_languages?: string[];
    [key: string]: any;
  };
}

function formatLanguage(lang: string): string {
  const lower = lang.toLowerCase();
  if (lower === 'python') return 'Python';
  if (lower === 'java') return 'Java';
  if (lower === 'cpp' || lower === 'c++') return 'C++';
  if (lower === 'javascript' || lower === 'js') return 'JavaScript';
  if (lower === 'typescript' || lower === 'ts') return 'TypeScript';
  return lang.charAt(0).toUpperCase() + lang.slice(1);
}

export const SolutionCodeCard: React.FC<SolutionCodeCardProps> = ({ meta }) => {
  const problemId = meta.problem?.id;
  const initialLang = (meta.solution?.language || 'python').toLowerCase();
  const initialCode = meta.solution?.code || '';

  const availableLanguages: string[] = useMemo(() => {
    const list =
      Array.isArray(meta.available_languages) && meta.available_languages.length > 0
        ? meta.available_languages.map((l) => l.toLowerCase())
        : [initialLang];
    if (!list.includes(initialLang)) {
      list.unshift(initialLang);
    }
    return list;
  }, [meta.available_languages, initialLang]);

  const [displayedLang, setDisplayedLang] = useState<string>(initialLang);
  const [selectValue, setSelectValue] = useState<string>(initialLang);
  const [codeCache, setCodeCache] = useState<Record<string, string>>(() => ({
    [initialLang]: initialCode,
  }));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLanguageChange = async (newLang: string) => {
    if (newLang === displayedLang || loading) return;
    setError(null);
    setSelectValue(newLang);

    // Instant switch if already fetched
    if (codeCache[newLang]) {
      setDisplayedLang(newLang);
      return;
    }

    if (!problemId) {
      setError("Couldn't load that language");
      setSelectValue(displayedLang);
      return;
    }

    setLoading(true);
    try {
      const res = await request<Array<{ code: string }>>(
        `/problems/${problemId}/solutions?language=${encodeURIComponent(newLang)}`
      );
      if (res && res.length > 0 && res[0]?.code) {
        setCodeCache((prev) => ({
          ...prev,
          [newLang]: res[0].code,
        }));
        setDisplayedLang(newLang);
      } else {
        setError("Couldn't load that language");
        setSelectValue(displayedLang);
      }
    } catch {
      setError("Couldn't load that language");
      setSelectValue(displayedLang);
    } finally {
      setLoading(false);
    }
  };

  const currentCode = codeCache[displayedLang] ?? initialCode;

  const headerContent = useMemo(() => {
    if (availableLanguages.length <= 1) {
      return formatLanguage(displayedLang);
    }

    return (
      <span className="inline-flex items-center gap-2">
        <select
          value={selectValue}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={loading}
          data-cursor="button"
          style={{
            backgroundColor: '#FAFAFB',
            color: '#1B1B1F',
            border: '1px solid rgba(0, 0, 0, 0.12)',
            borderRadius: '6px',
            padding: '1px 6px',
            fontSize: '11px',
            fontWeight: 500,
            textTransform: 'none',
            cursor: loading ? 'wait' : 'pointer',
            outline: 'none',
          }}
          className="transition-colors hover:border-black/30 focus:border-[#6C5CFF]"
        >
          {availableLanguages.map((lang) => (
            <option
              key={lang}
              value={lang}
              style={{
                backgroundColor: '#FFFFFF',
                color: '#1B1B1F',
                textTransform: 'none',
              }}
            >
              {formatLanguage(lang)}
            </option>
          ))}
        </select>

        {loading && (
          <span
            className="inline-flex items-center gap-1 text-[11px] normal-case"
            style={{ color: '#8A8A90', textTransform: 'none', letterSpacing: 'normal' }}
          >
            <Loader2 className="w-3 h-3 animate-spin text-[#6C5CFF]" />
            <span>Loading…</span>
          </span>
        )}

        {error && !loading && (
          <span
            className="inline-flex items-center text-[11px] normal-case"
            style={{ color: '#DC2626', textTransform: 'none', letterSpacing: 'normal' }}
            role="status"
          >
            {error}
          </span>
        )}
      </span>
    );
  }, [availableLanguages, selectValue, displayedLang, loading, error]);

  return <CodeBlock language={headerContent as any} code={currentCode} />;
};
