# InboxCast — MVP PRD 

**Owner:** Solo developer (you)
**Date:** 2025‑08‑17
**Status:** Draft v0.1 (founder‑approved)

---

## 1) Vision & Mission

**Vision**
Turn the firehose of fast‑moving industry updates (starting with AI) into daily, hands‑free inspiration—so people keep up, spark new ideas, and make better decisions with less screen time.

**Mission (MVP)**
Start with AI newsletters only. Users auto‑forward the newsletters they already read → InboxCast summarizes, dedupes, and speaks them into a private, ad‑free, tokenized RSS episode sized to the user’s commute and cadence—implemented with a legal‑first architecture (user‑provided inputs, per‑user storage, allowlist‑only public fetching, paywalls skipped).

**Product principles**

* User‑provided only; never crawl generically.
* Transformative summaries; cap verbatim quotes ≤ **30 words** per item.
* Semantic dedupe; one clean item per story; references in show notes only.
* High‑level numbers only (audio‑legible).
* Private by default (tokenized feed; signed media URLs; rotation).
* Minimal onboarding (length + cadence).
* No audio ads (sponsor notes live only in show notes, if ever).

**Differentiators**

* Optimized for **busy software engineers or product managers** tracking AI.
* Legal‑first posture (allowlist public fetching only; skip paywalls).
* Commute‑length control + tone presets; one best‑in‑class voice.
* Clean show notes with sources, references, and explicit *Skipped* reasons.

---

## 2) Target Audience & Use Case

**Primary persona:** Busy Software Engineer or Product Managers (AI/infra/product‑adjacent)
**Habits:** Listens during commute/dog walk/gym; wants 10–20 minutes of high‑signal audio.
**Needs:** One episode matching schedule; no duplicates; minimal filler; legal & private.
**JTBD:**

1. During commute, get **just the AI stories I care about**, sized to my time window.
2. Merge overlaps across newsletters into **one** item.
3. Skip paywalled/teaser items and tell me why in notes.

---

## 3) Scope (MVP)

**In scope**

* AI newsletters only (user‑forwarded emails).
* Email body parsing + allowlist public fetch (Firecrawl) when linked in email.
* Paywalls strictly **skipped**.
* Semantic dedupe across items per episode.
* Adjustable **length** & **cadence**; tone presets in Settings.
* Delivery via **private tokenized RSS**; signed audio URLs.
* Retention: Free **1 day**, Premium **14 days** (raw emails 30 days internal).
* Notifications: **No‑update** email; optional episode‑ready.
* Auth: Google Sign‑In (OIDC only); no Gmail read scopes.

**Out of scope (MVP)**

* Non‑AI domains; mobile app; YouTube/Spotify; multi‑voice gallery/voice cloning; creator licensing deals; generic crawling; Gmail API inbox reads.

**Assumptions**

* Stack: Next.js (web), FastAPI (API), Supabase Postgres + S3/Supabase storage.
* Cost ceiling guidance: TTS+LLM ≤ **\$150/user/month** max with built‑in caps.
* OpenAI or Gemini API for script generation
* MiniMax tts api for audio generation

---

## 4) Inputs & Ingestion

**4.1 Email forwarding**

* Per‑user inbound address (SES/Mailgun/SendGrid inbound → webhook → FastAPI).
* Accept text/html; max \~10 MB.
* Show in UI within ≤60s of arrival.

**4.2 Parsing**

* Sanitize HTML (remove nav/ads/unsubscribe).
* Extract readable article block + metadata (sender, subject, received\_at, canonical links).

**4.3 Allowlisted public fetch (via Firecrawl)**

* Hardcoded allowlist (e.g., `blog.openai.com`, `huggingface.co`, `anthropic.com`, `research.google`, `meta.ai`, `stability.ai`, …).
* Trigger only for links present in email and domain ∈ allowlist.
* Respect robots.txt/ToS; standard UA; 3 retries with backoff; no auth or paywall bypass.
* **200/OK & public:** extract article text/title/author/date.
* **Paywalled/blocked/4xx/5xx:** fallback to email content; mark *\[Skipped: paywalled]* in show notes.

**4.4 Paywall detection**

* Heuristics (overlay markers, subscriber‑only text, HTTP 402/403/451, truncated length).
* Never summarize fetched paywalled pages; skip teaser‑only emails.

**4.5 Semantic dedupe**

* Signals: canonical URL normalization + title sim; **embedding cosine ≥ 0.86–0.92**; entity overlaps.
* Keep one primary (prefer allowlist text); merge others into **references** (notes only).

**4.6 Shared fetch cache (allowlist only)**

* Cache **public extracted text** + metadata, keyed by canonical URL + content hash; TTL 7d; conditional revalidation.
* DMCA‑aware: purge + blocklist on takedown; never cache paywalled content.
* Target ≥70% cache hit for trending stories.

**4.7 Storage & retention**

* Raw EML per user namespace for **30 days** (audit/reprocess).
* Extracted text & provenance recorded; redacted logs.

**4.8 Policy filters**

* Verbatim quote cap **≤30 words** per item (pre‑ and post‑check).
* High‑level numbers only; avoid dense stats in audio.
* Attribution in show notes only.

**4.9 Observability**

* Evented pipeline (received→parsed→(fetched)→deduped→summarized→TTS→published).
* DMCA‑ready logs; per‑item provenance; content hash/blocklist.

**Acceptance**

* Zero summaries of paywalled fetched pages; duplicates <5%; missed merges <5% (tunable).

---

## 5) Processing & Summarization

**5.1 Item build**

* Choose **canonical text** (prefer allowlist public extraction; else email).
* Keep provenance in backend metadata only (not in prompt).

**5.2 Dedupe & merge**

* Embedding cosine ≥ \~0.90 default (user slider Conservative↔Aggressive).
* Keep one item; gather reference links for notes.

**5.3 Ordering**

* Recency → impact heuristics (allowlist > email‑only; key numbers; model/version; well‑known orgs) → user history (later).

**5.4 Duration planning**

* Target minutes × \~165 wpm − overhead → total word budget.
* Allocate per item by significance (min 25 / max 120 words).
* Shrink lowest‑rank items to headline‑only if over budget.

**5.5 Summarizer (OpenAI)**

* Deterministic, factual; **no >30‑word quotes**; high‑level numbers only.
* Prompt returns strict JSON: `{title, script, headline_tag, sources[], notes{has_numbers, paywalled:false}}`.

**5.6 Tone presets**

* Neutral; Impact (“so‑what”); Split (facts + one‑line impact).

**5.7 Fallbacks**

* Summarizer retry ×2; then headline‑only.
* Over‑budget → drop tail items (noted as *Deferred for time cap* in notes).

**Acceptance**

* Episode length within ±10% of target in ≥95% cases; quote‑limit violations: 0.

---

## 6) Output & Delivery

**6.1 TTS (MiniMax)**

* Single best‑in‑class voice; 44.1 kHz mono; MP3 64–96 kbps.
* Resilience: retry ×2; if item fails → drop item and note in *Skipped*.

**6.2 Stitcher**

* Per‑item TTS; join with 150–250 ms gaps; 10 ms micro‑fades; head/tail ≤200 ms.
* Two‑pass EBU R128 loudness normalization: **‑19 LUFS (mono)**; true‑peak ≤ **‑1.0 dBTP**.
* Output: `episode.mp3` + `episode.json` (chapters) for Podcasting 2.0.

**6.3 Storage & URLs**

* S3/Supabase path: `audio/{user_id}/{yyyy}/{mm}/{dd}/episode.mp3`.
* CDN with Range support; **signed URLs**.
* URL expiry aligned to retention (Free \~36h; Premium 15d buffer).

**6.4 Private RSS (tokenized)**

* `/rss/{user_id}/{feed_token}.xml`; iTunes tags; chapter sidecar link.
* **Rotate token** in dashboard → old feed 410/403 within minutes.

**6.5 Retention**

* Free: **1 day** episode access; Premium: **14 days**.
* Raw emails: **30 days** internal.

**6.6 Acceptance**

* ≥99% episodes live by cutoff ±5 min; playback & seek work across major apps.

---

## 7) Onboarding & Settings

**Onboarding (≤60s)**
A) Pick **length** (chips + slider).
B) Pick **cadence** (Daily/Weekdays/Weekly/Weekends) + **cutoff time** (default 07:00).
Then show **Setup checklist**: forwarding address, private feed URL, quick how‑to.

**Settings**

* Playback: target length, cadence, cutoff, tone preset, numbers policy.
* Sources: forwarding address; allowlist (read‑only) + request domain; dedupe slider.
* Delivery: feed URL + **Regenerate token**; retention display; download latest MP3/notes.
* Notifications: No‑update email (on), Episode‑ready (off).
* Account & Data: plan, purge, export; legal links.

**Defaults**: 8 min, Weekdays, 07:00, Neutral tone, high‑level numbers true, dedupe 0.90, No‑update ON.

---

## 8) Notifications & Monetization (Combined)

**Notifications**

* Episode Ready (OFF); No‑Update Day (ON); Delay (>15m late); RSS Token Rotated; DMCA notices; Billing (when enabled).
* Unsubscribe applies to non‑critical emails; security/policy always sent.
* Acceptance: ≥99% No‑Update within 5 minutes; no duplicate Delay.

**Plans & Pricing (hypothesis)**

* Free: \$0; Premium: \$8–\$12/mo.
* **Same quality** for both; differences are **access/retention**.

**Feature matrix**

* Delivery cadence: one schedule for MVP on both.
* Retention: Free 1 day; Premium 14 days.
* Private RSS + rotation: yes on both.
* Allowlisted public fetch: yes on both.
* Download latest MP3/notes: within retention window.
* Cost guardrails: per‑episode LLM tokens cap, TTS seconds cap; transparent *Deferred for time cap* in notes.

**Payments**

* Stripe checkout + portal; upgrade/downgrade effective within ≤5 minutes for retention and feed contents.

---

## 9) Legal & Risk Mitigations (Light)

**Legal posture**

* User‑initiated email forwarding; no inbox reads.
* Allowlist‑only public fetching via third‑party (Firecrawl); respect robots/ToS; **skip paywalls**.
* Transformative summaries; quote cap ≤30 words; attribution in notes only.
* Per‑user storage; private tokenized RSS; no model training on user content.
* Retention: Free 1 day; Premium 14 days; raw emails 30 days.
* *Product guidance, not legal advice; counsel to review ToS/Privacy/DMCA before launch.*

**DMCA‑style takedown (lean)**

1. Intake (public email/form; designated agent).
2. Acknowledge ≤24h; **disable** specific item/episode.
3. Purge audio/notes/extracted text for that item; keep others.
4. Add URL/hash to **blocklist**; purge cache entry.
5. Notify user; counter‑notice path.
6. Repeat‑infringer policy (e.g., 3 strikes per account/domain).
7. Immutable audit log of notice/action/timing.

**Key risks & mitigations**

* Copyright claim → DMCA flow; per‑item disable; cache purge; blocklist.
* Summarizing paywalled content → strict detection & skip; *\[Skipped: paywalled]* note.
* Generic crawling → allowlist‑only public fetch; domain circuit breakers.
* Cross‑user cache optics → cache public text only; DMCA‑purgeable; per‑user summaries.
* Token leakage → rotate; old 410/403; anomaly alerts.
* Cost blowouts → token/seconds caps; word‑budget fitting; tail drop with transparency.
* Missed cutoff → per‑item TTS + stitch; retries; Delay notice.
* Vendor outages → pluggable providers; email‑only fallback; health checks.
* Hallucinations → summarize provided text only; post‑checks; thumbs‑down loop.
* Over/under‑dedupe → threshold slider; monitor complaints; safe default.

**Launch “done” checks**

* ToS/Privacy/DMCA pages live; designated agent listed.
* Takedown manual runbook tested end‑to‑end.
* Robots/ToS enforcement for allowlist domains verified.
* Feed token rotation E2E ≤5 minutes.
* Quote‑limit & paywall‑skip tests pass on sample inboxes.

---

## 10) Open questions

* Allowlist expansion process (cadence, criteria).
* Dedupe default threshold (ship with 0.90?).
* Exact pricing point (\$8 vs \$10 vs \$12) & trial policy.
* Add **second schedule** for Premium post‑MVP?

---

## 11) Implementation checklist (solo‑dev order)

1. Inbound email + storage (EML) per user.
2. HTML extraction + newsletter cleaner.
3. Allowlist Firecrawl client + shared cache + DMCA blocklist.
4. Semantic dedupe (embeddings) + ranking.
5. Summarizer service (prompt + JSON validation + quote limiter).
6. MiniMax TTS wrapper; Stitcher (loudnorm; MP3 export; chapters).
7. Signed URL service + RSS builder + token rotation.
8. Onboarding + Settings + Notifications.
9. Observability + takedown console + runbooks.
10. Stripe payments + plan gating (retention/cadence).
