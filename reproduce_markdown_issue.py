import markdown
import os
import sys

# Mocking the context if needed, but here we just test the markdown conversion logic
content = """
# Test Title
This is **bold** and *italic*.

## List
- Item 1
- Item 2

| Table | Header |
|-------|--------|
| Cell  | Data   |

```python
print("Hello")
```
"""

def test_conversion(text):
    print(f"--- Original Markdown ---\n{text}")
    # This is the exact line from tools/create_pdf_tool.py:248
    html_body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc'])
    print(f"\n--- Generated HTML ---\n{html_body}")
    return html_body

if __name__ == "__main__":
    html = test_conversion(content)
    if "<h1>" in html and "<strong>" in html:
        print("\n✅ Markdown conversion seems to work in this environment.")
    else:
        print("\n❌ Markdown conversion FAILED to produce expected HTML tags.")
