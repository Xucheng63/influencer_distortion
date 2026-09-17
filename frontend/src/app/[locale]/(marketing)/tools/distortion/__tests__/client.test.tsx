import { test, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import { DistortionClient } from "../client";

const messages = {
  tools: {
    distortion: {
      heroTitle: "Influencer Distortion System",
      heroSubtitle: "Analyze influencer posts.",
      platformLabel: "Platform",
      platform_youtube: "YouTube",
      platform_twitter: "Twitter / X",
      platform_weibo: "Weibo",
      platform_bluesky: "Bluesky",
      platform_reddit: "Reddit",
      handleLabel: "Influencer handle or channel ID",
      handlePlaceholder: "@username or channel URL",
      analyze: "Analyze",
      analyzing: "Analyzing…",
      progress: "Fetching and scoring posts…",
      rateLimited: "Rate limited — please wait a moment and try again.",
      error: "Analysis failed. Check the handle and try again.",
      devSectionTitle: "Developer: update cookies",
      devPasswordLabel: "Developer password",
      devPasswordNote:
        "This is for developers only to update expired cookies. Regular users can ignore this field and just enter the account handle directly.",
      devUnlock: "Unlock",
      devUnlocking: "Unlocking…",
      devPasswordError: "Incorrect developer password.",
      devSaveCookies: "Save cookies",
      devSaving: "Saving…",
      devCookieSaved: "Cookies updated. New analyses will use them.",
      devCookieError: "Could not update cookies. Check the values and try again.",
    },
  },
} as AbstractIntlMessages;

function TestProviders({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={messages}>
        {children}
      </NextIntlClientProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  // Reset any DOM state between tests handled by testing-library cleanup.
});

test("twitter shows the handle input immediately (no cookie gate)", async () => {
  render(<DistortionClient />, { wrapper: TestProviders });
  await userEvent.selectOptions(screen.getByLabelText(/platform/i), "twitter");
  // Cookies now come from the backend env — no cookie fields or Test Connection.
  expect(screen.getByLabelText(/handle|username/i)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /test connection/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/auth_token/i)).not.toBeInTheDocument();
});

test("bluesky shows the handle input immediately", async () => {
  render(<DistortionClient />, { wrapper: TestProviders });
  await userEvent.selectOptions(screen.getByLabelText(/platform/i), "bluesky");
  expect(screen.getByLabelText(/handle|username/i)).toBeInTheDocument();
});

test("twitter shows the developer password gate with the note, cookie fields hidden", async () => {
  render(<DistortionClient />, { wrapper: TestProviders });
  await userEvent.selectOptions(screen.getByLabelText(/platform/i), "twitter");
  expect(screen.getByLabelText(/developer password/i)).toBeInTheDocument();
  expect(
    screen.getByText(/for developers only to update expired cookies/i),
  ).toBeInTheDocument();
  // Cookie inputs stay hidden until the password is verified.
  expect(screen.queryByLabelText(/auth_token/i)).not.toBeInTheDocument();
});

test("weibo also shows the developer password gate", async () => {
  render(<DistortionClient />, { wrapper: TestProviders });
  await userEvent.selectOptions(screen.getByLabelText(/platform/i), "weibo");
  expect(screen.getByLabelText(/developer password/i)).toBeInTheDocument();
});

test("keyless platforms show no developer password gate", async () => {
  render(<DistortionClient />, { wrapper: TestProviders });
  for (const p of ["youtube", "reddit", "bluesky"]) {
    await userEvent.selectOptions(screen.getByLabelText(/platform/i), p);
    expect(
      screen.queryByLabelText(/developer password/i),
    ).not.toBeInTheDocument();
  }
});
