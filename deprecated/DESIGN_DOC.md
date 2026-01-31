# 面经信息提取系统设计文档

## 1. 系统概述

本系统旨在利用 LLM（Claude API）从一亩三分地等论坛的面经帖子中自动提取关键面试信息。系统接收已解析的帖子内容（JSON格式），将其转换为 Markdown 格式，然后通过精心设计的 prompt 调用 Claude API 进行信息提取。

## 2. 数据流架构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌────────────────┐
│  JSON 原始数据   │ ──▶ │  Markdown 转换器  │ ──▶ │  LLM 信息提取器  │ ──▶ │  结构化输出     │
│  (posts数组)    │     │  (分组处理)       │     │  (Claude API)   │     │  (JSON/MD)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └────────────────┘
```

## 3. 核心模块设计

### 3.1 帖子分组器 (PostGrouper)

**目的**：将帖子按可配置数量分组，控制每次 LLM 调用的上下文大小。

```python
class PostGrouper:
    def __init__(self, group_size: int = 3):
        """
        Args:
            group_size: 每组帖子数量，默认3个
                       - 2-3个帖子约 2000-4000 tokens
                       - 保持在 Claude 上下文的合理范围内
        """
        self.group_size = group_size

    def group_posts(self, posts: List[dict]) -> List[List[dict]]:
        """将帖子列表分组"""
        return [posts[i:i+self.group_size]
                for i in range(0, len(posts), self.group_size)]
```

### 3.2 Markdown 转换器 (MarkdownConverter)

**目的**：将 JSON 格式的帖子内容转换为结构化的 Markdown，便于 LLM 理解。

```python
class MarkdownConverter:
    def convert_post(self, post: dict) -> str:
        """将单个帖子转换为 Markdown 格式"""

    def convert_group(self, posts: List[dict]) -> str:
        """将一组帖子转换为 Markdown 格式"""
```

**Markdown 输出格式示例**：

```markdown
# 帖子组 - 面试信息提取

---

## 帖子 1: [面试经验] 开放爱怪兽对战题

**来源URL**: https://www.1point3acres.com/bbs/thread-1156671-1-1.html

### 主楼内容

最近怪兽对战这道题出的蛮多的，看到地里有好几个面经都提到这道题...
[完整内容]

### 楼层回复

**回复 1**: 感谢楼主，请问这个是75min还是60min的题

**回复 2**: 60min，求加米！

**回复 3**: 可以请教一下这题的prompt是什么吗！
  - **子回复**: prompt是面试之前给一个范围...

---

## 帖子 2: [下一个帖子标题]
...
```

### 3.3 LLM 信息提取器 (InterviewInfoExtractor)

**目的**：调用 Claude API，使用精心设计的中文 prompt 提取关键面试信息。

```python
class InterviewInfoExtractor:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_info(self, markdown_content: str) -> dict:
        """从 Markdown 内容中提取面试信息"""
```

## 4. Prompt 设计（核心）

### 4.1 系统 Prompt

```
你是一位专业的面试信息分析师，专门从技术论坛的面经帖子中提取和整理有价值的面试准备信息。

你的任务是：
1. 识别并提取面试题目的核心内容
2. 从回复中补充重要的细节和澄清信息
3. 过滤掉无关的闲聊和噪音
4. 以结构化的方式输出提取的信息

请保持客观、准确，只提取帖子中明确提到的信息，不要添加推测。
```

### 4.2 用户 Prompt 模板

```
请仔细阅读以下来自技术论坛的面经帖子，提取关键的面试信息。

---
{markdown_content}
---

请按以下结构提取信息，以 JSON 格式输出：

```json
{
  "posts": [
    {
      "post_id": "帖子序号",
      "source_url": "原始链接",
      "title": "帖子标题",
      "position_type": "职位类型（SWE/Backend/Fullstack/ML/Research等，如能识别）",
      "interview_stage": "面试阶段（电话面试/店面/Onsite/VO等，如能识别）",
      "interview_info": {
        "题目类型": "Coding/System Design/ML Coding/Behavioral等",
        "时长": "如有提及（如60min/75min）",
        "题目描述": "题目的核心内容描述",
        "具体要求": ["要求1", "要求2", ...],
        "考察重点": ["重点1", "重点2", ...],
        "prompt提示": "如有提及面试前收到的prompt"
      },
      "from_replies": {
        "补充细节": ["从回复中获取的有价值补充信息"],
        "常见问题": ["其他面试者在回复中提出的相关问题"],
        "澄清信息": ["对题目的澄清或额外说明"]
      },
      "metadata": {
        "发帖时间": "如能提取",
        "面试结果": "如有提及（通过/挂了/等待中）",
        "难度评价": "如有提及"
      }
    }
  ],
  "cross_post_insights": {
    "相关题目": ["如果多个帖子提到相同或相关的题目"],
    "面试趋势": "综合多个帖子发现的面试趋势或规律"
  }
}
```

**提取指南**：

1. **主楼内容（mainPageContent）优先**：这是最重要的信息源，通常包含题目描述
2. **回复价值判断**：
   - 高价值：补充题目细节、clarification、follow-up问题、时长信息
   - 低价值：单纯的感谢、求大米、无实质内容的评论
3. **同音字/谐音处理**：论坛用户经常使用同音字或谐音来代替敏感词汇，请注意识别：
   - "开放爱" = "OpenAI"
   - "爱开放" = "OpenAI"
   - "店面" = "电话面试/Phone Screen"
   - 其他类似的谐音词请根据上下文理解
4. **敏感信息处理**：保留技术内容，忽略个人隐私信息
5. **不确定标记**：如果信息不确定，用"[待确认]"标记

请只输出 JSON，不需要其他解释。
```

## 5. 输出数据结构

### 5.1 单帖子提取结果

```python
@dataclass
class InterviewQuestion:
    question_type: str           # Coding/SD/ML/Behavioral
    duration: Optional[str]      # 60min, 75min, etc.
    description: str             # 题目核心描述
    requirements: List[str]      # 具体要求
    key_points: List[str]        # 考察重点
    prompt_hint: Optional[str]   # 面试前收到的prompt

@dataclass
class RepliesInsights:
    supplementary_details: List[str]  # 补充细节
    common_questions: List[str]       # 常见问题
    clarifications: List[str]         # 澄清信息

@dataclass
class PostExtraction:
    post_id: str
    source_url: str
    title: str                   # 帖子标题
    position_type: str           # 职位类型
    interview_stage: str         # 面试阶段
    interview_info: InterviewQuestion
    from_replies: RepliesInsights
    metadata: dict
```

### 5.2 批量处理结果

```python
@dataclass
class BatchExtractionResult:
    posts: List[PostExtraction]
    cross_post_insights: dict
    processing_metadata: dict  # 处理时间、token使用等
```

## 6. 配置参数

```python
class ExtractionConfig:
    # 分组设置
    posts_per_group: int = 3          # 每组帖子数量
    max_tokens_per_call: int = 4096   # 每次API调用的最大输出token

    # API设置
    model: str = "claude-sonnet-4-20250514"  # 使用的模型
    temperature: float = 0.1          # 低温度确保一致性

    # 过滤设置
    min_content_length: int = 50      # 最小内容长度
    skip_keywords: List[str] = [      # 跳过包含这些关键词的帖子
        "新人如何使用",
        "发错了",
        "积分"
    ]

    # 输出设置
    output_format: str = "json"       # json 或 markdown
    save_intermediate: bool = True    # 是否保存中间结果
```

## 7. 使用示例

```python
from interview_extractor import InterviewExtractor, ExtractionConfig

# 配置
config = ExtractionConfig(
    posts_per_group=3,
    model="claude-sonnet-4-20250514"
)

# 初始化
extractor = InterviewExtractor(
    api_key="your-api-key",
    config=config
)

# 从JSON文件加载
with open("combined_results_processed.json", "r") as f:
    data = json.load(f)

# 提取信息
results = extractor.extract_from_posts(data["posts"])

# 保存结果
results.save("extracted_interviews.json")
```

## 8. 非重要信息过滤策略

### 8.1 帖子级别过滤

跳过以下类型的帖子：
- 新人指南帖
- 求积分帖
- 内容过短（< 50字符）
- 明显的测试/发错帖

### 8.2 回复级别过滤

过滤以下类型的回复：
- 纯感谢语（"感谢楼主"、"已加米"等）
- 无实质内容（"顶"、"mark"等）
- 纯表情或符号
- 重复内容

### 8.3 基于 LLM 的智能过滤

在 prompt 中指导 LLM：
- 识别并忽略社交性回复
- 只提取与面试技术内容相关的信息
- 对模糊或可疑信息进行标记

## 9. 实现文件结构

```
PostProcessing/
├── DESIGN_DOC.md              # 本设计文档
├── interview_extractor.py     # 主提取器类
├── markdown_converter.py      # Markdown转换器
├── post_grouper.py            # 帖子分组器
├── prompt_templates.py        # Prompt模板
├── config.py                  # 配置类
├── models.py                  # 数据模型
├── utils.py                   # 工具函数
├── main.py                    # 入口脚本
└── output/                    # 输出目录
    ├── extracted/             # 提取结果
    └── intermediate/          # 中间结果
```

## 10. API 调用优化

### 10.1 成本控制
- 使用 Claude Sonnet 而非 Opus（性价比更高）
- 合理分组减少调用次数
- 缓存已处理结果

### 10.2 质量保证
- 低 temperature (0.1) 确保输出一致性
- 结构化输出便于后续解析
- 错误重试机制

## 11. 后续扩展

1. **多源支持**：支持其他论坛格式
2. **增量处理**：支持增量提取新帖子
3. **题目去重**：识别并合并相同题目的不同描述
4. **难度评估**：基于回复分析题目难度
5. **趋势分析**：分析面试题目的时间趋势
