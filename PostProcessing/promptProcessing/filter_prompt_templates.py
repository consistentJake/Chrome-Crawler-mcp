"""
Filter Prompt Templates

Prompts for LLM-based filtering of posts to identify interview-related content.
"""

from typing import List, Dict, Any


FILTER_SYSTEM_PROMPT = """你是一个帖子分类助手。你的任务是快速判断帖子是否与面试相关。

面试相关的帖子包括：
- 面试经验分享（面经）
- 面试题目讨论
- 面试流程介绍
- Offer相关讨论（薪资、谈判、比较）
- 求职经历分享
- 公司招聘流程介绍
- 内推相关帖子

不相关的帖子包括：
- 论坛使用教程
- 积分/米相关讨论
- 签证/移民话题（除非涉及工作签证和面试）
- 租房/生活话题
- 学业讨论（除非涉及实习/校招面试）
- 广告/推广
- 纯灌水帖子

请对每个帖子给出判断，并说明理由。你的回复必须是JSON格式。"""


FILTER_USER_PROMPT_TEMPLATE = """请判断以下帖子是否与面试相关。

{post_summaries}

请以JSON格式回复，格式如下：
```json
{{
  "posts": [
    {{
      "post_index": 0,
      "title": "帖子标题",
      "is_interview_related": true或false,
      "confidence": 0.0到1.0之间的数字,
      "reason": "简短的判断理由"
    }}
  ]
}}
```

注意：
- confidence表示你对判断的确信程度，1.0表示非常确定
- 只返回JSON，不要有其他文字
"""


def get_filter_prompt(post_summaries: List[Dict[str, Any]]) -> str:
    """
    Generate the user prompt for filtering posts.

    Args:
        post_summaries: List of post summaries with keys 'index', 'title', 'content_preview'

    Returns:
        Formatted user prompt string
    """
    # Format post summaries
    formatted_posts = []
    for summary in post_summaries:
        post_text = f"""[帖子 {summary['index']}]
标题: {summary['title']}
内容摘要: {summary['content_preview']}"""
        formatted_posts.append(post_text)

    posts_section = "\n\n---\n\n".join(formatted_posts)

    return FILTER_USER_PROMPT_TEMPLATE.format(post_summaries=posts_section)


def prepare_post_summary(
    post: Dict[str, Any],
    index: int,
    max_content_length: int = 200
) -> Dict[str, Any]:
    """
    Prepare a post summary for filtering.

    Args:
        post: Full post dictionary
        index: Index of the post in the batch
        max_content_length: Maximum length of content preview

    Returns:
        Dictionary with 'index', 'title', 'content_preview'
    """
    # Import here to avoid circular imports
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from shared import get_post_title, get_main_content

    title = get_post_title(post) or "(无标题)"
    content = get_main_content(post) or ""

    # Truncate content for preview
    if len(content) > max_content_length:
        content_preview = content[:max_content_length] + "..."
    else:
        content_preview = content or "(无内容)"

    return {
        "index": index,
        "title": title,
        "content_preview": content_preview
    }
