import React from 'react';
import { ArrowUpRight } from 'lucide-react';

interface SuggestionChipsProps {
  onSelect: (prompt: string) => void;
}

const STARTERS = [
  {
    label: 'Explain Two Sum with two pointers',
    category: 'Array / Hash',
  },
  {
    label: 'How does Binary Search divide the array?',
    category: 'Search / Log N',
  },
  {
    label: 'Visualize Merge Sort step-by-step',
    category: 'Divide & Conquer',
  },
  {
    label: 'Time complexity of DFS vs BFS',
    category: 'Graph / Traversal',
  },
];

export const SuggestionChips: React.FC<SuggestionChipsProps> = ({ onSelect }) => {
  return (
    <div className="w-full max-w-2xl grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-6 select-none">
      {STARTERS.map((item, idx) => (
        <button
          key={idx}
          type="button"
          onClick={() => onSelect(item.label)}
          data-cursor="button"
          className="group relative flex items-center justify-between p-3.5 sm:p-4 rounded-[18px] bg-white/70 hover:bg-white border border-black/[0.06] hover:border-black/[0.12] shadow-xs hover:shadow-sm text-left transition-all duration-200 cursor-pointer active:scale-[0.98]"
        >
          <div className="flex flex-col pr-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6C5CFF]">
              {item.category}
            </span>
            <span className="text-[13px] font-medium text-[#111113] group-hover:text-[#5241E0] transition-colors mt-0.5 line-clamp-1">
              {item.label}
            </span>
          </div>

          <div className="w-6 h-6 rounded-full bg-black/[0.04] group-hover:bg-[#111113] group-hover:text-white flex items-center justify-center shrink-0 transition-colors text-[#8A8A90]">
            <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </div>
        </button>
      ))}
    </div>
  );
};
