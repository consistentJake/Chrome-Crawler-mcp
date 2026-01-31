#!/usr/bin/env python3
"""
JSON Processor for Forum Scraping Results

This script processes JSON files from forum scraping workflows and extracts:
- base_url from config
- summary information
- For each post: url, page_title, thread_title, and a hierarchical reply structure
  based on quotes (replies quoting other replies are nested as children)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from pprint import pprint


def clean_content_from_quote(content: str, quote: str) -> str:
    """
    Remove the quote part from the beginning of content.
    
    Args:
        content: Full content text
        quote: Quote text to remove
        
    Returns:
        Cleaned content with quote removed
    """
    if not quote:
        return content
    
    if content.startswith(quote):
        return content[len(quote):].strip()
    return content


def extract_reply_data(reply: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract data from a single reply.
    
    Args:
        reply: Reply dictionary
        
    Returns:
        Dictionary with post_id, content, quote, and cleaned_content
    """
    if not isinstance(reply, dict):
        return None
    
    post_id = reply.get('post_id', '')
    content = reply.get('content', '')
    quotes = reply.get('quotes', [])
    
    # Usually only one quote per reply
    quote = quotes[0] if quotes and len(quotes) > 0 else ''
    
    # Clean content by removing quote
    cleaned_content = clean_content_from_quote(content, quote)

    ## need to normalize the quote
    ## example can be 
    """
                "content": "littlehardy 发表于 2025-12-7 08:39\n同问，收到一个75分钟的prompt， 75 Minute Coding Interview - This is a 75 minute coding interview, fo ...\n求问最后面到的是哪题？",
            "timestamp": "",
            "reactions": {},
            "quotes": [
              "littlehardy 发表于 2025-12-7 08:39\n同问，收到一个75分钟的prompt， 75 Minute Coding Interview - This is a 75 minute coding interview, fo ..."
            ],"""
    
    if quote == "":
        normalized_quote = ""
    else:
        normalized_quote = quote.split('\n')[1] # assume there is only one line of quoted content after the username and timestamp
    
    if normalized_quote.endswith(' ...'):
        normalized_quote = normalized_quote[:-4]
    return {
        'post_id': post_id,
        'content': content,
        'quote': normalized_quote,
        'cleaned_content': cleaned_content,
        'user': reply.get('user', {}),
        'timestamp': reply.get('timestamp', ''),
        'reactions': reply.get('reactions', {}),
        'url': reply.get('url', '')
    }


def find_quoted_post_id(quote: str, replies_data: List[Dict[str, Any]]) -> Optional[str]:
    """
    Find which post is being quoted based on the quote text.
    
    Args:
        quote: Quote text
        replies_data: List of all reply data
        
    Returns:
        post_id of the quoted post, or None if not found
    """
    if not quote:
        return None
    
    # Extract the content part from quote (after username and timestamp)
    # Quote format: "username 发表于 timestamp\ncontent..."
    quote_lines = quote.split('\n')
    if len(quote_lines) < 2:
        # If only one line, use it directly
        quote_content = quote.strip()
    else:
        # Skip first line (username + timestamp) and use rest
        quote_content = '\n'.join(quote_lines[1:]).strip()
    
    # Search for matching content in replies
    for reply_data in replies_data:
        reply_content = reply_data['content'].strip()
        cleaned_content = reply_data['cleaned_content'].strip()
        
        # Check if quote content matches beginning of any reply's content or cleaned_content
        if quote_content and (
            reply_content.startswith(quote_content) or
            cleaned_content.startswith(quote_content) or
            quote_content in reply_content[:len(quote_content) + 100]  # Fuzzy match
        ):
            return reply_data['post_id']
    
    return None


def build_reply_hierarchy(replies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build hierarchical structure of replies based on quotes.
    
    The first reply is typically the main post. Other replies that quote it
    are children. Replies that quote those replies are grandchildren, etc.
    
    Args:
        replies: List of reply dictionaries
        
    Returns:
        List of hierarchical reply structures (typically just one root - the main post)
    """
    if not replies:
        return []
    
    # Extract data from all replies
    replies_data = []
    for reply in replies:
        reply_data = extract_reply_data(reply)
        if reply_data:
            replies_data.append(reply_data)
    
    if not replies_data:
        return []

    ## build hierarchical structure

    contents = []
    parent2ChildrenContentMap = {}
    for rd in replies_data[1:]:
        if rd['quote'] != "" and rd['cleaned_content'] != "":
            parent2ChildrenContentMap[rd['quote']] = parent2ChildrenContentMap.get(rd['quote'], []) + [rd['cleaned_content']]
        contents.append(rd['cleaned_content'])
    print("debug:parent2ChildrenContentMap", parent2ChildrenContentMap)

    # print(parent2ChildrenContentMap)


    # ## becasue quote can be only the right truncuated content, we need to fix the key(which is quote) to the content it refers to
    # ## can have a bug that people post same contents and when we find the first matched one, but quote is referring to other post

    current_quotes = list(parent2ChildrenContentMap.keys())
    quotes2del = []
    for quote in current_quotes:
        for content in contents:
            if content.startswith(quote) and content != quote and quote != "":
                parent2ChildrenContentMap[content] = parent2ChildrenContentMap[quote]
                # del parent2ChildrenContentMap[quote] # we delete too early, we will lose the reference can be used in next element
                # also we content and quote are the same, we should not delete the quote key
                quotes2del.append(quote)
    
    for quote in quotes2del:
        del parent2ChildrenContentMap[quote]   


    # first reply is the main page content
    mainPageContent = replies_data[0]['cleaned_content']


    class ReplyNode:
        content: str
        parent: 'ReplyNode'
        children: List['ReplyNode']
        def __init__(self, content: str):
            self.content = content
            self.parent = None
            self.children = []
        def addChild(self, child: 'ReplyNode'):
            self.children.append(child)

        def toDict(self) -> Dict[str, Any]:
            result = {"content": self.content}
            # Only include children field if it's not empty
            if self.children:
                result["children"] = [child.toDict() for child in self.children]
            return result
        def __str__(self) -> str:
            return json.dumps(self.toDict(), ensure_ascii=False, indent=2)


    # create all nodes
    content2NodeMap = {}
    for pd in replies_data[1:]:
        node = ReplyNode(pd["cleaned_content"])
        content2NodeMap[pd["cleaned_content"]] = node
    for k, v in content2NodeMap.items():
        print(k)
        print(v)
        print("--------------------------------")
    ## now we need to find the children of each node
    for content, children in parent2ChildrenContentMap.items():
        for child in children:
            content2NodeMap[content].addChild(content2NodeMap[child])
            # don't forget to set parent for the child
            content2NodeMap[child].parent = content2NodeMap[content]

    ## after all nodes are created, we need to find the nodes without parents
    nodesWithoutParents = []

    for node in content2NodeMap.values():
        if not node.parent:
            nodesWithoutParents.append(node)

    ## process nodes without parents
    results = []
    results.append({"mainPageContent" : mainPageContent})
    for node in nodesWithoutParents:
        results.append(node.toDict())
    return results


def process_post(post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single post and extract required fields with hierarchical replies.
    
    Args:
        post: Post dictionary from the input JSON
        
    Returns:
        Dictionary with extracted fields or None if invalid
    """
    try:
        # Extract basic post information
        url = post.get('url', '')
        metadata = post.get('metadata', {})
        page_title = metadata.get('page_title', '')
        thread_title = metadata.get('thread_title', '')
        
        # Extract replies from items
        items = post.get('items', {})
        replies = items.get('replies', [])
        main_post = items.get('main_post')
        
        # Combine main_post and replies for hierarchy building
        all_replies = []
        
        # Add main_post as first reply if it exists
        if main_post and isinstance(main_post, dict):
            all_replies.append(main_post)
        
        # Add other replies
        all_replies.extend(replies)
        
        # Build hierarchical structure
        hierarchical_replies = build_reply_hierarchy(all_replies)
        
        return {
            'url': url,
            'page_title': page_title,
            'thread_title': thread_title,
            'replies': hierarchical_replies
        }
    except Exception as e:
        print(f"Error processing post: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def process_json_file(input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Process the input JSON file and extract required fields with hierarchical structure.
    
    Args:
        input_path: Path to input JSON file
        output_path: Optional path for output JSON file. If None, auto-generates name.
        
    Returns:
        Dictionary with extracted data
    """
    # Read input JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract base_url from config
    config = data.get('config', {})
    base_url = config.get('base_url', '')
    
    # Extract summary
    summary = data.get('summary', {})
    
    # Process posts
    posts_data = data.get('posts', [])
    processed_posts = []
    
    for i, post in enumerate(posts_data):
        print(f"Processing post {i+1}/{len(posts_data)}...", file=sys.stderr)
        processed_post = process_post(post)
        if processed_post:
            processed_posts.append(processed_post)
    
    # Build output structure
    output = {
        'base_url': base_url,
        'summary': summary,
        'posts': processed_posts
    }
    
    # Write output JSON
    if output_path is None:
        input_file = Path(input_path)
        output_path = input_file.parent / f"{input_file.stem}_processed{input_file.suffix}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nProcessed {len(processed_posts)} posts", file=sys.stderr)
    print(f"Output written to: {output_path}", file=sys.stderr)
    
    return output


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python process_json.py <input_json_file> [output_json_file]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_path).exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        process_json_file(input_path, output_path)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
