# InboxCast Episode-Level Script Cohesion Enhancement Plan

**Date:** 2025-09-05  
**Status:** Implementation Ready  
**Goal:** Transform segmented newsletter summaries into cohesive podcast episodes with natural narrative flow

## Problem Statement

Current InboxCast script generation processes each newsletter item independently, resulting in:
- Choppy transitions between segments
- No episode-level introduction or conclusion  
- Missing thematic connections between related items
- Audio that sounds like disconnected summaries rather than a cohesive podcast

## Solution Architecture

### Two-Stage Script Generation Approach

**Stage 1: Individual Item Processing (Existing)**
- Keep current `OpenAISummarizer` for legal compliance and policy checks
- Maintain 30-word quote limits per item
- Preserve segmented processing for error isolation

**Stage 2: Episode-Level Script Synthesis (New)**
- New `EpisodeScriptEngine` synthesizes individual summaries into cohesive narrative
- Generate episode introduction, transitions, and conclusion
- Create thematic groupings and natural bridges between segments

## Implementation Plan

### Phase 1: Architecture Design
- [x] Analyze current script generation pipeline (`openai_engine.py`, `cli/main.py`)
- [x] Design `EpisodeScriptEngine` class interface
- [x] Define episode script structure and output format

### Phase 2: Episode Script Engine Implementation
- [x] Create `inboxcast/script/episode_engine.py`
- [x] Implement episode-level OpenAI prompts
- [x] Add thematic grouping and content relationship analysis
- [x] Build natural transition generation logic

### Phase 3: CLI Pipeline Integration  
- [x] Modify `cli/main.py` to use two-stage approach
- [x] Update script output format for episode structure
- [x] Ensure compatibility with existing TTS/audio pipeline

### Phase 4: Testing & Validation
- [x] Test episode cohesion with sample newsletter data
- [x] Validate listening experience improvements
- [x] Performance testing with existing audio processing

## Technical Details

### Current Pipeline (cli/main.py:117-127)
```python
# Current: Simple script file generation
script_path = output_path / "episode_script.txt"
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(f"InboxCast Episode Script - {datetime.now().strftime('%Y-%m-%d')}\n")
    f.write("=" * 60 + "\n\n")
    for i, item in enumerate(planned_items, 1):
        f.write(f"{i}. Title: {item.title}\n")
        f.write(f"   Words: {item.word_count}\n")
        f.write(f"   Script: {item.script}\n\n")
```

### Proposed Enhancement
```python
# Enhanced: Episode-level script synthesis
episode_engine = EpisodeScriptEngine()
episode_script = episode_engine.synthesize_episode(planned_items, target_minutes)

# Generate structured episode script with:
# - Episode introduction
# - Thematic segments with transitions
# - Natural bridges between items  
# - Episode conclusion
```

### Episode Script Structure
```
InboxCast Episode - YYYY-MM-DD (X minutes)
====================================================

INTRODUCTION: [Generated episode opening]

SEGMENT 1: [Thematic group title]
- Transition: [Natural bridge to first item]
- Item 1: [Enhanced script with context]
- Item 2: [Related item with transition]

SEGMENT 2: [Next thematic group]  
- Transition: [Bridge from previous segment]
- Item 3: [Enhanced script]

CONCLUSION: [Episode wrap-up and key takeaways]
```

## Benefits

### Listening Experience
- Natural podcast-style episode flow
- Professional introductions and conclusions
- Smooth transitions between topics
- Thematic organization of content

### Technical Benefits Preserved
- Maintains segmented TTS processing for cost efficiency
- Preserves legal compliance (30-word quotes per item)
- Keeps modular architecture for maintainability  
- Enables granular error handling per item

### Implementation Advantages
- Non-breaking changes to existing audio pipeline
- Backward compatibility with current TTS providers
- Extensible design for future enhancements

## Success Metrics

1. **Narrative Coherence**: Episodes sound like cohesive podcasts vs. segmented summaries
2. **Transition Quality**: Natural bridges between items based on content themes
3. **Episode Structure**: Clear intro/conclusion with thematic organization
4. **Technical Compatibility**: Seamless integration with existing TTS/audio pipeline
5. **Performance**: No significant impact on processing time or costs

## Next Steps

1. Begin Phase 1 implementation with `EpisodeScriptEngine` design
2. Create prototype with sample newsletter data
3. Iterate on episode prompts and structure
4. Integration testing with full pipeline

---

*This enhancement focuses purely on script-level improvements while maintaining all existing technical architecture and audio processing capabilities.*