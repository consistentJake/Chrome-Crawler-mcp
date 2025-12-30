## get posts
1. use interactive-web-agent, go to https://www.1point3acres.com/bbs/tag/openai-9407-1.html, go to 3rd next page, verify that we are in the 3rd next page, get the list of posts link. The expected post link will be in format "https://www.1point3acres.com/bbs/thread-*-*-*.html"

## test page download
2. use interactive-web-agent, go to https://x.com/search?q=gold, scroll down 20 times,download the content.

## scroll and test in current page
3. still use interactive-web-agent, switch to the tab with URL is like https://x.com/***, then we scroll down 100 times, download the content


## test scrolling
4. use interactive-web-agent, go to https://platform.moonshot.cn/console/account, don't check the page first, just get the current url on the browswer and make sure we go to the right page, then scroll down 2 times, then scroll up 1 times, download the content. 

5. use interactive-web-agent, go to https://x.com/search?q=gold, scroll down 20 times, use special parser to parse and dump the content

6. use interactive-web-agent, go to https://www.1point3acres.com/bbs/tag/openai-9407-1.html, get all the posts link. For each of the post link, we do speical parsing on the post page one by one.