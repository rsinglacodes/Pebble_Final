import React from 'react';
import { ChatMessage } from '../../lib/chat.ts';

export type PebbleLanguage = 'python' | 'java' | 'cpp';

export const PEBBLE_LANG_KEY = 'pebble_code_lang';

export function getStoredLanguage(): PebbleLanguage {
  try {
    const val = localStorage.getItem(PEBBLE_LANG_KEY);
    if (val === 'python' || val === 'java' || val === 'cpp') {
      return val;
    }
  } catch {}
  return 'python';
}

export function setStoredLanguage(lang: PebbleLanguage): void {
  try {
    localStorage.setItem(PEBBLE_LANG_KEY, lang);
  } catch {}
}

export function normalizeLanguage(lang?: string): PebbleLanguage | null {
  if (!lang) return null;
  const l = lang.toLowerCase().trim();
  if (l === 'python' || l === 'py') return 'python';
  if (l === 'java') return 'java';
  if (l === 'cpp' || l === 'c++') return 'cpp';
  return null;
}

export function mentionsLanguage(text?: string): boolean {
  if (!text) return false;
  return /\b(python|java|cpp)\b|c\+\+/i.test(text);
}

interface LanguageChipsProps {
  message: ChatMessage;
  onSelectLanguage?: (lang: PebbleLanguage) => void;
}

const LANGUAGE_OPTIONS: { id: PebbleLanguage; label: string }[] = [
  { id: 'python', label: 'Python' },
  { id: 'java', label: 'Java' },
  { id: 'cpp', label: 'C++' },
];

export const LanguageChips: React.FC<LanguageChipsProps> = ({ message, onSelectLanguage }) => {
  const meta = message.meta;
  if (!meta) return null;

  // Check eligibility: can_generate or status found/no_solution/concept
  const canGenerate = Boolean(meta.can_generate);
  const status = meta.status;
  const isEligibleStatus = status === 'found' || status === 'no_solution' || status === 'concept';
  if (!canGenerate && !isEligibleStatus) {
    return null;
  }

  // If the user's message already names a language (python, java, c++, cpp) do NOT show the chips.
  const userPrompt = meta.userPrompt;
  if (mentionsLanguage(userPrompt)) {
    return null;
  }

  // Question to re-ask
  const questionToReask = userPrompt || meta.problem?.title || meta.video_request?.problem_title || '';
  if (!questionToReask) {
    return null;
  }

  // Current language
  const currentLang: PebbleLanguage =
    normalizeLanguage(meta.solution?.language) ||
    normalizeLanguage(meta.language) ||
    getStoredLanguage();

  // Available languages when status === 'found'
  const rawAvailable: string[] = Array.isArray(meta.available_languages) ? meta.available_languages : [];
  const availableList: PebbleLanguage[] = rawAvailable
    .map((lang: string) => normalizeLanguage(lang))
    .filter((l: PebbleLanguage | null): l is PebbleLanguage => l !== null);

  const handleChipClick = (lang: PebbleLanguage) => {
    if (lang === currentLang) return;

    // Save choice as new default
    setStoredLanguage(lang);

    if (onSelectLanguage) {
      onSelectLanguage(lang);
    } else {
      // Dispatch reask event to useChat
      window.dispatchEvent(
        new CustomEvent('pebble:reask', {
          detail: { text: questionToReask, language: lang },
        })
      );
    }
  };

  return (
    <div className="flex items-center flex-wrap gap-1 text-[12px] select-none mt-1 text-[#8A8A90]">
      <span className="font-normal mr-1">Show in:</span>
      {LANGUAGE_OPTIONS.map((item, idx) => {
        const isCurrent = currentLang === item.id;
        const isEnabled = status === 'found' ? availableList.includes(item.id) : true;

        return (
          <React.Fragment key={item.id}>
            {idx > 0 && <span className="text-[#C4C4C8] text-[10px] mx-0.5 select-none">·</span>}
            <button
              type="button"
              disabled={!isEnabled || isCurrent}
              onClick={() => handleChipClick(item.id)}
              data-cursor={isEnabled && !isCurrent ? 'button' : undefined}
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium transition-all ${
                isCurrent
                  ? 'bg-[#111113] text-white shadow-2xs'
                  : isEnabled
                  ? 'text-[#55555D] hover:text-[#111113] hover:bg-black/5 cursor-pointer'
                  : 'text-[#B0B0B8] opacity-40 cursor-not-allowed'
              }`}
            >
              {item.label}
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );
};
