"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Input, Label, Skeleton, Progress } from "@/components/ui";
import { DistortionResults } from "@/components/distortion/distortion-results";
import { DevCookieGate } from "@/components/distortion/dev-cookie-gate";
import { useDistortionAnalyze, useDistortionJob } from "@/hooks/use-distortion";
import { ApiError } from "@/lib/api-client";
import type { DistortionPlatform } from "@/types";

const PLATFORMS: DistortionPlatform[] = [
  "youtube",
  "twitter",
  "weibo",
  "bluesky",
  "reddit",
];

export function DistortionClient() {
  const t = useTranslations("tools.distortion");

  // Platform state
  const [platform, setPlatform] = useState<DistortionPlatform>("youtube");

  // Handle and analysis state
  const [handle, setHandle] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [rateLimited, setRateLimited] = useState(false);
  const [analyzeError, setAnalyzeError] = useState(false);

  const analyze = useDistortionAnalyze();

  // Poll job status when we have a jobId and the job is pending/running
  const jobEnabled =
    !!jobId &&
    !!analyze.data &&
    analyze.data.status !== "done" &&
    !analyze.data.cached;

  const job = useDistortionJob(jobId, platform, handle, jobEnabled);

  function handlePlatformChange(newPlatform: DistortionPlatform) {
    setPlatform(newPlatform);
    setHandle("");
    setJobId(null);
    setRateLimited(false);
    setAnalyzeError(false);
    analyze.reset();
  }

  function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    setRateLimited(false);
    setAnalyzeError(false);
    setJobId(null);
    analyze.reset();

    analyze.mutate(
      { platform, handle: handle.trim() },
      {
        onSuccess: (data) => {
          if (!data.cached && data.status !== "done" && data.job_id) {
            setJobId(data.job_id);
          }
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 429) {
            setRateLimited(true);
          } else {
            setAnalyzeError(true);
          }
        },
      },
    );
  }

  // Determine what result to render
  const directResult =
    analyze.data && (analyze.data.cached || analyze.data.status === "done")
      ? analyze.data.result
      : undefined;
  const polledResult =
    job.data?.status === "done" ? job.data.result : undefined;
  const result = directResult ?? polledResult;
  const jobError = job.data?.status === "error" ? job.data.error : undefined;

  const progress = job.data?.progress;
  const isPolling = jobEnabled && job.isFetching;

  return (
    <>
      {/* ══════════════ HERO ══════════════ */}
      <section
        aria-label="Influencer Distortion System"
        className="border-border/30 relative overflow-hidden border-t px-4 pt-36 pb-10 sm:px-6 sm:pt-44 sm:pb-12"
      >
        <div className="relative mx-auto max-w-3xl text-center">
          <h1 className="text-4xl leading-[1.05] font-bold tracking-tight sm:text-5xl lg:text-6xl">
            {t("heroTitle")}
          </h1>
          <p className="text-muted-foreground mx-auto mt-6 max-w-2xl text-base leading-relaxed sm:text-lg">
            {t("heroSubtitle")}
          </p>
        </div>
      </section>

      {/* ══════════════ ANALYZER ══════════════ */}
      <section aria-label="Analyzer" className="px-4 pt-2 pb-16 sm:px-6 sm:pt-3 sm:pb-20">
        <div className="mx-auto max-w-2xl">
          <div className="border-border bg-card rounded-xl border p-6 space-y-6">

            {/* Platform picker — native <select> for jsdom compatibility */}
            <div className="space-y-1.5">
              <Label htmlFor="distortion-platform">{t("platformLabel")}</Label>
              <select
                id="distortion-platform"
                value={platform}
                onChange={(e) => handlePlatformChange(e.target.value as DistortionPlatform)}
                className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>
                    {t(`platform_${p}`)}
                  </option>
                ))}
              </select>
            </div>

            {/* Handle input + analyze — shown for every platform */}
            <form onSubmit={handleAnalyze} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="distortion-handle">{t("handleLabel")}</Label>
                <Input
                  id="distortion-handle"
                  type="text"
                  placeholder={t("handlePlaceholder")}
                  value={handle}
                  onChange={(e) => setHandle(e.target.value)}
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={analyze.isPending || !handle.trim()}
              >
                {analyze.isPending ? t("analyzing") : t("analyze")}
              </Button>
            </form>

            {/* Developer-only cookie refresh for the authenticated platforms. */}
            {(platform === "twitter" || platform === "weibo") && (
              <DevCookieGate platform={platform} />
            )}

            {/* Rate-limit message */}
            {rateLimited && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300">
                {t("rateLimited")}
              </div>
            )}

            {/* Generic error */}
            {analyzeError && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {t("error")}
              </div>
            )}

            {/* Job error from polling */}
            {jobError && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {jobError}
              </div>
            )}

            {/* Loading skeleton (initial analyze pending, not yet polling) */}
            {analyze.isPending && (
              <div className="space-y-4">
                <Skeleton className="h-7 w-40" />
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-4 w-full" />
                  ))}
                </div>
              </div>
            )}

            {/* Progress bar while polling */}
            {jobEnabled && !result && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{t("progress")}</p>
                {progress && progress.total > 0 ? (
                  <Progress value={(progress.done / progress.total) * 100} />
                ) : (
                  <Progress value={undefined} className="animate-pulse" />
                )}
                {isPolling && <Skeleton className="h-4 w-32" />}
              </div>
            )}

            {/* Results */}
            {result && <DistortionResults result={result} />}
          </div>
        </div>
      </section>
    </>
  );
}
