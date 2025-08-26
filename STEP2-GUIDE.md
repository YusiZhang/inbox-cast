# InboxCast Step 2: Smart Content Processing

## Overview

Step 2 implements intelligent content processing with OpenAI summarization, semantic deduplication, and robust legal compliance guards. This upgrade transforms the basic Step 1 pipeline into a production-ready content processing system.

## Key Features

### 🤖 OpenAI-Powered Summarization
- **Model**: GPT-4o-mini for cost-effective, high-quality summaries
- **Legal Compliance**: Built-in quote detection and transformative content requirements
- **Structured Output**: JSON-formatted responses with content analysis
- **Policy Guards**: Automatic filtering of paywalled or problematic content

### 🔍 Semantic Deduplication  
- **Technology**: Sentence Transformers with cosine similarity matching
- **Model**: `all-MiniLM-L6-v2` for efficient semantic understanding
- **Caching**: Persistent embedding cache to reduce compute costs
- **Threshold**: Configurable similarity detection (default: 85%)

### 🧹 Intelligent Content Cleaning
- **Readability Algorithm**: Extracts main article content from HTML
- **Full-Text Fetching**: Retrieves complete articles when RSS content is truncated
- **Paywall Detection**: Identifies and skips subscription-gated content
- **HTML Processing**: BeautifulSoup + lxml for robust content extraction

### ⚖️ Legal Compliance Framework
- **Quote Limits**: Enforces maximum 30-word direct quotes
- **Transformative Analysis**: Requires commentary and insights, not just copying  
- **Policy Violations**: Comprehensive checking with detailed reporting
- **Safe Defaults**: Strict compliance mode available for maximum legal safety

## Configuration

### Basic Step 2 Setup

```yaml
# config-step2.yaml
processing:
  # Use OpenAI summarization
  summarizer: "openai"
  openai_model: "gpt-4o-mini"
  max_words: 50
  
  # Use semantic deduplication
  deduplicator: "semantic"
  similarity_threshold: 0.85
  
  # Enable content cleaning
  use_readability: true
  fetch_full_content: true
  
  # Legal compliance
  max_quote_words: 30
  strict_policy_mode: false
```

### Environment Setup

```bash
# Required for OpenAI integration
export OPENAI_API_KEY="your-api-key-here"

# Install new dependencies
uv sync
```

## Usage Examples

### Run Full Step 2 Pipeline

```bash
# Use Step 2 configuration
inboxcast run -c config-step2.yaml

# Monitor semantic deduplication in action
inboxcast plan -c config-step2.yaml
```

### Component-by-Component Testing

```bash
# Test with just semantic deduplication (no OpenAI)
processing:
  summarizer: "simple"      # Use basic summarizer
  deduplicator: "semantic"  # Use smart deduplication

# Test with just OpenAI (no semantic deduplication)  
processing:
  summarizer: "openai"     # Use smart summarization
  deduplicator: "simple"   # Use basic deduplication
```

## Performance Characteristics

### Step 1 vs Step 2 Comparison

| Feature | Step 1 | Step 2 |
|---------|---------|---------|
| **Deduplication** | URL normalization | Semantic similarity |
| **Summarization** | Text truncation | AI-generated insights |
| **Content Cleaning** | Basic HTML stripping | Readability extraction |
| **Legal Compliance** | Basic paywall detection | Comprehensive policy framework |
| **Cost per Episode** | ~$0.00 | ~$0.10-0.30 |
| **Processing Time** | ~5 seconds | ~30-60 seconds |
| **Content Quality** | Basic | Production-ready |

### Resource Requirements

- **Memory**: 2-4GB additional (for embedding models)
- **Disk**: 500MB-1GB (model downloads + embedding cache)
- **Network**: OpenAI API calls (~1-5KB per article)
- **CPU**: Moderate increase for embedding computation

## Troubleshooting

### Common Issues

#### OpenAI API Errors
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test with simple fallback
processing:
  summarizer: "simple"  # Falls back automatically on error
```

#### Embedding Model Download
```python
# Models download automatically on first run
# Progress: Loading sentence transformer model: all-MiniLM-L6-v2
# Cache: ~/.cache/huggingface/transformers/
```

#### Memory Issues
```yaml
# Use smaller embedding model
processing:
  embedding_model: "all-MiniLM-L6-v2"  # 23MB model
  # vs "all-mpnet-base-v2"              # 109MB model
```

### Debug Mode

```yaml
processing:
  strict_policy_mode: true  # Show all policy warnings as errors
```

## Legal Compliance Details

### Quote Policy
- **Maximum**: 30 words per direct quote
- **Detection**: Automatic scanning for quoted text patterns
- **Enforcement**: Items with violations are automatically skipped

### Transformative Content Requirements
- **Analysis Required**: Scripts must include commentary/insights
- **Derivative Language**: Flagged phrases like "according to the article"
- **Compliance Scoring**: Automatic evaluation of transformative elements

### Paywall Handling  
- **Detection**: Multi-level indicators (strong/moderate/weak)
- **Action**: Automatic skipping of paywalled content
- **Logging**: Clear reporting of skip reasons

## Migration from Step 1

### Backward Compatibility
- Step 1 configs work without modification (uses defaults)
- Gradual migration possible (mix Step 1 and Step 2 components)
- No breaking changes to existing workflows

### Recommended Migration Path
1. **Test with defaults**: Run existing config with Step 2 code
2. **Add semantic deduplication**: Enable `deduplicator: "semantic"`
3. **Enable content cleaning**: Set `use_readability: true`
4. **Activate OpenAI**: Set `summarizer: "openai"` with API key
5. **Tune parameters**: Adjust thresholds and limits for your use case

## Cost Management

### OpenAI Usage Optimization
```yaml
processing:
  openai_model: "gpt-4o-mini"      # Most cost-effective
  max_words: 50                    # Shorter = cheaper
  openai_temperature: 0.3          # Deterministic outputs
```

### Embedding Cache Efficiency  
```yaml
processing:
  embedding_cache_days: 7          # Keep embeddings for a week
  # Cache location: out/cache/embedding_cache.pkl
```

## Next Steps

Step 2 provides the intelligent content processing foundation for Step 3's production audio pipeline and Step 4's quality assurance framework. The legal compliance and content quality improvements enable reliable automated newsletter processing at scale.