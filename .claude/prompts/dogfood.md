# InboxCast Alpha Execution Plan - Thin Vertical Slice for Dog Fooding 

## 🎯 Alpha Goal

From 3 allowlisted RSS feeds → dedupe → fit to target minutes → summarize → TTS → stitch → **one MP3** + simple RSS by **07:00 PT** daily.

---

## 📂 Repository & Contracts

**Deliverables**

* Project skeleton with clear module boundaries.
* Stable contracts between pipeline components.

**Structure**

```
inboxcast/
  sources/rss.py
  clean/html_clean.py
  dedupe/simple.py
  plan/duration.py
  summarize/engine.py
  policy/quote_checker.py
  tts/abi.py
  tts/minimax.py
  audio/stitch.py
  audio/loudnorm.py
  output/rss.py
  cli/main.py
  eval/harness.py
  data/fixtures/
  tests/
```

**Contracts**

* `Source.fetch() -> list[RawItem]`
* `Summarizer.summarize(item) -> {title, script, sources[], notes{...}}`
* `TTSProvider.synthesize(text, voice, speed, sample_rate, format) -> bytes`
* `EpisodeBuilder.fit(items, target_minutes) -> planned_items[]`

---

## 📥 Sources & Cleaning

**Scope**

* 3 hardcoded allowlisted RSS feeds.
* Local filesystem storage only.

**Tasks**

* Parse RSS → canonical URL → extract readable block.
* Sanitize HTML: strip nav, ads, unsubscribe footers.
* Fallback: mark as *Skipped: unreadable* if extraction fails.
* Paywall detection: truncated length or “subscriber-only” → mark *Skipped: paywalled*.

**Exit**

* `inboxcast fetch` prints cleaned, deduped items.

---

## 🧹 Dedupe

**Method**

* Embedding cosine similarity ≥0.9 (configurable threshold).
* Fallback: Title similarity + canonical URL normalization.
* Keep first, attach references to notes.

**Exit**

* `inboxcast fetch` output shows unique items only.

---

## ✍️ Summarizer & Policy Guards

**Summarizer**

* Deterministic JSON output:

  ```json
  { "title": "...", "script": "...", "sources": [], "notes": { "paywalled": false, "has_numbers": true } }
  ```
* Temp ≤0.4; paraphrase if needed.

**Policy Guards**

* **Quote checker**: no >30-word direct quotes (exclude code snippets, technical specs).
* **Numbers filter**: compress dense stats into high-level summaries.

**Exit**

* `inboxcast plan --minutes 10` emits validated JSON.

---

## ⏱ Duration Planner

**Method**

* Calibrate actual TTS speed: measure output duration vs. input word count.
* Word budget = minutes × calibrated_wpm (fallback: 165 wpm).
* Allocate per item (min 25 / max 120 words).
* Shrink tail to headline-only or drop (*Deferred for time cap*).

**Exit**

* Planned JSON within ±10% of target duration.

---

## 🗣️ TTS ABI & Provider

**TTS ABI**

```python
class TTSProvider(Protocol):
    def synthesize(text, voice="default", speed=1.0, sample_rate=44100, format="wav") -> bytes:
        ...
```

**Provider**

* `tts/minimax.py`: retries, chunking, backoff.
* `tts/espeak.py`: local fallback provider (prevents vendor lock-in).
* Replaceable with dummy provider.

**Exit**

* `inboxcast synth` produces audio bytes for given script.

---

## 🎧 Stitcher & Loudness

**Stitcher**

* Per-item synthesis.
* Join with 150–250 ms gaps; 10 ms micro-fades; head/tail ≤200 ms.

**Loudness**

* FFmpeg two-pass EBU R128:
  -19 LUFS (mono), true-peak ≤ -1.0 dBTP.
* Export MP3: 64–96 kbps @ 44.1 kHz.

**Exit**

* `inboxcast synth --out out/episode.mp3` yields clean, normalized MP3.

---

## 📡 RSS Output

**Features**

* Generate `feed.xml` pointing to `episode.mp3`.
* Simple chapters JSON: `{start_ms, title}`.
* Serve locally via `python -m http.server` or similar.

**Exit**

* `inboxcast run --minutes 10` produces `episode.mp3`, `feed.xml`, and `episode.json`.

---

## ✅ Eval Harness

**Checks**

* Quote count violations = 0.
* LUFS in \[-19 ±0.5]; TP ≤ -1.0 dBTP.
* Duration error ≤ ±10%.
* No paywalled summaries.
* No duplicates to ear.

**Exit**

* `inboxcast eval` returns success/failure.

---

## ⚙️ Configuration

**Config file: `config.yaml`**

```yaml
rss_feeds:
  - url: "https://blog.openai.com/rss.xml"
    weight: 1.0
  - url: "https://huggingface.co/blog/feed.xml" 
    weight: 1.0
target_duration: 10  # minutes
dedupe_threshold: 0.9
voice_settings:
  provider: "minimax"  # or "espeak"
  speed: 1.0
  voice_id: "default"
```

---

## 📊 Logging & Metrics

* CSV per run:

  ```
  run_id, items_in, items_after_dedupe, items_skipped, words_planned, words_spoken,
  minutes_target, minutes_actual, duration_error_pct, lufs, true_peak_db,
  tts_seconds, prompt_tokens, wall_time_ms, vendor, tts_cost_usd, llm_cost_usd
  ```

---

## 🚨 Error Handling & Resilience

**Strategy**

* **RSS feed failures**: Skip feed, continue with others, log error.
* **TTS failures**: Retry 2x, fallback to espeak, then skip item (*Skipped: TTS failed*).
* **Summarization failures**: Retry 2x, then headline-only.
* **Memory limits**: Process items in batches, streaming where possible.
* **Fatal errors**: Fail fast with clear error messages, preserve partial progress.

---

## 🚦 Acceptance Criteria (Alpha Done)

* End-to-end run produces **episode.mp3** + feed by **07:00 PT** daily.
* Audio: -19 LUFS mono (±0.5), TP ≤ -1.0 dBTP, seekable MP3.
* Duration within ±10% of target.
* 0 quote violations; 0 paywalled summaries.
* Cost tracking shows per-episode expense ≤ $0.50.
* Deterministic output with seed control for testing.
* Swap TTS provider with single constructor change.
* `make eval` passes on fixtures.

