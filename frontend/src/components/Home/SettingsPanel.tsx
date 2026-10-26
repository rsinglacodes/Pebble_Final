import React from 'react';
import { X, Sliders, Monitor, Volume2, Shield } from 'lucide-react';
import { useSettings } from '../../hooks/useSettings.ts';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onClose }) => {
  const { settings, updateSetting } = useSettings();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/25 backdrop-blur-[4px] cursor-pointer"
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-md bg-[#FAFAFB] rounded-[24px] border border-black/[0.08] shadow-[0_30px_70px_rgba(0,0,0,0.18)] p-6 z-10 flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-black/[0.06]">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-[#6C5CFF]" />
            <h3 className="text-lg font-semibold text-[#111113]">Settings & Preferences</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-cursor="button"
            className="w-8 h-8 rounded-full bg-white hover:bg-black/[0.05] border border-black/[0.06] flex items-center justify-center text-[#55555D] hover:text-[#111113] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Options */}
        <div className="space-y-4">
          {/* 1. Visualization Speed */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-[#6B6B73]">
              Step Walkthrough Speed
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['slow', 'normal', 'fast'] as const).map((spd) => (
                <button
                  key={spd}
                  type="button"
                  onClick={() => updateSetting('stepSpeed', spd)}
                  data-cursor="button"
                  className={`py-2 rounded-[12px] text-xs font-semibold capitalize transition-all cursor-pointer ${
                    settings.stepSpeed === spd
                      ? 'bg-[#111113] text-white shadow-2xs'
                      : 'bg-black/[0.04] text-[#55555D] hover:bg-black/[0.08]'
                  }`}
                >
                  {spd}
                </button>
              ))}
            </div>
          </div>

          {/* 2. Show ASCII and State Diagrams */}
          <div className="flex items-center justify-between py-2 border-t border-black/[0.04]">
            <div className="flex items-center gap-2.5">
              <Monitor className="w-4 h-4 text-[#8A8A90]" />
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-[#111113]">
                  State & Pointer Previews
                </span>
                <span className="text-[11px] text-[#8A8A90]">
                  Show variable boxes under algorithm steps
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.showAsciiGraph}
              onChange={(e) => updateSetting('showAsciiGraph', e.target.checked)}
              data-cursor="button"
              className="w-4 h-4 rounded text-[#6C5CFF] accent-[#6C5CFF] cursor-pointer"
            />
          </div>

          {/* 3. Audio Cues */}
          <div className="flex items-center justify-between py-2 border-t border-black/[0.04]">
            <div className="flex items-center gap-2.5">
              <Volume2 className="w-4 h-4 text-[#8A8A90]" />
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-[#111113]">
                  Sound Feedback
                </span>
                <span className="text-[11px] text-[#8A8A90]">
                  Play gentle clicks during step navigation
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.soundEffects}
              onChange={(e) => updateSetting('soundEffects', e.target.checked)}
              data-cursor="button"
              className="w-4 h-4 rounded text-[#6C5CFF] accent-[#6C5CFF] cursor-pointer"
            />
          </div>

          {/* 4. Privacy */}
          <div className="flex items-center justify-between py-2 border-t border-black/[0.04]">
            <div className="flex items-center gap-2.5">
              <Shield className="w-4 h-4 text-[#8A8A90]" />
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-[#111113]">
                  Local Storage Privacy
                </span>
                <span className="text-[11px] text-[#8A8A90]">
                  All chats stored locally on your device
                </span>
              </div>
            </div>
            <span className="text-[10px] font-semibold text-[#3CC8FF] px-2 py-0.5 rounded-full bg-[#3CC8FF]/10">
              Active
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 flex justify-end border-t border-black/[0.06]">
          <button
            type="button"
            onClick={onClose}
            data-cursor="button"
            className="px-5 py-2 rounded-full bg-[#111113] text-white text-xs font-semibold hover:bg-[#25252A] transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
