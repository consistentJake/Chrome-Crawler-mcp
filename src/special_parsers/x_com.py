"""
X.com / Twitter Parser
Extracts structured tweet data from X.com pages.

Based on: /Users/zhenkai/Documents/personal/Projects/BrowserAgent/crawler/x_com/dom_extractor.py
"""

from datetime import datetime
from typing import Dict, List, Any
from .base import BaseParser


class XComParser(BaseParser):
    """
    Parser for X.com (formerly Twitter) pages.

    Supports:
    - Search results
    - User timelines
    - Single tweet pages
    - Trending topics
    """

    name = "x.com"
    description = "Extracts tweets with user info, text, metrics, and media"
    version = "1.0.0"

    def parse(self, browser_client) -> Dict[str, Any]:
        """
        Extract tweets from current X.com page.

        Args:
            browser_client: BrowserIntegration instance

        Returns:
            Structured tweet data
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
        tweets = extraction_result.get('tweets', [])

        return {
            "parser": self.name,
            "parser_version": self.version,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(tweets),
            "items": tweets,
            "metadata": {
                "page_title": page_title,
                "extraction_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "total_articles_found": extraction_result.get('count', 0)
            }
        }

    def get_extraction_js(self) -> str:
        """
        JavaScript code to extract tweets from DOM.

        Adapted from dom_extractor.py
        """
        return """
        () => {
          const articles = document.querySelectorAll('article[data-testid="tweet"]');

          const extractTweetFromDOM = (article) => {
            try {
              // Extract username from status link
              const statusLink = article.querySelector('a[href*="/status/"]');
              const href = statusLink?.getAttribute('href') || '';
              const username = href.split('/')[1] || '';

              // Extract display name from User-Name element
              const displayNameElement = article.querySelector('[data-testid="User-Name"]');
              let displayName = '';
              if (displayNameElement) {
                const fullText = displayNameElement.textContent || '';
                displayName = fullText.split('@')[0].trim();
              }

              // Extract tweet text
              const tweetTextElement = article.querySelector('[data-testid="tweetText"]');
              const text = tweetTextElement?.textContent || '';

              // Extract timestamp
              const timeElement = article.querySelector('time');
              const timestamp = timeElement?.getAttribute('datetime') || '';

              // Extract tweet ID from URL
              const tweetId = href.match(/status\\/(\\d+)/)?.[1] || '';

              // Extract metrics from aria-labels
              const metricsGroup = article.querySelector('[role="group"]');
              const metrics = {
                replies: 0,
                retweets: 0,
                likes: 0,
                views: 0,
                bookmarks: 0
              };

              if (metricsGroup) {
                const buttons = metricsGroup.querySelectorAll('button, a');
                buttons.forEach(btn => {
                  const ariaLabel = btn.getAttribute('aria-label') || '';

                  // Parse numbers from aria labels like "10 Replies"
                  const numberMatch = ariaLabel.match(/(\\d+)/);
                  const count = numberMatch ? parseInt(numberMatch[1], 10) : 0;

                  if (ariaLabel.toLowerCase().includes('repl')) {
                    metrics.replies = count;
                  } else if (ariaLabel.toLowerCase().includes('repost')) {
                    metrics.retweets = count;
                  } else if (ariaLabel.toLowerCase().includes('like')) {
                    metrics.likes = count;
                  } else if (ariaLabel.toLowerCase().includes('view')) {
                    metrics.views = count;
                  } else if (ariaLabel.toLowerCase().includes('bookmark')) {
                    metrics.bookmarks = count;
                  }
                });
              }

              // Extract media (images, videos)
              const media = [];
              const mediaImages = article.querySelectorAll('img[src*="pbs.twimg.com/media"]');
              mediaImages.forEach(img => {
                media.push({
                  type: 'photo',
                  url: img.src,
                  alt: img.alt || ''
                });
              });

              // Check for video
              const videoElement = article.querySelector('video');
              if (videoElement) {
                media.push({
                  type: 'video',
                  url: videoElement.src || '',
                  poster: videoElement.poster || ''
                });
              }

              // Check if it's a retweet or quote tweet
              const isRetweet = !!article.querySelector('[data-testid="socialContext"]')?.textContent?.includes('reposted');

              return {
                id: tweetId,
                username,
                displayName: displayName.replace(/\\s+/g, ' ').trim(),
                text: text.trim(),
                timestamp,
                metrics,
                media,
                url: `https://x.com/${username}/status/${tweetId}`,
                isRetweet,
                source: 'dom-parser',
                capturedAt: new Date().toISOString()
              };
            } catch (err) {
              return {
                error: err.message,
                stack: err.stack
              };
            }
          };

          const tweets = Array.from(articles).map(extractTweetFromDOM);

          // Filter out tweets with errors or missing IDs
          const validTweets = tweets.filter(t => t.id && !t.error);

          return {
            count: validTweets.length,
            tweets: validTweets
          };
        }
        """

    def validate_page(self, browser_client) -> bool:
        """Check if current page is a valid X.com page"""
        url = browser_client.get_current_url()
        return 'x.com' in url or 'twitter.com' in url
