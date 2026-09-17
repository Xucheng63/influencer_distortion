# Frontend verification screenshots

Captured 2026-09-17 against the live deployment
(<https://blunt-posh-pencil.ngrok-free.dev>) with headless Chromium via
Playwright, viewport 1280px, full-page.

| File | Shows |
|---|---|
| `00-landing.png` | Landing page, five platform cards |
| `01-twitter.png` | Twitter/X `@realDonaldTrump` — index 23, 26 posts, dimension badges |
| `02-weibo.png` | Weibo `环球时报` — index 17, 30 posts |
| `03-bluesky.png` | Bluesky `theverge.com` — index 8, 30 posts |
| `04-devgate-unlocked.png` | Dev cookie gate unlocked, `auth_token` / `ct0` fields revealed |
| `05-devgate-save-fake-cookies.png` | Save rejecting deliberately invalid test cookies |

Notes:

- `05` shows a **red error on purpose.** "Save cookies" validates the pasted
  values against the live platform via `POST /test-connection`, so placeholder
  values are correctly refused. A successful save needs real session cookies.
- Rendering Chinese requires a CJK font on the capture host. The server had
  none, so an earlier run produced tofu boxes; Noto Sans CJK was installed to
  `~/.local/share/fonts` before `02` was retaken.
- Per-post `classification_method` is visible in each card's footer and is the
  quickest way to tell a rules-only verdict from an LLM one.
