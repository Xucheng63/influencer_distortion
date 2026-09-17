import { test, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import { DistortionResults } from "@/components/distortion/distortion-results";

const messages = {
  tools: {
    distortion: {
      indexLabel: "Distortion Index",
      dim_inflate: "Inflation",
      dim_anxiety: "Anxiety",
      dim_novelty: "Novelty bias",
      dim_loaded_language: "Loaded language",
      dim_temporal: "Temporal pressure",
      severityLow: "Low distortion signal",
      severityModerate: "Moderate distortion signal",
      severityHigh: "High distortion signal",
      confidenceLabel: "Confidence:",
    },
  },
} as AbstractIntlMessages;

const mockResult = {
  account: { handle: "h", display_name: "H", platform: "bluesky" as const },
  profile: {
    distortion_index: 72,
    total_posts_analyzed: 1,
    significance_inflation_rate: 0.5,
    anxiety_manufacturing_rate: 0,
    novelty_claim_rate: 0,
    loaded_language_rate: 0,
    temporal_distortion_rate: 0,
  },
  posts: [
    {
      content: "changes everything",
      distortion_types: ["inflate"],
      confidence: 0.9,
      classification_method: "rules_v2",
      trigger_signals: [],
      posted_at: "2024-01-01T00:00:00Z",
    },
  ],
};

function renderWithIntl(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      {ui}
    </NextIntlClientProvider>
  );
}

test("shows the distortion index number", () => {
  renderWithIntl(<DistortionResults result={mockResult} />);
  expect(screen.getByText("72")).toBeInTheDocument();
});

test("shows a dimension badge for inflate (rendered as i18n label 'Inflation')", () => {
  renderWithIntl(<DistortionResults result={mockResult} />);
  // dim_inflate → "Inflation" via i18n
  expect(screen.getByText(/inflation/i)).toBeInTheDocument();
});

test("shows the post content", () => {
  renderWithIntl(<DistortionResults result={mockResult} />);
  expect(screen.getByText(/changes everything/i)).toBeInTheDocument();
});
