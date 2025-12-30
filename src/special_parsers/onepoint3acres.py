"""
1Point3Acres Forum Parser
Extracts structured forum post and review data from 1point3acres.com pages.
"""

from datetime import datetime
from typing import Dict, List, Any
from .base import BaseParser


class OnePoint3AcresParser(BaseParser):
    """
    Parser for 1point3acres.com forum pages.

    Supports:
    - Thread pages with main post and replies
    - Extracts user info, post content, reactions
    - Thread metadata (title, tags, views, etc.)
    """

    name = "1point3acres"
    description = "Extracts forum posts and replies with user info, content, and reactions"
    version = "1.0.0"

    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract forum posts from current 1point3acres page.

        Args:
            browser_client: BrowserIntegration instance

        Returns:
            Structured forum post data
        """
        # Get current URL
        url = browser_client.get_current_url()
        page_title = browser_client.get_page_title()

        # Execute extraction JavaScript
        js_code = self.get_extraction_js()

        start_time = datetime.now()
        result = browser_client.playwright_client.browser_evaluate(function=js_code)
        end_time = datetime.now()

        # Parse response
        extraction_result = self._parse_response(result)

        # Build structured output
        main_post = extraction_result.get('main_post', {})
        replies = extraction_result.get('replies', [])
        metadata = extraction_result.get('metadata', {})

        return {
            "parser": self.name,
            "parser_version": self.version,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(replies) + (1 if main_post else 0),
            "items": {
                "main_post": main_post,
                "replies": replies
            },
            "metadata": {
                "page_title": page_title,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "thread_title": metadata.get('thread_title', ''),
                "thread_tags": metadata.get('tags', []),
                "total_replies": len(replies)
            }
        }

    def get_extraction_js(self) -> str:
        """
        JavaScript code to extract forum posts from DOM.
        """
        return r"""
        () => {
          try {
            // Extract thread metadata
            const extractMetadata = () => {
              // Get thread title from navigation or page header
              let threadTitle = '';

              // Try multiple selectors for thread title
              const titleSelectors = [
                'h1.ts',
                'span#thread_subject',
                '.authi a[href*="thread"]',
                'a[href*="thread-"][title]'
              ];

              for (const selector of titleSelectors) {
                const titleElem = document.querySelector(selector);
                if (titleElem) {
                  threadTitle = titleElem.textContent?.trim() || titleElem.title || '';
                  if (threadTitle) break;
                }
              }

              // Extract tags
              const tags = [];
              const tagElements = document.querySelectorAll('a.taglink, a[href*="tag-"]');
              tagElements.forEach(tagElem => {
                const tagText = tagElem.textContent?.trim();
                if (tagText) tags.push(tagText);
              });

              return {
                thread_title: threadTitle,
                tags: tags
              };
            };

            // Extract a single post (main or reply)
            const extractPost = (postElement) => {
              try {
                // Get post ID from element id
                // Real page uses: id="post_20740624" or id="pid20740624"
                // Sanitized page uses: id="postnum20740624"
                let postId = '';
                if (postElement.id) {
                  if (postElement.id.startsWith('post_')) {
                    postId = postElement.id.replace('post_', '');
                  } else if (postElement.id.startsWith('pid')) {
                    postId = postElement.id.replace('pid', '');
                  } else if (postElement.id.startsWith('postnum')) {
                    postId = postElement.id.replace('postnum', '');
                  }
                }

                // Extract user info
                let username = '';
                let userId = '';
                let userPosts = '';
                let userReplies = '';
                let userPoints = '';

                // Find username link - multiple possible selectors
                const userLink = postElement.querySelector('a.avtm, a[href*="space-uid-"]');
                if (userLink) {
                  const userHref = userLink.getAttribute('href') || '';
                  const userIdMatch = userHref.match(/uid[=-](\d+)/);
                  if (userIdMatch) userId = userIdMatch[1];

                  // Username might be in the link text or nearby
                  username = userLink.textContent?.trim() || '';
                }

                // Look for username in alternative locations
                if (!username) {
                  const userNameElem = postElement.querySelector('.xi2[href*="space-uid-"]');
                  if (userNameElem) {
                    username = userNameElem.textContent?.trim() || '';
                  }
                }

                // Extract user stats (posts, replies, points)
                const statLinks = postElement.querySelectorAll('a.xi2[href*="do=thread"], a.xi2[href*="do=profile"]');
                statLinks.forEach(link => {
                  const text = link.textContent?.trim() || '';
                  const href = link.getAttribute('href') || '';

                  if (href.includes('type=thread')) {
                    userPosts = text;
                  } else if (href.includes('type=reply')) {
                    userReplies = text;
                  } else if (href.includes('do=profile')) {
                    userPoints = text;
                  }
                });

                // Extract post content
                // Content is typically in a div with specific classes
                let content = '';
                const contentSelectors = [
                  '.t_f',
                  '.pcb',
                  '[id^="postmessage_"]',
                  '.message'
                ];

                for (const selector of contentSelectors) {
                  const contentElem = postElement.querySelector(selector);
                  if (contentElem) {
                    content = contentElem.textContent?.trim() || '';
                    if (content) break;
                  }
                }

                // Extract timestamp
                let timestamp = '';
                const timeElem = postElement.querySelector('em[id^="authorposton"], .authi em');
                if (timeElem) {
                  timestamp = timeElem.textContent?.trim() || '';
                }

                // Extract reactions/likes
                const reactions = {};

                // Look for thumbs up/down buttons
                const likeButton = postElement.querySelector('a[href*="recommend&do=add"]');
                if (likeButton) {
                  const likeText = likeButton.textContent?.trim() || '0';
                  const likeMatch = likeText.match(/(\d+)/);
                  reactions.likes = likeMatch ? parseInt(likeMatch[1], 10) : 0;
                }

                const dislikeButton = postElement.querySelector('a[href*="recommend&do=subtract"]');
                if (dislikeButton) {
                  const dislikeText = dislikeButton.textContent?.trim() || '0';
                  const dislikeMatch = dislikeText.match(/(\d+)/);
                  reactions.dislikes = dislikeMatch ? parseInt(dislikeMatch[1], 10) : 0;
                }

                // Check for emoji reactions
                const reactionElements = postElement.querySelectorAll('[id^="reaction-"]');
                reactionElements.forEach(reactionElem => {
                  const reactionText = reactionElem.textContent?.trim() || '';
                  // Parse emoji reactions like "😮1"
                  const match = reactionText.match(/([^\d]+)(\d+)/);
                  if (match) {
                    const emoji = match[1].trim();
                    const count = parseInt(match[2], 10);
                    if (!reactions.emoji_reactions) {
                      reactions.emoji_reactions = [];
                    }
                    reactions.emoji_reactions.push({ emoji, count });
                  }
                });

                // Check if post is anonymous
                const isAnonymous = postElement.querySelector('[href*="/next/contact-post/"]') !== null;

                // Extract any quoted content
                const quotes = [];
                const quoteElements = postElement.querySelectorAll('.quote, blockquote');
                quoteElements.forEach(quote => {
                  quotes.push(quote.textContent?.trim() || '');
                });

                return {
                  post_id: postId,
                  user: {
                    username: username || 'Unknown',
                    user_id: userId,
                    stats: {
                      posts: userPosts,
                      replies: userReplies,
                      points: userPoints
                    },
                    is_anonymous: isAnonymous
                  },
                  content: content,
                  timestamp: timestamp,
                  reactions: reactions,
                  quotes: quotes,
                  url: window.location.href + '#' + postId
                };
              } catch (err) {
                return {
                  error: err.message,
                  stack: err.stack
                };
              }
            };

            // Extract main post
            // Main post is typically the first post or has specific markers
            let mainPost = null;

            // Try multiple selectors for posts (real page vs sanitized)
            let postElements = document.querySelectorAll('[id^="post_"]');  // Real page: id="post_XXXXX"
            if (postElements.length === 0) {
              postElements = document.querySelectorAll('[id^="pid"]');  // Real page: id="pidXXXXX"
            }
            if (postElements.length === 0) {
              postElements = document.querySelectorAll('[id^="postnum"]');  // Sanitized page
            }

            if (postElements.length > 0) {
              mainPost = extractPost(postElements[0]);
            }

            // Extract all replies
            const replies = [];

            // Skip first one if we already got it as main post
            const startIdx = mainPost ? 1 : 0;

            for (let i = startIdx; i < postElements.length; i++) {
              const post = extractPost(postElements[i]);
              if (post && !post.error) {
                replies.push(post);
              }
            }

            // Extract metadata
            const metadata = extractMetadata();

            return {
              main_post: mainPost,
              replies: replies,
              metadata: metadata,
              total_posts: postElements.length,
              extraction_timestamp: new Date().toISOString()
            };

          } catch (err) {
            return {
              error: err.message,
              stack: err.stack
            };
          }
        }
        """

    def validate_page(self, browser_client) -> bool:
        """Check if current page is a valid 1point3acres forum page"""
        url = browser_client.get_current_url()
        return '1point3acres.com' in url or '1point3acres' in url
