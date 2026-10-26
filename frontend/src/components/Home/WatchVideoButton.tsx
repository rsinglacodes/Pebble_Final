import React, { useState, useEffect, useRef } from 'react';
import { Play, RotateCcw, AlertCircle, Film, Sparkles, Loader2 } from 'lucide-react';
import {
  CreateVideoJobRequest,
  createVideoJob,
  getVideoJob,
  getVideoResult,
  retryVideoJob,
} from '../../lib/video.ts';
import { ApiError } from '../../lib/api.ts';

interface WatchVideoButtonProps {
  videoRequest: CreateVideoJobRequest;
  initialVideoUrl?: string | null;
  initialJobId?: string | null;
  onMetaUpdate?: (metaUpdates: { video_job_id?: string; video_url?: string }) => void;
}

type JobState = 'idle' | 'queued' | 'running' | 'completed' | 'failed';

export const WatchVideoButton: React.FC<WatchVideoButtonProps> = ({
  videoRequest,
  initialVideoUrl,
  initialJobId,
  onMetaUpdate,
}) => {
  // If video was already completed, show immediately with no waiting
  const [status, setStatus] = useState<JobState>(() =>
    initialVideoUrl ? 'completed' : 'idle'
  );
  const [videoUrl, setVideoUrl] = useState<string | null>(initialVideoUrl || null);
  const [jobId, setJobId] = useState<string | null>(initialJobId || null);
  const [stage, setStage] = useState<string>('');
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollStartRef = useRef<number>(0);
  const isMountedRef = useRef(true);

  // Clean up polling interval
  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopPolling();
    };
  }, []);

  const getFriendlyErrorMessage = (err: unknown): string => {
    if (err instanceof ApiError) {
      if (err.status === 503) {
        return 'The video service is currently busy. Please wait a moment and retry.';
      }
      if (err.status === 422) {
        return 'Unable to generate video for this solution format.';
      }
      return err.message;
    }
    return 'An unexpected error occurred while generating the video.';
  };

  const handleJobCompletion = (completedUrl: string, id: string) => {
    stopPolling();
    if (!isMountedRef.current) return;

    setVideoUrl(completedUrl);
    setStatus('completed');
    setErrorMessage(null);

    // Save video_job_id and video_url back into message meta
    onMetaUpdate?.({
      video_job_id: id,
      video_url: completedUrl,
    });
  };

  const startPolling = (targetJobId: string) => {
    stopPolling();
    pollStartRef.current = Date.now();

    pollIntervalRef.current = setInterval(async () => {
      if (!isMountedRef.current) {
        stopPolling();
        return;
      }

      // Stop after 30 minutes
      const elapsedMs = Date.now() - pollStartRef.current;
      if (elapsedMs > 30 * 60 * 1000) {
        stopPolling();
        setStatus('failed');
        setErrorMessage('Video generation timed out after 30 minutes. Please retry.');
        return;
      }

      try {
        const job = await getVideoJob(targetJobId);
        if (!isMountedRef.current) return;

        if (job.status === 'completed') {
          let finalUrl = job.video_url;
          if (!finalUrl) {
            try {
              const res = await getVideoResult(targetJobId);
              finalUrl = res.video_url;
            } catch {
              // Ignore fallback error
            }
          }
          if (finalUrl) {
            handleJobCompletion(finalUrl, targetJobId);
          } else {
            stopPolling();
            setStatus('failed');
            setErrorMessage('Video artifact could not be retrieved.');
          }
        } else if (job.status === 'failed') {
          stopPolling();
          setStatus('failed');
          setErrorMessage(job.error || 'Video rendering failed.');
        } else if (job.status === 'queued') {
          setStatus('queued');
          setQueuePosition(job.queue_position ?? null);
          setStage(job.stage || 'In queue');
        } else if (job.status === 'running') {
          setStatus('running');
          setStage(job.stage || 'Rendering frames');
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        // Don't stop immediately on intermittent 503 during polling, but show notification
        if (err instanceof ApiError && err.status === 503) {
          setStage('Waiting for server capacity...');
        } else {
          stopPolling();
          setStatus('failed');
          setErrorMessage(getFriendlyErrorMessage(err));
        }
      }
    }, 5000);
  };

  const handleStartGeneration = async () => {
    setErrorMessage(null);
    setStatus('queued');
    setStage('Submitting generation job...');

    try {
      const job = await createVideoJob(videoRequest);
      setJobId(job.id);

      if (job.status === 'completed' && job.video_url) {
        handleJobCompletion(job.video_url, job.id);
        return;
      }

      if (job.status === 'queued') {
        setStatus('queued');
        setQueuePosition(job.queue_position ?? null);
      } else if (job.status === 'running') {
        setStatus('running');
        setStage(job.stage || 'Rendering frames');
      }

      startPolling(job.id);
    } catch (err) {
      stopPolling();
      setStatus('failed');
      setErrorMessage(getFriendlyErrorMessage(err));
    }
  };

  const handleRetry = async () => {
    if (!jobId) {
      handleStartGeneration();
      return;
    }

    setErrorMessage(null);
    setStatus('queued');
    setStage('Retrying video generation...');

    try {
      const job = await retryVideoJob(jobId);
      if (job.status === 'completed' && job.video_url) {
        handleJobCompletion(job.video_url, job.id);
        return;
      }
      startPolling(job.id);
    } catch (err) {
      stopPolling();
      setStatus('failed');
      setErrorMessage(getFriendlyErrorMessage(err));
    }
  };

  // 1. Completed State: Render Inline HTML5 Video
  if (status === 'completed' && videoUrl) {
    return (
      <div className="w-full my-2.5 rounded-[20px] bg-[#121217] border border-black/[0.08] p-3 shadow-md">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.08] px-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-white">
            <Film className="w-4 h-4 text-[#3CC8FF]" />
            <span>AI Algorithmic Animation</span>
          </div>
          <span className="text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
            Ready
          </span>
        </div>

        <video
          controls
          autoPlay={false}
          playsInline
          src={videoUrl}
          className="w-full rounded-[14px] aspect-video bg-black shadow-inner"
        >
          Your browser does not support the video tag.
        </video>
      </div>
    );
  }

  // 2. Queued or Running State: Animated Progress Indicator
  if (status === 'queued' || status === 'running') {
    return (
      <div className="w-full my-2 rounded-[16px] bg-[#FAFAFB] border border-[#6C5CFF]/20 p-3.5 flex items-center justify-between shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#6C5CFF]/10 flex items-center justify-center text-[#6C5CFF] shrink-0">
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-[#111113]">
              {status === 'queued'
                ? `Queued for video rendering${queuePosition !== null ? ` (Position #${queuePosition})` : ''}`
                : 'Generating Algorithm Video'}
            </span>
            <span className="text-[11px] text-[#8A8A90] font-mono mt-0.5">
              {stage || (status === 'queued' ? 'Waiting in line...' : 'Processing video frames...')}
            </span>
          </div>
        </div>

        <span className="text-[10px] uppercase font-mono tracking-wider font-semibold text-[#6C5CFF] bg-[#6C5CFF]/10 px-2.5 py-1 rounded-full animate-pulse">
          polling
        </span>
      </div>
    );
  }

  // 3. Failed State: Friendly Error Message + Retry Button
  if (status === 'failed') {
    return (
      <div className="w-full my-2 rounded-[16px] bg-[#FEF2F2] border border-[#FCA5A5]/40 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-[#D9485F] shrink-0 mt-0.5" />
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-[#991B1B]">Video Generation Failed</span>
            <span className="text-xs text-[#7F1D1D] mt-0.5">{errorMessage || 'Could not complete video rendering.'}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleRetry}
          className="self-end sm:self-center px-3.5 py-1.5 rounded-[10px] bg-white border border-[#FCA5A5] hover:bg-[#FEE2E2] text-[#991B1B] text-xs font-medium flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  // 4. Idle State: Clean Action Button
  return (
    <div className="w-full my-2">
      <button
        type="button"
        onClick={handleStartGeneration}
        data-cursor="button"
        className="relative group px-4 py-2.5 rounded-[14px] bg-[#111113] hover:bg-[#222226] text-white text-xs font-semibold flex items-center gap-2.5 transition-all duration-200 shadow-2xs hover:shadow-xs hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
      >
        <div className="w-5 h-5 rounded-md bg-white/10 flex items-center justify-center text-[#A5F3FC] group-hover:scale-110 transition-transform">
          <Play className="w-3 h-3 fill-current ml-0.5" />
        </div>
        <span>Watch Video Explanation</span>
        <Sparkles className="w-3.5 h-3.5 text-[#3CC8FF] ml-0.5 opacity-80" />
      </button>
    </div>
  );
};
