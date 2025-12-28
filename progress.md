


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