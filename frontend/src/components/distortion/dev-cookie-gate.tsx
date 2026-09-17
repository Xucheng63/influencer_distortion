"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Input, Label } from "@/components/ui";
import {
  useDistortionVerifyDevPassword,
  useDistortionUpdateCookies,
} from "@/hooks/use-distortion";

/**
 * Developer-only gate for refreshing Twitter/Weibo session cookies without a
 * redeploy. Regular users ignore this and use the handle input directly.
 *
 * Flow: enter the developer password → Unlock (server-verified, the password
 * never gates client-side) → reveal the platform's cookie inputs → Save, which
 * stores the cookies in the backend (Redis) for subsequent scrapes.
 */

const COOKIE_FIELDS: Record<"twitter" | "weibo", { key: string; label: string }[]> = {
  twitter: [
    { key: "auth_token", label: "auth_token" },
    { key: "ct0", label: "ct0" },
  ],
  weibo: [
    { key: "sub", label: "SUB" },
    { key: "subp", label: "SUBP" },
  ],
};

export function DevCookieGate({ platform }: { platform: "twitter" | "weibo" }) {
  const t = useTranslations("tools.distortion");
  const fields = COOKIE_FIELDS[platform];

  const [password, setPassword] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  const verify = useDistortionVerifyDevPassword();
  const update = useDistortionUpdateCookies();

  function handleUnlock() {
    verify.mutate(
      { password },
      { onSuccess: (d) => setUnlocked(!!d.ok) },
    );
  }

  function handleSave() {
    setSaved(false);
    update.mutate(
      { platform, password, cookies: values },
      { onSuccess: () => setSaved(true) },
    );
  }

  const allFilled = fields.every((f) => (values[f.key] ?? "").trim().length > 0);

  return (
    <details className="border-border/60 rounded-lg border bg-muted/30 px-4 py-3">
      <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
        {t("devSectionTitle")}
      </summary>

      <div className="mt-3 space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="distortion-dev-password">{t("devPasswordLabel")}</Label>
          <div className="flex gap-2">
            <Input
              id="distortion-dev-password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setUnlocked(false);
                setSaved(false);
              }}
              autoComplete="off"
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleUnlock}
              disabled={!password.trim() || verify.isPending}
            >
              {verify.isPending ? t("devUnlocking") : t("devUnlock")}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">{t("devPasswordNote")}</p>
          {verify.isError && (
            <p className="text-destructive text-xs">{t("devPasswordError")}</p>
          )}
        </div>

        {unlocked && (
          <div className="space-y-3 border-t border-border/50 pt-3">
            {fields.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label htmlFor={`distortion-cookie-${f.key}`}>{f.label}</Label>
                <Input
                  id={`distortion-cookie-${f.key}`}
                  type="text"
                  value={values[f.key] ?? ""}
                  onChange={(e) =>
                    setValues((v) => ({ ...v, [f.key]: e.target.value }))
                  }
                  autoComplete="off"
                />
              </div>
            ))}
            <Button
              type="button"
              onClick={handleSave}
              disabled={!allFilled || update.isPending}
            >
              {update.isPending ? t("devSaving") : t("devSaveCookies")}
            </Button>
            {saved && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400">
                {t("devCookieSaved")}
              </p>
            )}
            {update.isError && (
              <p className="text-destructive text-xs">{t("devCookieError")}</p>
            )}
          </div>
        )}
      </div>
    </details>
  );
}
