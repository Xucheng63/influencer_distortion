"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { Badge } from "@/components/ui";
import { Progress } from "@/components/ui";
import type { DistortionProfileResult } from "@/types/distortion";

// Dimension key mapping: backend value → i18n key suffix
const DIM_KEY_MAP: Record<string, string> = {
  inflate: "dim_inflate",
  anxiety: "dim_anxiety",
  novelty: "dim_novelty",
  loaded_language: "dim_loaded_language",
  temporal: "dim_temporal",
};

function getToneColor(index: number): string {
  if (index < 34) return "var(--color-tone-good)";
  if (index <= 66) return "var(--color-tone-warn)";
  return "var(--color-tone-bad)";
}

function getToneBarClass(index: number): string {
  if (index < 34) return "[&>div]:bg-green-500";
  if (index <= 66) return "[&>div]:bg-amber-500";
  return "[&>div]:bg-red-500";
}

export function DistortionResults({ result }: { result: DistortionProfileResult }) {
  const t = useTranslations("tools.distortion");
  const { distortion_index } = result.profile;
  const toneColor = getToneColor(distortion_index);
  const toneBarClass = getToneBarClass(distortion_index);

  return (
    <div className="space-y-6">
      {/* Overall distortion index gauge */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground tracking-wide uppercase">
            {t("indexLabel")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            {/* Circular gauge */}
            <div className="relative inline-flex h-24 w-24 shrink-0 items-center justify-center">
              <svg
                className="h-full w-full -rotate-90"
                viewBox="0 0 100 100"
                aria-hidden="true"
              >
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  strokeWidth="8"
                  className="stroke-secondary"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke={toneColor}
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={String(2 * Math.PI * 42)}
                  strokeDashoffset={String(2 * Math.PI * 42 * (1 - distortion_index / 100))}
                  className="transition-all"
                />
              </svg>
              <div
                role="img"
                aria-label={`${t("indexLabel")}: ${distortion_index} out of 100`}
                className="absolute flex flex-col items-center"
              >
                <span
                  className="text-2xl font-bold tabular-nums"
                  style={{ color: toneColor }}
                >
                  {distortion_index}
                </span>
                <span className="text-[10px] font-medium tracking-wide uppercase text-muted-foreground">
                  / 100
                </span>
              </div>
            </div>

            {/* Linear progress bar */}
            <div className="flex-1 space-y-2">
              <Progress
                value={distortion_index}
                className={toneBarClass}
                aria-label={`${t("indexLabel")}: ${distortion_index}%`}
              />
              <p className="text-xs text-muted-foreground">
                {distortion_index < 34
                  ? t("severityLow")
                  : distortion_index <= 66
                    ? t("severityModerate")
                    : t("severityHigh")}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-post cards */}
      {result.posts.length > 0 && (
        <div className="space-y-3">
          {result.posts.map((post, idx) => (
            <Card key={post.posted_at + ":" + idx}>
              <CardContent className="pt-4 space-y-3">
                {/* Post content (truncated) */}
                <p className="text-sm text-foreground line-clamp-3">{post.content}</p>

                {/* Dimension badges */}
                {post.distortion_types.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {post.distortion_types.map((dim) => {
                      const key = DIM_KEY_MAP[dim];
                      const label = key ? t(key as keyof typeof DIM_KEY_MAP) : dim;
                      return (
                        <Badge
                          key={dim}
                          variant="secondary"
                          className="text-xs"
                        >
                          {label}
                        </Badge>
                      );
                    })}
                  </div>
                )}

                {/* Metadata row */}
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>
                    {t("confidenceLabel")}{" "}
                    <span className="font-medium tabular-nums">
                      {Math.round(post.confidence * 100)}%
                    </span>
                  </span>
                  <span className="text-border">·</span>
                  <span className="font-mono">{post.classification_method}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
