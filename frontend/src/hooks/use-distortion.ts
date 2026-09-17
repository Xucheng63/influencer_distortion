"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { DistortionJob, DistortionPlatform } from "@/types";

export function useDistortionAnalyze() {
  return useMutation({
    mutationFn: (v: { platform: DistortionPlatform; handle: string }) =>
      apiClient.post<DistortionJob>("/distortion/analyze", v),
  });
}

/** Developer-only: verify the cookie-refresh password (never leaves the server). */
export function useDistortionVerifyDevPassword() {
  return useMutation({
    mutationFn: (v: { password: string }) =>
      apiClient.post<{ ok: boolean }>("/distortion/cookies/verify", v),
  });
}

/** Developer-only: push refreshed session cookies for a platform. */
export function useDistortionUpdateCookies() {
  return useMutation({
    mutationFn: (v: {
      platform: DistortionPlatform;
      password: string;
      cookies: Record<string, string>;
    }) =>
      apiClient.post<{ ok: boolean; platform: string }>("/distortion/cookies", v),
  });
}

export function useDistortionJob(
  jobId: string | null,
  platform: string,
  handle: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["distortion-job", jobId],
    enabled: enabled && !!jobId,
    refetchInterval: (q) => {
      const s = (q.state.data as DistortionJob | undefined)?.status;
      return s === "done" || s === "error" ? false : 2000;
    },
    queryFn: () =>
      apiClient.get<DistortionJob>(`/distortion/analyze/${jobId}`, {
        params: { platform, handle },
      }),
  });
}
