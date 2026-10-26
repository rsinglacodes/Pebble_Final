import React, { useEffect, useState } from 'react';
import { RobotCompanion } from '../RobotCompanion.tsx';
import { SuggestionChips } from './SuggestionChips.tsx';
import { getSavedSession } from '../../lib/auth.ts';
import { getPointer, subscribeIdle } from '../../lib/pointerStore.ts';

interface GreetingProps {
  onSelectPrompt: (prompt: string) => void;
}

export const Greeting: React.FC<GreetingProps> = ({ onSelectPrompt }) => {
  const session = getSavedSession();
  const rawName = session?.name || 'Explorer';
  const firstName = rawName.trim().split(' ')[0];

  const pointer = getPointer();
  const [isIdle, setIsIdle] = useState(pointer.isIdle);

  useEffect(() => {
    return subscribeIdle((idle) => {
      setIsIdle(idle);
    });
  }, []);

  return (
    <div className="w-full flex-1 flex flex-col items-center justify-center text-center px-4 py-8 select-none my-auto">
      {/* Compact 3D Robot Companion in calm mode */}
      <div className="relative mb-2">
        <RobotCompanion
          size={200}
          calm={true}
          clientX={pointer.clientX}
          clientY={pointer.clientY}
          isIdle={isIdle}
        />
      </div>

      {/* Headline */}
      <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#111113] mt-2">
        What are we visualizing today,{' '}
        <span
          style={{
            backgroundImage: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {firstName}
        </span>
        ?
      </h2>

      {/* Subtitle */}
      <p className="text-sm sm:text-base text-[#6B6B73] max-w-md mt-2 font-normal leading-relaxed">
        Ask a coding question, paste a LeetCode problem, or pick a starter below.
      </p>

      {/* Quick Prompt Chips */}
      <SuggestionChips onSelect={onSelectPrompt} />
    </div>
  );
};
