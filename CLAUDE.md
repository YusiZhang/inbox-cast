# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**InboxCast** - AI newsletter summarization to private audio podcasts. Converts user-forwarded AI newsletters into commute-sized audio episodes via semantic deduplication, transformative summarization, and private RSS delivery.

**Target Users:** Busy software engineers/PMs tracking AI developments  
**Core Value:** Turn newsletter firehose into hands-free, commute-length audio with legal-first architecture

## Key Architecture (Planned)

**Stack:** Next.js (web) + FastAPI (API) + Supabase (DB/Storage)  
**Pipeline:** Email forwarding → Parse → Allowlist fetch (Firecrawl) → Dedupe → Summarize (OpenAI) → TTS (MiniMax) → Private RSS

**Legal-First Design:**
- User-provided content only (no crawling)
- Allowlist-only public fetching
- Skip paywalls completely
- 30-word max quotes per item
- Private tokenized RSS feeds

## Development Commands
*To be added when project is initialized*

## Reference Documents
- Full PRD: `.claude/prompts/PRD-MVP.md`
- Implementation order in PRD section 11