/**
 * Video generation and polling client using the /video-jobs API.
 */

import { request } from './api.ts';

export interface CreateVideoJobRequest {
  problem_id?: number | null;
  text?: string | null;
  user_code?: string | null;
  programming_language: string;
  title?: string | null;
  explanation_language?: string | null;
  explanation_style?: string | null;
}

export interface VideoJobResponse {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  stage: string;
  video_url?: string | null;
  error?: string | null;
  queue_position?: number | null;
  elapsed_seconds?: number | null;
}

export interface VideoResultResponse {
  video_url: string;
  blob_name: string;
  status: string;
  solution?: any;
}

export async function createVideoJob(videoRequest: CreateVideoJobRequest): Promise<VideoJobResponse> {
  return request<VideoJobResponse>('/video-jobs', {
    method: 'POST',
    body: videoRequest,
  });
}

export async function getVideoJob(id: string): Promise<VideoJobResponse> {
  return request<VideoJobResponse>(`/video-jobs/${id}`);
}

export async function getVideoResult(id: string): Promise<VideoResultResponse> {
  return request<VideoResultResponse>(`/video-jobs/${id}/result`);
}

export async function retryVideoJob(id: string): Promise<VideoJobResponse> {
  return request<VideoJobResponse>(`/video-jobs/${id}/retry`, {
    method: 'POST',
  });
}
