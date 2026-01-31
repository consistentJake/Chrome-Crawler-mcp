# Interview Information Extraction Tool

自动从一亩三分地等论坛的面经帖子中提取结构化的面试信息。

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic pyyaml
```

### 2. 配置

复制配置模板并填入你的 API key：

```bash
cp config.yaml.template config.yaml
```

编辑 `config.yaml`：

```yaml
api:
  api_key: "your-api-key-here"  # 填入你的 Anthropic API key
  base_url: null                 # 如需使用代理，设置代理 URL
  model: "claude-sonnet-4-20250514"
```

**注意**: `config.yaml` 已被 `.gitignore` 忽略，不会被提交到 git。

### 3. 运行

```bash
# 基本用法
python main.py ../workflows/output/combined_results_processed.json

# 先测试 Markdown 转换（不调用 API）
python main.py input.json --dry-run
```

## base_url 配置

在 `config.yaml` 中设置 `base_url` 来使用 API 代理：

```yaml
api:
  api_key: "your-api-key"
  base_url: "https://your-proxy.com/v1"  # 设置代理 URL
  # 或者
  base_url: null  # 使用官方 API (默认)
```

**常用 base_url**：
- 官方 API：`null` (默认)
- OpenRouter：`https://openrouter.ai/api/v1`
- 自定义代理：`https://your-proxy.com/v1`
- 本地服务器：`http://localhost:8080`

## 文件说明

- `config.yaml.template` - 配置模板（可提交到 git）
- `config.yaml` - 你的配置（含 API key，不提交）
- `.gitignore` - 已配置忽略所有 `config*.yaml` 文件
