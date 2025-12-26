# Element Registry, RAG, and browser-use Parallels

## Why element_registry exists in html_sanitizer.py
- Creates a compact, structured index of actionable/important elements (links, form controls, headings)
- Filters to visible targets to avoid hidden/irrelevant nodes
- Enriches each element with text, attributes, and multiple locator strategies
- Injects a stable data attribute (data-element-id) for later targeting
- Supports token-bounded outputs while keeping important nodes

## How this helps in RAG
- Produces retrieval-friendly units (one element == one compact "document")
- Separates content for retrieval from action targets for execution
- Enables deterministic grounding: retrieved text maps to a real DOM element
- Lets you prune the DOM aggressively without losing actionable references

## Code example: element_registry flow
```python
from html_sanitizer import HTMLSanitizer

sanitizer = HTMLSanitizer(max_tokens=4000)
result = sanitizer.sanitize(html_content, extraction_mode="links")

# LLM sees a compact indexed list
print(result["indexed_text"])
# [0] <a href="/post/123">Read more</a>
# [1] <a href="/post/456">Details</a>

# Later, resolve a chosen element to a locator for action
picked = result["element_registry"][0]
locator = picked["locators"]["data_id"]  # e.g. [data-element-id="elem-0"]
```

## How browser-use handles the same problem
browser-use uses a DOM snapshot + serializer that marks interactive nodes and builds a selector map.

Key parallels:
- It detects interactive elements and assigns a marker in the serialized DOM
- It stores a selector_map that resolves the LLM-chosen marker back to a DOM node
- That map is the equivalent of element_registry: a compact bridge between LLM text and live DOM

## Code example: browser-use flow (conceptual)
```python
# Conceptual pseudo-flow based on browser-use internals
# 1) Capture DOM state and serialize with interactive markers
state, _timing = serializer.serialize(dom_tree)
print(state.llm_representation())
# ...
# *[12345]<button class="buy">Buy now</button>
# ...

# 2) LLM picks marker 12345; resolve to node via selector_map
node = state.selector_map[12345]  # backend_node_id -> EnhancedDOMTreeNode
# Use node to click or construct a locator
```

Reference points in browser-use:
- DOM serializer assigns interactive markers and builds selector_map
  - browser_use/dom/serializer/serializer.py
- Serialized DOM representation uses backend_node_id markers
  - browser_use/dom/serializer/serializer.py
- selector_map stored on SerializedDOMState
  - browser_use/dom/views.py

## References (browser-use)
- Repository: https://github.com/browser-use/browser-use
- DOM serializer source: https://github.com/browser-use/browser-use/blob/main/browser_use/dom/serializer/serializer.py
- DOM view/state source: https://github.com/browser-use/browser-use/blob/main/browser_use/dom/views.py
- Docs home: https://docs.browser-use.com
- Articles (Browser Use blog):
  - https://browser-use.com/posts/sota-technical-report
  - https://browser-use.com/posts/playwright-to-cdp
  - https://browser-use.com/posts/llm-gateway
  - https://browser-use.com/posts/browser-infra
  - https://browser-use.com/posts/seed-round
  - https://browser-use.com/posts/speed-matters
  - https://browser-use.com/posts/one-year-of-progress

## Practical takeaway
Both approaches solve the same core issue:
- LLMs need a compact, readable representation for reasoning
- The system must still be able to target the exact DOM node for actions
- element_registry (yours) and selector_map (browser-use) are the mapping layer
