import React, { useState } from 'react';
import { MarkdownRenderer } from '../../lib/markdown.tsx';
import { ChatMessage, VisualStep } from '../../lib/chat.ts';
import { getSavedSession } from '../../lib/auth.ts';
import { ChevronRight, Play, CheckCircle2 } from 'lucide-react';
import { WatchVideoButton } from './WatchVideoButton.tsx';
import { SolutionCodeCard } from './SolutionCodeCard.tsx';

const FENCED_CODE_REGEX = /```[^\n`]*\r?\n[\s\S]*?```/;

interface MessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  onUpdateMeta?: (messageId: string, metaUpdates: Record<string, any>) => void;
}

export const Message: React.FC<MessageProps> = ({ message, isStreaming = false, onUpdateMeta }) => {
  const isUser = message.role === 'user';
  const session = getSavedSession();
  const userName = session?.name || 'Explorer';
  const userInitials = userName
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  if (isUser) {
    return (
      <div className="w-full flex justify-end items-end gap-2.5 my-3 select-text">
        <div className="max-w-[85%] sm:max-w-[70%] bg-[#FAFAFB] rounded-[20px] rounded-br-[6px] px-4 py-3 border border-black/[0.06] shadow-2xs text-[#111113] text-[14.5px] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
        <div className="w-7 h-7 rounded-full bg-[#16161A] text-white flex items-center justify-center font-semibold text-[10px] shrink-0 shadow-2xs select-none">
          {userInitials}
        </div>
      </div>
    );
  }

  // Assistant message
  const hasSolutionCard = Boolean(
    message.meta?.problem?.id && message.meta?.solution?.code
  );

  let beforeCode = '';
  let afterCode = '';
  let hasFencedCode = false;

  if (hasSolutionCard && message.content) {
    const match = FENCED_CODE_REGEX.exec(message.content);
    if (match && typeof match.index === 'number') {
      hasFencedCode = true;
      beforeCode = message.content.slice(0, match.index).trim();
      afterCode = message.content.slice(match.index + match[0].length).trim();
    }
  }

  return (
    <div className="w-full flex justify-start items-start gap-3 my-4 select-text">
      {/* Pebble Gradient Logo Avatar */}
      <div
        className="w-7 h-7 rounded-[10px] p-[1.5px] shrink-0 mt-1 select-none shadow-2xs"
        style={{
          background: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
        }}
      >
        <div className="w-full h-full bg-[#121217] rounded-[9px] flex items-center justify-center gap-0.5 px-0.5">
          <span className="w-1 h-1.5 bg-gradient-to-b from-white to-[#C7D2FE] rounded-full" />
          <span className="w-1 h-1.5 bg-gradient-to-b from-white to-[#A5F3FC] rounded-full" />
        </div>
      </div>

      {/* Assistant Content Box */}
      <div className="flex-1 max-w-[92%] sm:max-w-[85%] flex flex-col gap-3">
            <div className="relative">
              {hasSolutionCard ? (
                hasFencedCode ? (
                  <>
                    {beforeCode ? <MarkdownRenderer content={beforeCode} /> : null}
                    <SolutionCodeCard meta={message.meta} />
                    {afterCode ? <MarkdownRenderer content={afterCode} /> : null}
                  </>
                ) : (
                  <>
                    {message.content ? <MarkdownRenderer content={message.content} /> : null}
                    <SolutionCodeCard meta={message.meta} />
                  </>
                )
              ) : message.content ? (
                <MarkdownRenderer content={message.content} />
              ) : isStreaming ? (
                <div className="flex items-center gap-1.5 text-xs text-[#8A8A90] py-1 select-none">
                  <span className="w-2 h-2 rounded-full bg-[#6C5CFF] animate-ping" />
                  <span>Thinking & breaking down steps...</span>
                </div>
              ) : null}

              {/* Glowing cursor bar during streaming */}
              {isStreaming && message.content && (
                <span className="inline-block w-1.5 h-4 ml-1 bg-gradient-to-b from-[#6C5CFF] to-[#3CC8FF] rounded-full animate-pulse align-middle" />
              )}
            </div>

        {/* Visual Step Walkthrough Box */}
        {message.visualSteps && message.visualSteps.length > 0 && (
          <VisualStepsCard steps={message.visualSteps} />
        )}

        {/* Video Solution when video-capable */}
        {message.meta?.can_generate && message.meta?.video_request && (
          <div className="flex flex-col gap-1 mt-1">
            <WatchVideoButton
              videoRequest={message.meta.video_request}
              initialVideoUrl={message.meta.video_url}
              initialJobId={message.meta.video_job_id}
              onMetaUpdate={(updates) => onUpdateMeta?.(message.id, updates)}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// Interactive Visual Step Walkthrough Card
const VisualStepsCard: React.FC<{ steps: VisualStep[] }> = ({ steps }) => {
  const [activeStep, setActiveStep] = useState(0);

  const current = steps[activeStep] || steps[0];

  return (
    <div className="my-2 rounded-[20px] bg-white/80 border border-black/[0.08] shadow-xs p-4 select-none">
      <div className="flex items-center justify-between border-b border-black/[0.06] pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-[#6C5CFF]/10 text-[#6C5CFF] flex items-center justify-center">
            <Play className="w-3 h-3 fill-current" />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-[#111113]">
            Algorithm Step Walkthrough
          </span>
        </div>
        <span className="text-xs font-mono text-[#8A8A90]">
          Step {activeStep + 1} of {steps.length}
        </span>
      </div>

      {/* Step Pills Selector */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
        {steps.map((st, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setActiveStep(i)}
            data-cursor="button"
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer shrink-0 ${
              activeStep === i
                ? 'bg-[#111113] text-white shadow-2xs'
                : 'bg-black/[0.04] text-[#55555D] hover:bg-black/[0.08]'
            }`}
          >
            <span className="w-4 h-4 rounded-full bg-white/20 text-[10px] flex items-center justify-center">
              {st.step}
            </span>
            <span>{st.label}</span>
          </button>
        ))}
      </div>

      {/* Step Details */}
      <div className="mt-3 p-3.5 rounded-[14px] bg-[#F7F7F8] border border-black/[0.04] space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#111113]">
          <CheckCircle2 className="w-4 h-4 text-[#3CC8FF]" />
          <span>{current.label}</span>
        </div>
        <p className="text-xs sm:text-[13px] text-[#44444C] leading-relaxed">
          {current.description}
        </p>
        {current.statePreview && (
          <div className="mt-2 px-3 py-1.5 rounded-[8px] bg-[#16161A] text-[#A5F3FC] font-mono text-xs overflow-x-auto">
            {current.statePreview}
          </div>
        )}
      </div>

      {/* Step Navigation Controls */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-black/[0.04]">
        <button
          type="button"
          onClick={() => setActiveStep((prev) => Math.max(0, prev - 1))}
          disabled={activeStep === 0}
          data-cursor="button"
          className="text-xs font-medium text-[#6B6B73] hover:text-[#111113] disabled:opacity-30 disabled:hover:text-[#6B6B73] cursor-pointer"
        >
          ← Previous
        </button>
        <button
          type="button"
          onClick={() => setActiveStep((prev) => Math.min(steps.length - 1, prev + 1))}
          disabled={activeStep === steps.length - 1}
          data-cursor="button"
          className="text-xs font-medium text-[#6C5CFF] hover:text-[#5241E0] disabled:opacity-30 flex items-center gap-0.5 cursor-pointer"
        >
          <span>Next step</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
