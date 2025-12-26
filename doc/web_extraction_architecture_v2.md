# Web Content Extraction Tool Architecture v2
## With Bidirectional Element Mapping for Agentic AI
### Incorporating Browser-Use Design Patterns

---

## Problem Statement

When building a web agent tool that:
1. **Sanitizes/simplifies HTML** for LLM consumption (reducing tokens, removing noise)
2. **Allows LLM to make decisions** (e.g., "click this link", "extract this data")
3. **Executes actions on the original page** via Playwright

The critical challenge is: **How do we map elements from the simplified/sanitized HTML back to the original DOM so Playwright can interact with them?**

---

## Solution Overview

We combine the best of both approaches:
- **Numeric indices** for LLM communication (token-efficient, like browser-use)
- **Injected data attributes** as primary locator (robust, survives DOM changes)
- **Visual highlighting** for debugging and multimodal agents
- **Multiple fallback locators** for reliability

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         ARCHITECTURE OVERVIEW v2                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐     ┌───────────────────────────────────────────────────┐  │
│  │   Original   │────▶│            DOM Processor (in-browser JS)          │  │
│  │     Page     │     │  ┌─────────────────┐  ┌─────────────────────────┐ │  │
│  │              │     │  │  ID Injection   │  │  Visual Highlighter     │ │  │
│  └──────────────┘     │  │  (data-element- │  │  (optional overlays     │ │  │
│                       │  │   id attribute) │  │   with numeric labels)  │ │  │
│                       │  └────────┬────────┘  └────────────┬────────────┘ │  │
│                       └───────────┼────────────────────────┼──────────────┘  │
│                                   │                        │                  │
│                                   ▼                        ▼                  │
│  ┌────────────────────────────────────────┐   ┌─────────────────────────────┐│
│  │         Element Registry               │   │   Annotated Screenshot      ││
│  │  ┌──────────────────────────────────┐ │   │   (for multimodal models)   ││
│  │  │ Index: 0                         │ │   │                             ││
│  │  │ elementId: "elem-a1b2c3"         │ │   │   ┌─────┐                   ││
│  │  │ tag: "button"                    │ │   │   │ [0] │ Login Button      ││
│  │  │ text: "Login"                    │ │   │   └─────┘                   ││
│  │  │ locators: {                      │ │   │   ┌─────┐                   ││
│  │  │   primary: [data-element-id=...] │ │   │   │ [1] │ Search Box        ││
│  │  │   xpath: //button[1]             │ │   │   └─────┘                   ││
│  │  │   css: button.login-btn          │ │   │                             ││
│  │  │   role: button[name="Login"]     │ │   └─────────────────────────────┘│
│  │  │ }                                │ │                                   │
│  │  │ bbox: {x, y, width, height}      │ │                                   │
│  │  │ isVisible: true                  │ │                                   │
│  │  │ isInteractive: true              │ │                                   │
│  │  └──────────────────────────────────┘ │                                   │
│  │  ┌──────────────────────────────────┐ │                                   │
│  │  │ Index: 1                         │ │                                   │
│  │  │ ...                              │ │                                   │
│  │  └──────────────────────────────────┘ │                                   │
│  └───────────────────┬────────────────────┘                                   │
│                      │                                                        │
│                      ▼                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        HTML Sanitizer                                   │  │
│  │  - Remove: scripts, styles, comments, hidden elements                  │  │
│  │  - Strip: most attributes (keep data-element-id, href, src, alt)       │  │
│  │  - Condense: merge nested containers, remove empty nodes               │  │
│  │  - Output modes: full | structure | minimal | interactive-only         │  │
│  └───────────────────┬────────────────────────────────────────────────────┘  │
│                      │                                                        │
│                      ▼                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │              LLM-Ready Output (choose format)                           │  │
│  │                                                                         │  │
│  │  Format A: Indexed Text (browser-use style) ──────────────────────────  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐    │  │
│  │  │ [0] <button>Login</button>                                      │    │  │
│  │  │ [1] <input type="text" placeholder="Search...">                 │    │  │
│  │  │ [2] <a href="/about">About Us</a>                               │    │  │
│  │  │ [3] <select><option>Option 1</option>...</select>               │    │  │
│  │  └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                         │  │
│  │  Format B: Sanitized HTML (with data-element-id) ─────────────────────  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐    │  │
│  │  │ <button data-element-id="elem-a1b2c3">Login</button>            │    │  │
│  │  │ <input data-element-id="elem-d4e5f6" placeholder="Search...">   │    │  │
│  │  └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                         │  │
│  │  Format C: Structured JSON ───────────────────────────────────────────  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐    │  │
│  │  │ {"elements": [                                                  │    │  │
│  │  │   {"index": 0, "tag": "button", "text": "Login", ...},          │    │  │
│  │  │   {"index": 1, "tag": "input", "placeholder": "Search...", ...} │    │  │
│  │  │ ]}                                                              │    │  │
│  │  └────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────┬────────────────────────────────────────────────────┘  │
│                      │                                                        │
│                      ▼                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         LLM Agent                                       │  │
│  │  Input: Simplified content + optional screenshot                        │  │
│  │  Task: "Log into the website with username 'test@example.com'"          │  │
│  │  Output: {"action": "click", "index": 0}                                │  │
│  │      or: {"action": "type", "index": 1, "text": "search query"}         │  │
│  └───────────────────┬────────────────────────────────────────────────────┘  │
│                      │                                                        │
│                      ▼                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      Action Executor                                    │  │
│  │                                                                         │  │
│  │  1. LLM returns: {"action": "click", "index": 0}                        │  │
│  │  2. Look up index 0 in registry → get element info                      │  │
│  │  3. Try locators in priority order:                                     │  │
│  │     ① page.locator('[data-element-id="elem-a1b2c3"]')  ← most stable   │  │
│  │     ② page.locator('[data-testid="login-btn"]')        ← if exists     │  │
│  │     ③ page.locator('#login-button')                    ← if has id     │  │
│  │     ④ page.getByRole('button', {name: 'Login'})        ← semantic      │  │
│  │     ⑤ page.locator('xpath=//button[1]')                ← structural    │  │
│  │     ⑥ page.getByText('Login')                          ← text-based    │  │
│  │  4. Execute action on first successful locator                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Stage 1: DOM Processing (In-Browser JavaScript)

This script runs via Playwright's `page.evaluate()` and performs:
1. Element discovery and filtering
2. ID injection
3. Registry building
4. Optional visual highlighting

```javascript
/**
 * buildDomTree.js - DOM processor for web agents
 * 
 * Inspired by browser-use's approach but with enhancements:
 * - Uses stable element IDs (not just numeric indices)
 * - Supports multiple output formats
 * - Includes comprehensive locator strategies
 */

(function(options = {}) {
  const {
    doHighlightElements = false,
    highlightColor = '#ff0000',
    viewportExpansion = 0,  // -1 for all elements, 0 for viewport only, N for pixels beyond
    includeTextNodes = false,
  } = options;

  // ============================================================================
  // CONFIGURATION
  // ============================================================================
  
  const INTERACTIVE_SELECTORS = [
    'a[href]',
    'button',
    'input',
    'select',
    'textarea',
    '[role="button"]',
    '[role="link"]',
    '[role="menuitem"]',
    '[role="tab"]',
    '[role="checkbox"]',
    '[role="radio"]',
    '[role="switch"]',
    '[role="slider"]',
    '[role="textbox"]',
    '[role="combobox"]',
    '[role="listbox"]',
    '[role="option"]',
    '[onclick]',
    '[onmousedown]',
    '[onmouseup]',
    '[contenteditable="true"]',
    'details',
    'summary',
    'label',
  ];

  const CONTENT_SELECTORS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p',
    'li',
    'td', 'th',
    'img[alt]',
    'figcaption',
  ];

  const SKIP_TAGS = new Set([
    'script', 'style', 'noscript', 'template', 'svg', 'path',
    'meta', 'link', 'head', 'title',
  ]);

  const PRESERVE_ATTRIBUTES = new Set([
    'href', 'src', 'alt', 'title', 'type', 'name', 'value',
    'placeholder', 'aria-label', 'role', 'data-testid',
  ]);

  // ============================================================================
  // STATE
  // ============================================================================
  
  let elementIndex = 0;
  const registry = [];
  const elementIdMap = new Map();  // DOM element -> elementId
  let highlightContainer = null;

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  /**
   * Generate a unique, stable element ID
   * Uses a combination of tag, position, and content hash for stability
   */
  function generateElementId(element) {
    const tag = element.tagName.toLowerCase();
    const text = (element.textContent || '').trim().substring(0, 20);
    const hash = simpleHash(tag + text + element.className);
    return `elem-${hash}`;
  }

  function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;  // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36).substring(0, 6);
  }

  /**
   * Check if element is visible
   */
  function isElementVisible(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;
    
    const style = window.getComputedStyle(element);
    if (style.display === 'none') return false;
    if (style.visibility === 'hidden') return false;
    if (parseFloat(style.opacity) === 0) return false;
    
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return false;
    
    return true;
  }

  /**
   * Check if element is within viewport (with expansion)
   */
  function isInViewport(element, expansion = 0) {
    if (expansion === -1) return true;  // -1 means include all
    
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;
    const viewWidth = window.innerWidth;
    
    return (
      rect.bottom >= -expansion &&
      rect.top <= viewHeight + expansion &&
      rect.right >= -expansion &&
      rect.left <= viewWidth + expansion
    );
  }

  /**
   * Check if element is interactive
   */
  function isInteractiveElement(element) {
    const tag = element.tagName.toLowerCase();
    
    // Form elements are always interactive
    if (['input', 'button', 'select', 'textarea'].includes(tag)) return true;
    
    // Links with href
    if (tag === 'a' && element.hasAttribute('href')) return true;
    
    // Elements with click handlers
    if (element.onclick || element.hasAttribute('onclick')) return true;
    
    // Elements with interactive roles
    const role = element.getAttribute('role');
    if (role && ['button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 
                 'switch', 'slider', 'textbox', 'combobox', 'listbox', 'option'].includes(role)) {
      return true;
    }
    
    // Contenteditable
    if (element.isContentEditable) return true;
    
    // Check computed cursor style
    const cursor = window.getComputedStyle(element).cursor;
    if (cursor === 'pointer') return true;
    
    return false;
  }

  /**
   * Check if element is the topmost at its position (not obscured)
   */
  function isTopElement(element) {
    const rect = element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    // Check if center point hits this element
    const topEl = document.elementFromPoint(centerX, centerY);
    if (!topEl) return false;
    
    return element === topEl || element.contains(topEl) || topEl.contains(element);
  }

  /**
   * Generate XPath for element
   */
  function getXPath(element) {
    // If element has ID, use it
    if (element.id) {
      return `//*[@id="${element.id}"]`;
    }
    
    const parts = [];
    let current = element;
    
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let index = 1;
      let sibling = current.previousElementSibling;
      
      while (sibling) {
        if (sibling.tagName === current.tagName) index++;
        sibling = sibling.previousElementSibling;
      }
      
      const tagName = current.tagName.toLowerCase();
      const part = index > 1 ? `${tagName}[${index}]` : tagName;
      parts.unshift(part);
      
      current = current.parentElement;
    }
    
    return '/' + parts.join('/');
  }

  /**
   * Generate CSS selector for element
   */
  function getCssSelector(element) {
    if (element.id) {
      return `#${CSS.escape(element.id)}`;
    }
    
    const parts = [];
    let current = element;
    
    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      
      // Add class if unique enough
      if (current.className && typeof current.className === 'string') {
        const classes = current.className.trim().split(/\s+/).filter(c => c.length > 0);
        if (classes.length > 0 && classes[0].length < 30) {
          selector += `.${CSS.escape(classes[0])}`;
        }
      }
      
      // Add nth-child if needed for uniqueness
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
        if (siblings.length > 1) {
          const index = siblings.indexOf(current) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      
      parts.unshift(selector);
      
      // Stop if we have a unique enough selector
      if (current.id || document.querySelectorAll(parts.join(' > ')).length === 1) {
        break;
      }
      
      current = current.parentElement;
    }
    
    return parts.join(' > ');
  }

  /**
   * Get accessible name for element
   */
  function getAccessibleName(element) {
    // aria-label takes precedence
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) return ariaLabel;
    
    // aria-labelledby
    const labelledBy = element.getAttribute('aria-labelledby');
    if (labelledBy) {
      const labelEl = document.getElementById(labelledBy);
      if (labelEl) return labelEl.textContent?.trim();
    }
    
    // For inputs, check associated label
    if (element.tagName.toLowerCase() === 'input') {
      const id = element.id;
      if (id) {
        const label = document.querySelector(`label[for="${id}"]`);
        if (label) return label.textContent?.trim();
      }
    }
    
    // Title attribute
    const title = element.getAttribute('title');
    if (title) return title;
    
    // Placeholder for inputs
    const placeholder = element.getAttribute('placeholder');
    if (placeholder) return placeholder;
    
    // Alt text for images
    const alt = element.getAttribute('alt');
    if (alt) return alt;
    
    // Text content (truncated)
    return element.textContent?.trim().substring(0, 50) || '';
  }

  // ============================================================================
  // VISUAL HIGHLIGHTING (Optional, for debugging/multimodal)
  // ============================================================================

  function createHighlightContainer() {
    let container = document.getElementById('agent-highlight-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'agent-highlight-container';
      container.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 2147483647;
      `;
      document.body.appendChild(container);
    }
    return container;
  }

  function highlightElement(element, index, parentIframe = null) {
    if (!highlightContainer) {
      highlightContainer = createHighlightContainer();
    }

    const rect = element.getBoundingClientRect();
    
    // Adjust for iframe offset if needed
    let offsetX = 0, offsetY = 0;
    if (parentIframe) {
      const iframeRect = parentIframe.getBoundingClientRect();
      offsetX = iframeRect.left;
      offsetY = iframeRect.top;
    }

    // Create highlight overlay
    const overlay = document.createElement('div');
    overlay.className = 'agent-highlight-overlay';
    overlay.style.cssText = `
      position: fixed;
      left: ${rect.left + offsetX}px;
      top: ${rect.top + offsetY}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      border: 2px solid ${highlightColor};
      background: ${highlightColor}20;
      pointer-events: none;
      box-sizing: border-box;
    `;

    // Create label
    const label = document.createElement('div');
    label.className = 'agent-highlight-label';
    label.textContent = String(index);
    label.style.cssText = `
      position: fixed;
      left: ${rect.left + offsetX}px;
      top: ${Math.max(0, rect.top + offsetY - 18)}px;
      background: ${highlightColor};
      color: white;
      font-size: 12px;
      font-weight: bold;
      font-family: monospace;
      padding: 1px 4px;
      border-radius: 2px;
      pointer-events: none;
      z-index: 2147483647;
    `;

    highlightContainer.appendChild(overlay);
    highlightContainer.appendChild(label);
  }

  function clearHighlights() {
    const container = document.getElementById('agent-highlight-container');
    if (container) {
      container.remove();
    }
    highlightContainer = null;
  }

  // ============================================================================
  // MAIN PROCESSING FUNCTIONS
  // ============================================================================

  /**
   * Process a single element and add to registry
   */
  function processElement(element, parentIframe = null) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return null;
    if (SKIP_TAGS.has(element.tagName.toLowerCase())) return null;
    
    const isVisible = isElementVisible(element);
    if (!isVisible) return null;
    
    const inViewport = isInViewport(element, viewportExpansion);
    if (!inViewport) return null;
    
    const isInteractive = isInteractiveElement(element);
    const isTop = viewportExpansion === -1 ? true : isTopElement(element);
    
    // For now, only process interactive elements or important content
    const isImportantContent = ['h1','h2','h3','h4','h5','h6','img'].includes(
      element.tagName.toLowerCase()
    );
    
    if (!isInteractive && !isImportantContent) return null;
    if (isInteractive && !isTop) return null;
    
    // Generate and inject element ID
    const elementId = generateElementId(element);
    element.setAttribute('data-element-id', elementId);
    
    const currentIndex = elementIndex++;
    
    // Build locators
    const locators = {
      primary: `[data-element-id="${elementId}"]`,
      testId: element.dataset.testid ? `[data-testid="${element.dataset.testid}"]` : null,
      id: element.id ? `#${element.id}` : null,
      xpath: getXPath(element),
      css: getCssSelector(element),
      role: element.getAttribute('role'),
      ariaLabel: element.getAttribute('aria-label'),
      text: element.textContent?.trim().substring(0, 50),
    };
    
    // Extract relevant attributes
    const attributes = {};
    for (const attr of PRESERVE_ATTRIBUTES) {
      const value = element.getAttribute(attr);
      if (value) attributes[attr] = value;
    }
    
    // Get bounding box
    const rect = element.getBoundingClientRect();
    const bbox = {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    };
    
    // Build entry
    const entry = {
      index: currentIndex,
      elementId: elementId,
      tag: element.tagName.toLowerCase(),
      text: (element.textContent || '').trim().substring(0, 100),
      accessibleName: getAccessibleName(element),
      locators: locators,
      attributes: attributes,
      bbox: bbox,
      isVisible: isVisible,
      isInteractive: isInteractive,
      isTopElement: isTop,
      parentIframe: parentIframe ? parentIframe.src : null,
    };
    
    registry.push(entry);
    elementIdMap.set(element, elementId);
    
    // Visual highlighting
    if (doHighlightElements && isInteractive) {
      highlightElement(element, currentIndex, parentIframe);
    }
    
    return entry;
  }

  /**
   * Recursively process DOM tree
   */
  function processTree(root, parentIframe = null) {
    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT,
      {
        acceptNode: (node) => {
          if (SKIP_TAGS.has(node.tagName.toLowerCase())) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    let node = walker.currentNode;
    while (node) {
      processElement(node, parentIframe);
      
      // Handle iframes
      if (node.tagName.toLowerCase() === 'iframe') {
        try {
          const iframeDoc = node.contentDocument;
          if (iframeDoc) {
            processTree(iframeDoc.body, node);
          }
        } catch (e) {
          // Cross-origin iframe, skip
        }
      }
      
      // Handle shadow DOM
      if (node.shadowRoot) {
        processTree(node.shadowRoot, parentIframe);
      }
      
      node = walker.nextNode();
    }
  }

  /**
   * Generate simplified HTML representation
   */
  function generateSimplifiedHtml() {
    let html = '';
    for (const entry of registry) {
      const tag = entry.tag;
      const attrs = [`data-element-id="${entry.elementId}"`];
      
      // Add important attributes
      if (entry.attributes.href) attrs.push(`href="${entry.attributes.href}"`);
      if (entry.attributes.src) attrs.push(`src="${entry.attributes.src}"`);
      if (entry.attributes.type) attrs.push(`type="${entry.attributes.type}"`);
      if (entry.attributes.placeholder) attrs.push(`placeholder="${entry.attributes.placeholder}"`);
      if (entry.attributes.alt) attrs.push(`alt="${entry.attributes.alt}"`);
      if (entry.attributes.value) attrs.push(`value="${entry.attributes.value}"`);
      
      const text = entry.text.substring(0, 50);
      const selfClosing = ['input', 'img', 'br', 'hr'].includes(tag);
      
      if (selfClosing) {
        html += `<${tag} ${attrs.join(' ')}>\n`;
      } else {
        html += `<${tag} ${attrs.join(' ')}>${text}</${tag}>\n`;
      }
    }
    return html;
  }

  /**
   * Generate indexed text representation (browser-use style)
   */
  function generateIndexedText() {
    let text = '';
    for (const entry of registry) {
      const tag = entry.tag;
      const attrs = [];
      
      if (entry.attributes.href) attrs.push(`href="${entry.attributes.href}"`);
      if (entry.attributes.type) attrs.push(`type="${entry.attributes.type}"`);
      if (entry.attributes.placeholder) attrs.push(`placeholder="${entry.attributes.placeholder}"`);
      
      const attrStr = attrs.length > 0 ? ' ' + attrs.join(' ') : '';
      const content = entry.accessibleName || entry.text.substring(0, 50);
      const selfClosing = ['input', 'img', 'br', 'hr'].includes(tag);
      
      if (selfClosing) {
        text += `[${entry.index}] <${tag}${attrStr}>\n`;
      } else {
        text += `[${entry.index}] <${tag}${attrStr}>${content}</${tag}>\n`;
      }
    }
    return text;
  }

  // ============================================================================
  // MAIN EXECUTION
  // ============================================================================

  // Clear any existing highlights
  clearHighlights();
  
  // Process the DOM
  processTree(document.body);
  
  // Return results
  return {
    registry: registry,
    indexedText: generateIndexedText(),
    simplifiedHtml: generateSimplifiedHtml(),
    elementCount: registry.length,
    timestamp: Date.now(),
  };

})
```

### Stage 2: Python Integration

```python
# web_agent.py
"""
Web Agent Tool with Bidirectional Element Mapping

Features:
- Element ID injection for stable references
- Multiple output formats (indexed text, HTML, JSON)
- Visual highlighting for debugging
- Robust locator fallback strategies
- Support for iframes and shadow DOM
"""

from playwright.async_api import async_playwright, Page, Locator
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from pathlib import Path
import json
import asyncio


@dataclass
class ElementInfo:
    """Information about a single interactive element"""
    index: int
    element_id: str
    tag: str
    text: str
    accessible_name: str
    locators: Dict[str, Optional[str]]
    attributes: Dict[str, str]
    bbox: Dict[str, float]
    is_visible: bool
    is_interactive: bool
    is_top_element: bool
    parent_iframe: Optional[str] = None


@dataclass
class PageState:
    """Complete state of a processed page"""
    url: str
    title: str
    elements: List[ElementInfo]
    indexed_text: str
    simplified_html: str
    element_count: int
    timestamp: int
    screenshot: Optional[bytes] = None
    
    def get_element_by_index(self, index: int) -> Optional[ElementInfo]:
        """Get element by its numeric index"""
        for el in self.elements:
            if el.index == index:
                return el
        return None
    
    def get_element_by_id(self, element_id: str) -> Optional[ElementInfo]:
        """Get element by its stable ID"""
        for el in self.elements:
            if el.element_id == element_id:
                return el
        return None


class WebAgentTool:
    """
    Web agent tool with bidirectional element mapping.
    
    Usage:
        agent = WebAgentTool()
        await agent.init_browser()
        
        await agent.navigate('https://example.com')
        state = await agent.analyze_page()
        
        # LLM sees state.indexed_text:
        # [0] <button>Login</button>
        # [1] <input type="text" placeholder="Username">
        
        # LLM decides to click button 0
        await agent.click(0)
        
        # Or type into input 1
        await agent.type_text(1, "my_username")
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None
        self.current_state: Optional[PageState] = None
        self._js_code: Optional[str] = None
    
    async def init_browser(
        self,
        headless: bool = True,
        viewport: Dict[str, int] = None,
    ):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport=viewport or {'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
        
        # Load the DOM processing script
        self._js_code = self._get_dom_processor_script()
    
    def _get_dom_processor_script(self) -> str:
        """Load the DOM processor JavaScript"""
        # In production, load from file
        # For this example, we embed a simplified version
        return """
        (function(options) {
            // ... (the full JavaScript from Stage 1)
            // Simplified version for brevity:
            
            const registry = [];
            let index = 0;
            
            document.querySelectorAll('a, button, input, select, textarea, [role="button"]')
                .forEach(el => {
                    if (el.offsetParent === null) return;
                    
                    const elementId = 'elem-' + Math.random().toString(36).substr(2, 6);
                    el.setAttribute('data-element-id', elementId);
                    
                    const rect = el.getBoundingClientRect();
                    
                    registry.push({
                        index: index++,
                        elementId: elementId,
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 100),
                        accessibleName: el.getAttribute('aria-label') || 
                                       el.getAttribute('title') ||
                                       el.getAttribute('placeholder') ||
                                       (el.textContent || '').trim().substring(0, 50),
                        locators: {
                            primary: `[data-element-id="${elementId}"]`,
                            testId: el.dataset.testid ? `[data-testid="${el.dataset.testid}"]` : null,
                            id: el.id ? `#${el.id}` : null,
                            xpath: getXPath(el),
                        },
                        attributes: {
                            href: el.getAttribute('href'),
                            type: el.getAttribute('type'),
                            placeholder: el.getAttribute('placeholder'),
                            value: el.value,
                        },
                        bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                        isVisible: true,
                        isInteractive: true,
                    });
                    
                    // Optional: Visual highlighting
                    if (options.doHighlightElements) {
                        const overlay = document.createElement('div');
                        overlay.style.cssText = `
                            position: fixed;
                            left: ${rect.left}px;
                            top: ${rect.top}px;
                            width: ${rect.width}px;
                            height: ${rect.height}px;
                            border: 2px solid red;
                            pointer-events: none;
                            z-index: 999999;
                        `;
                        const label = document.createElement('div');
                        label.textContent = String(index - 1);
                        label.style.cssText = `
                            position: fixed;
                            left: ${rect.left}px;
                            top: ${Math.max(0, rect.top - 18)}px;
                            background: red;
                            color: white;
                            font-size: 12px;
                            padding: 1px 4px;
                            pointer-events: none;
                            z-index: 999999;
                        `;
                        document.body.appendChild(overlay);
                        document.body.appendChild(label);
                    }
                });
            
            function getXPath(el) {
                if (el.id) return `//*[@id="${el.id}"]`;
                const parts = [];
                while (el && el.nodeType === 1) {
                    let idx = 1;
                    let sib = el.previousElementSibling;
                    while (sib) {
                        if (sib.tagName === el.tagName) idx++;
                        sib = sib.previousElementSibling;
                    }
                    parts.unshift(el.tagName.toLowerCase() + (idx > 1 ? `[${idx}]` : ''));
                    el = el.parentElement;
                }
                return '/' + parts.join('/');
            }
            
            // Generate indexed text output
            let indexedText = '';
            for (const el of registry) {
                const attrs = [];
                if (el.attributes.href) attrs.push(`href="${el.attributes.href}"`);
                if (el.attributes.type) attrs.push(`type="${el.attributes.type}"`);
                if (el.attributes.placeholder) attrs.push(`placeholder="${el.attributes.placeholder}"`);
                const attrStr = attrs.length ? ' ' + attrs.join(' ') : '';
                const content = el.accessibleName || el.text.substring(0, 50);
                const selfClose = ['input', 'img'].includes(el.tag);
                if (selfClose) {
                    indexedText += `[${el.index}] <${el.tag}${attrStr}>\\n`;
                } else {
                    indexedText += `[${el.index}] <${el.tag}${attrStr}>${content}</${el.tag}>\\n`;
                }
            }
            
            return {
                registry: registry,
                indexedText: indexedText,
                elementCount: registry.length,
                timestamp: Date.now(),
            };
        })
        """
    
    async def navigate(self, url: str, wait_until: str = 'networkidle'):
        """Navigate to a URL"""
        await self.page.goto(url, wait_until=wait_until)
    
    async def analyze_page(
        self,
        highlight: bool = False,
        include_screenshot: bool = False,
        viewport_expansion: int = 0,
    ) -> PageState:
        """
        Analyze the current page and return structured state.
        
        Args:
            highlight: Whether to add visual overlays for debugging
            include_screenshot: Whether to capture a screenshot
            viewport_expansion: Pixels beyond viewport to include (-1 for all)
        
        Returns:
            PageState object with all element information
        """
        # Execute DOM processor
        options = {
            'doHighlightElements': highlight,
            'viewportExpansion': viewport_expansion,
        }
        result = await self.page.evaluate(f"({self._js_code})({json.dumps(options)})")
        
        # Parse results
        elements = [
            ElementInfo(
                index=el['index'],
                element_id=el['elementId'],
                tag=el['tag'],
                text=el['text'],
                accessible_name=el.get('accessibleName', ''),
                locators=el['locators'],
                attributes=el.get('attributes', {}),
                bbox=el['bbox'],
                is_visible=el.get('isVisible', True),
                is_interactive=el.get('isInteractive', True),
                is_top_element=el.get('isTopElement', True),
                parent_iframe=el.get('parentIframe'),
            )
            for el in result['registry']
        ]
        
        # Capture screenshot if requested
        screenshot = None
        if include_screenshot:
            screenshot = await self.page.screenshot(full_page=False)
        
        # Build state
        self.current_state = PageState(
            url=self.page.url,
            title=await self.page.title(),
            elements=elements,
            indexed_text=result['indexedText'],
            simplified_html=result.get('simplifiedHtml', ''),
            element_count=result['elementCount'],
            timestamp=result['timestamp'],
            screenshot=screenshot,
        )
        
        return self.current_state
    
    async def _get_locator(self, index_or_id: int | str) -> Locator:
        """
        Get a Playwright locator for an element with fallback strategies.
        
        Args:
            index_or_id: Either numeric index or element ID string
        
        Returns:
            Playwright Locator object
        """
        if not self.current_state:
            raise RuntimeError("Must call analyze_page() first")
        
        # Find element info
        if isinstance(index_or_id, int):
            element = self.current_state.get_element_by_index(index_or_id)
        else:
            element = self.current_state.get_element_by_id(index_or_id)
        
        if not element:
            raise ValueError(f"Element not found: {index_or_id}")
        
        locators = element.locators
        
        # Try locators in priority order
        strategies = [
            ('primary', locators.get('primary')),       # data-element-id (most stable)
            ('testId', locators.get('testId')),         # data-testid
            ('id', locators.get('id')),                 # HTML id
            ('xpath', locators.get('xpath')),           # XPath
            ('css', locators.get('css')),               # CSS selector
            ('text', locators.get('text')),             # Text content
        ]
        
        for strategy_name, selector in strategies:
            if not selector:
                continue
            
            try:
                if strategy_name == 'xpath':
                    locator = self.page.locator(f"xpath={selector}")
                elif strategy_name == 'text':
                    locator = self.page.get_by_text(selector, exact=False)
                else:
                    locator = self.page.locator(selector)
                
                # Verify locator finds exactly one element
                count = await locator.count()
                if count == 1:
                    return locator
                elif count > 1:
                    # Try to narrow down with first()
                    return locator.first
            except Exception:
                continue
        
        # Last resort: use the primary locator even if it might fail
        return self.page.locator(locators['primary'])
    
    async def click(self, index_or_id: int | str) -> bool:
        """Click an element by index or ID"""
        locator = await self._get_locator(index_or_id)
        await locator.click()
        return True
    
    async def type_text(
        self,
        index_or_id: int | str,
        text: str,
        clear: bool = True,
    ) -> bool:
        """Type text into an element"""
        locator = await self._get_locator(index_or_id)
        if clear:
            await locator.clear()
        await locator.type(text)
        return True
    
    async def fill(self, index_or_id: int | str, text: str) -> bool:
        """Fill an input with text (faster than type)"""
        locator = await self._get_locator(index_or_id)
        await locator.fill(text)
        return True
    
    async def select_option(self, index_or_id: int | str, value: str) -> bool:
        """Select an option from a dropdown"""
        locator = await self._get_locator(index_or_id)
        await locator.select_option(value)
        return True
    
    async def hover(self, index_or_id: int | str) -> bool:
        """Hover over an element"""
        locator = await self._get_locator(index_or_id)
        await locator.hover()
        return True
    
    async def get_text(self, index_or_id: int | str) -> str:
        """Get text content of an element"""
        locator = await self._get_locator(index_or_id)
        return await locator.text_content() or ''
    
    async def get_value(self, index_or_id: int | str) -> str:
        """Get value of an input element"""
        locator = await self._get_locator(index_or_id)
        return await locator.input_value()
    
    async def is_visible(self, index_or_id: int | str) -> bool:
        """Check if element is visible"""
        locator = await self._get_locator(index_or_id)
        return await locator.is_visible()
    
    async def scroll_to(self, index_or_id: int | str) -> bool:
        """Scroll element into view"""
        locator = await self._get_locator(index_or_id)
        await locator.scroll_into_view_if_needed()
        return True
    
    async def screenshot_element(self, index_or_id: int | str) -> bytes:
        """Take a screenshot of a specific element"""
        locator = await self._get_locator(index_or_id)
        return await locator.screenshot()
    
    async def clear_highlights(self):
        """Remove visual highlighting overlays"""
        await self.page.evaluate("""
            () => {
                document.querySelectorAll('[style*="pointer-events: none"]')
                    .forEach(el => el.remove());
            }
        """)
    
    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# ============================================================================
# LLM INTEGRATION EXAMPLE
# ============================================================================

class LLMWebAgent:
    """
    Example of integrating the WebAgentTool with an LLM.
    """
    
    def __init__(self, tool: WebAgentTool, llm_client):
        self.tool = tool
        self.llm = llm_client
    
    async def execute_task(self, task: str, max_steps: int = 10) -> str:
        """
        Execute a task using the LLM to decide actions.
        
        Args:
            task: Natural language description of the task
            max_steps: Maximum number of actions to take
        
        Returns:
            Result or status message
        """
        for step in range(max_steps):
            # Get current page state
            state = await self.tool.analyze_page(highlight=False)
            
            # Build prompt for LLM
            prompt = f"""
You are a web automation agent. Your task is: {task}

Current page: {state.url}
Title: {state.title}

Interactive elements on the page:
{state.indexed_text}

Based on this information, what action should you take?
Respond with a JSON object:
{{"action": "click|type|select|scroll|done|fail", "index": <element_index>, "text": "<text_if_typing>", "reason": "<brief explanation>"}}

If the task is complete, use action "done".
If the task cannot be completed, use action "fail".
"""
            
            # Get LLM response
            response = await self.llm.complete(prompt)
            action_data = json.loads(response)
            
            action = action_data['action']
            
            if action == 'done':
                return f"Task completed: {action_data.get('reason', 'Success')}"
            
            if action == 'fail':
                return f"Task failed: {action_data.get('reason', 'Unknown error')}"
            
            # Execute the action
            index = action_data.get('index')
            
            if action == 'click':
                await self.tool.click(index)
            elif action == 'type':
                await self.tool.type_text(index, action_data.get('text', ''))
            elif action == 'select':
                await self.tool.select_option(index, action_data.get('text', ''))
            elif action == 'scroll':
                await self.tool.scroll_to(index)
            
            # Wait for page to update
            await asyncio.sleep(0.5)
        
        return "Max steps reached without completing task"


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """Example usage of the WebAgentTool"""
    
    agent = WebAgentTool()
    await agent.init_browser(headless=False)
    
    try:
        # Navigate to a page
        await agent.navigate('https://example.com')
        
        # Analyze the page
        state = await agent.analyze_page(highlight=True, include_screenshot=True)
        
        print(f"URL: {state.url}")
        print(f"Title: {state.title}")
        print(f"Found {state.element_count} interactive elements")
        print("\nElements (indexed text format):")
        print(state.indexed_text)
        
        # Example: LLM would see the indexed_text and respond with an action
        # For demo, let's just click the first link if one exists
        if state.elements:
            links = [el for el in state.elements if el.tag == 'a']
            if links:
                print(f"\nClicking first link: {links[0].text}")
                await agent.click(links[0].index)
                
                # Re-analyze after action
                new_state = await agent.analyze_page()
                print(f"Now on: {new_state.url}")
        
        # Keep browser open for inspection
        await asyncio.sleep(5)
        
    finally:
        await agent.close()


if __name__ == '__main__':
    asyncio.run(main())
```

---

## Output Formats Comparison

### Format A: Indexed Text (Recommended for LLMs)
Token-efficient, easy to parse. Used by browser-use.

```
[0] <button>Login</button>
[1] <input type="text" placeholder="Username">
[2] <input type="password" placeholder="Password">
[3] <a href="/forgot">Forgot password?</a>
[4] <button>Create account</button>
```

**Pros:** Minimal tokens, clear indices, familiar HTML-like syntax
**Cons:** Loses some structural context

### Format B: Simplified HTML (For XPath/CSS generation)
Preserves structure, includes stable IDs.

```html
<form>
  <button data-element-id="elem-a1b2c3">Login</button>
  <input data-element-id="elem-d4e5f6" type="text" placeholder="Username">
  <input data-element-id="elem-g7h8i9" type="password" placeholder="Password">
  <a data-element-id="elem-j0k1l2" href="/forgot">Forgot password?</a>
</form>
```

**Pros:** Preserves structure, stable IDs for reference
**Cons:** More tokens, may include irrelevant structure

### Format C: Structured JSON (For programmatic use)
Complete metadata for each element.

```json
{
  "elements": [
    {
      "index": 0,
      "elementId": "elem-a1b2c3",
      "tag": "button",
      "text": "Login",
      "accessibleName": "Login",
      "locators": {
        "primary": "[data-element-id=\"elem-a1b2c3\"]",
        "xpath": "//form/button[1]"
      },
      "bbox": {"x": 100, "y": 200, "width": 80, "height": 40}
    }
  ]
}
```

**Pros:** Complete information, easy to process
**Cons:** Verbose, high token count

---

## Comparison with Browser-Use

| Feature | This Design | Browser-Use |
|---------|-------------|-------------|
| **Element ID Attribute** | `data-element-id` | `browser-user-highlight-id` |
| **ID Format** | Hash-based (`elem-a1b2c3`) | Sequential numeric |
| **Primary Locator** | Injected attribute | XPath + CSS fallback |
| **Visual Highlighting** | Optional | Built-in |
| **LLM Output Format** | Indexed text + HTML + JSON | Indexed text |
| **Fallback Strategies** | 6 levels | 2-3 levels |
| **Shadow DOM Support** | Yes | Yes |
| **iFrame Support** | Yes | Yes |
| **Viewport Expansion** | Configurable | Configurable |

---

## Key Design Decisions

### 1. Dual Identification System
- **Numeric index**: For LLM communication (token-efficient)
- **Element ID**: For stable references (survives minor DOM changes)

### 2. Priority Locator Strategy
1. `data-element-id` - Injected, most stable
2. `data-testid` - Developer-provided, if exists
3. `#id` - Native HTML id
4. Role + accessible name - Semantic, recommended by Playwright
5. XPath - Structural fallback
6. Text content - Last resort

### 3. Visual Highlighting
- Optional overlays with numeric labels
- Useful for debugging and multimodal models
- Can be toggled on/off
- Removed before action execution

### 4. Output Format Selection
- **indexed_text**: Default for LLMs (lowest tokens)
- **simplified_html**: For tools needing structure
- **JSON**: For programmatic processing

---

## References

- **Browser-Use**: https://github.com/browser-use/browser-use
- **Playwright Locators**: https://playwright.dev/docs/locators
- **WebArena**: Accessibility tree approach
- **Mind2Web**: Two-stage element filtering
- **XPath Agent**: XPath generation with cue text anchoring
- **Prune4Web**: Programmatic element filtering
