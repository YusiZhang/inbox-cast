# InboxCast Alpha Implementation Plan

## Technical Execution Strategy: Vertical Slice → Iterative Enhancement

### **Step 1: Minimal End-to-End Pipeline**
**Goal:** Get something working end-to-end quickly

- Basic project structure with core contracts/protocols
- Simple RSS parsing (feedparser) 
- Dummy deduplication (by URL)
- Basic summarization (simple truncation)
- Dummy TTS (espeak fallback)
- Audio concatenation 
- Simple RSS output

**Output:** `inboxcast run` produces episode.mp3 + feed.xml

### **Step 2: Smart Content Processing**
**Goal:** Make the content pipeline intelligent

- HTML cleaning with readability extraction
- Embedding-based deduplication using sentence-transformers
- OpenAI summarization with structured JSON output
- Policy guards (quote checker, paywall detection)

**Validation:** Content quality dramatically improves

### **Step 3: Production Audio Pipeline**
**Goal:** Professional audio quality

- MiniMax TTS integration with retry logic
- Professional audio stitching (gaps, fades, normalization)
- FFmpeg loudness normalization to -19 LUFS broadcast standard
- Duration planning with TTS speed calibration

**Validation:** Audio meets broadcast standards

### **Step 4: Quality & Operations**
**Goal:** Production readiness

- Evaluation harness with automated quality checks
- Comprehensive error handling and provider fallbacks
- Configuration management and metrics logging

**Validation:** Passes all acceptance criteria from dogfood.md

## Key Technical Decisions

- **Python ecosystem** (feedparser, sentence-transformers, pydub/ffmpeg)
- **Embeddings**: sentence-transformers for offline deduplication
- **TTS fallback chain**: MiniMax → espeak → skip item
- **Config**: YAML with environment overrides
- **CLI**: Click with subcommands

## Success Criteria (from dogfood.md)

- Daily 07:00 PT episode generation
- ±10% duration accuracy
- Zero quote violations
- <$0.50 per episode cost
- -19 LUFS audio normalization
- Deterministic output with seed control
- Swappable TTS providers