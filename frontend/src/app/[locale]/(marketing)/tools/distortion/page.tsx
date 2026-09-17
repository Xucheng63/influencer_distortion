import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { LandingNav } from "@/components/layout/landing-nav";
import { Footer } from "@/components/layout/footer";
import { DistortionClient } from "./client";
import { SITE_NAME, SITE_URL } from "@/lib/entities";
import { PAGE_BLOOM_STYLE } from "@/lib/page-bloom";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("tools");
  const title = t("distortion.metaTitle");
  const description = t("distortion.metaDescription");

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${SITE_URL}/tools/distortion`,
      siteName: SITE_NAME,
      images: [{ url: `${SITE_URL}/og-default.png`, width: 1200, height: 630 }],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`${SITE_URL}/og-default.png`],
    },
    alternates: { canonical: `${SITE_URL}/tools/distortion` },
  };
}

export default async function DistortionPage() {
  const t = await getTranslations("landing");

  return (
    <div className="bg-background min-h-screen" style={PAGE_BLOOM_STYLE}>
      <LandingNav
        signInLabel={t("signIn")}
        getStartedLabel={t("getStarted")}
        dashboardLabel={t("dashboardLabel")}
      />
      <main>
        <DistortionClient />
      </main>
      <Footer />
    </div>
  );
}
