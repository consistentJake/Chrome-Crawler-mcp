# Multi-Provider Support

The Interview Extractor now supports both **Anthropic Claude** and **OpenAI** models.

## Configuration

### Using Anthropic Claude

```yaml
# config.yaml
api:
  provider: "anthropic"
  api_key: "sk-ant-..."
  model: "claude-sonnet-4-20250514"
```

**Supported Models:**
- `claude-sonnet-4-20250514` (recommended)
- `claude-opus-4-20250514` (higher quality)
- `claude-3-5-haiku-20241022` (faster, cheaper)

### Using OpenAI

```yaml
# openAIconfig.yaml
api:
  provider: "openai"
  api_key: "sk-..."
  model: "gpt-4o"
```

**Supported Models:**
- `gpt-4o` (recommended)
- `gpt-4o-mini` (faster, cheaper)
- `gpt-4-turbo`
- `o1-preview` (advanced reasoning)
- `o1-mini` (faster reasoning)

**Note:** o1 models don't support system messages or temperature parameters.

## Usage

### With Anthropic (default config.yaml)

```bash
python main.py input.json
```

### With OpenAI

```bash
python main.py input.json --config openAIconfig.yaml
```

## API Key Priority

1. Command line: `--api-key`
2. Config file: `api.api_key`
3. Environment variable:
   - `ANTHROPIC_API_KEY` (for Anthropic)
   - `OPENAI_API_KEY` (for OpenAI)

## Dependencies

```bash
# For Anthropic
pip install anthropic

# For OpenAI
pip install openai

# Both
pip install anthropic openai pyyaml
```

## Model Comparison

| Provider | Model | Speed | Quality | Cost | Chinese Support |
|----------|-------|-------|---------|------|-----------------|
| Anthropic | claude-sonnet-4 | Fast | Excellent | $$ | Excellent |
| Anthropic | claude-opus-4 | Slow | Best | $$$ | Excellent |
| OpenAI | gpt-4o | Fast | Excellent | $$ | Excellent |
| OpenAI | gpt-4o-mini | Very Fast | Good | $ | Good |
| OpenAI | o1-preview | Slow | Best (reasoning) | $$$$ | Excellent |

All models support Chinese prompts and can extract Chinese content effectively.
