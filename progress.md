


### Dec 26
1. one improvement idea is that, copying the serializer in browser-use [link](https://github.com/browser-use/browser-use/blob/main/browser_use/dom/serializer/serializer.py#L435), and we remove the logic that keeps the shadow content
2. Assign interactive indices to **only** clickable elements that are also visible. During this step, serializer will also build the selector map
```
				self._selector_map[node.original_node.backend_node_id] = node.original_node

```
3. 

## Dec 27
1. /Users/zhenkai/Documents/personal/Projects/WebAgent/src/interactive_web_agent_mcp.py is working now as a mcp. We can successfully use 
2. /Users/zhenkai/Documents/personal/Projects/WebAgent/downloads/sessions/9661bffa_20251227170627/html/002_raw.html

3. fix a bug where empty santizied html is returned 
> I found the bug! In html_sanitizer.py, the data-web-agent-id attribute is not included in the PRESERVE_ATTRIBUTES set (src/html_sanitizer.py:49-53).

  Here's what happens:
  1. _build_element_registry() adds data-web-agent-id attributes to elements
  2. _sanitize_attributes() removes data-web-agent-id because it's not in PRESERVE_ATTRIBUTES
  3. _truncate_preserving_structure() tries to find elements with data-web-agent-id but finds none
  4. Returns empty <html><body></body></html>


some ideas:
1. in get_content function, we can add a customerized extractor based on the website type, explicitly define the extraction logic of the page
 