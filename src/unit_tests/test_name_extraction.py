"""
Unit tests for name extraction service.

Tests H1, H2, and frontmatter extraction from markdown content.
"""
import pytest
from wiki.services.name_extraction import NameExtractionService


class TestNameExtractionService:
    """Test name extraction from markdown content."""
    
    def test_extract_h1_simple(self):
        """Extract simple H1 header."""
        content = "# My Title\n\nSome content here."
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "My Title"
    
    def test_extract_h1_with_multiple_headers(self):
        """Extract first H1 when multiple headers exist."""
        content = "# First Title\n\n## Subtitle\n\n# Second Title"
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "First Title"
    
    def test_extract_h1_not_h2(self):
        """H1 extraction should not match H2 headers."""
        content = "## Not H1\n\n# This is H1"
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "This is H1"
    
    def test_extract_h1_skip_code_blocks(self):
        """H1 extraction should skip headers in code blocks."""
        content = """```markdown
# This is in code block
```

# Real Header"""
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "Real Header"
    
    def test_extract_h1_skip_html_comments(self):
        """H1 extraction should skip headers in HTML comments."""
        content = """<!-- # This is in comment -->

# Real Header"""
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "Real Header"
    
    def test_extract_h1_not_found(self):
        """Return None when no H1 header exists."""
        content = "## Only H2 here\n\nNo H1 at all."
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result is None
    
    def test_extract_h2_simple(self):
        """Extract simple H2 header."""
        content = "## My Subtitle\n\nSome content here."
        result = NameExtractionService.extract_from_markdown(content, 'first_h2')
        assert result == "My Subtitle"
    
    def test_extract_h2_with_h1(self):
        """Extract first H2 even when H1 exists."""
        content = "# Title\n\n## First Subtitle\n\n## Second Subtitle"
        result = NameExtractionService.extract_from_markdown(content, 'first_h2')
        assert result == "First Subtitle"
    
    def test_extract_h2_not_h3(self):
        """H2 extraction should not match H3 headers."""
        content = "### Not H2\n\n## This is H2"
        result = NameExtractionService.extract_from_markdown(content, 'first_h2')
        assert result == "This is H2"
    
    def test_extract_h2_skip_code_blocks(self):
        """H2 extraction should skip headers in code blocks."""
        content = """```
## In code block
```

## Real H2"""
        result = NameExtractionService.extract_from_markdown(content, 'first_h2')
        assert result == "Real H2"
    
    def test_extract_h2_not_found(self):
        """Return None when no H2 header exists."""
        content = "# Only H1 here\n\nNo H2 at all."
        result = NameExtractionService.extract_from_markdown(content, 'first_h2')
        assert result is None
    
    def test_extract_frontmatter_simple(self):
        """Extract title from YAML frontmatter."""
        content = """---
title: My Document Title
author: John Doe
---

# Content starts here"""
        result = NameExtractionService.extract_from_markdown(content, 'title_frontmatter')
        assert result == "My Document Title"
    
    def test_extract_frontmatter_no_title(self):
        """Return None when frontmatter has no title field."""
        content = """---
author: John Doe
date: 2024-01-01
---

# Content"""
        result = NameExtractionService.extract_from_markdown(content, 'title_frontmatter')
        assert result is None
    
    def test_extract_frontmatter_not_found(self):
        """Return None when no frontmatter exists."""
        content = "# Just a regular markdown file"
        result = NameExtractionService.extract_from_markdown(content, 'title_frontmatter')
        assert result is None
    
    def test_extract_frontmatter_invalid_yaml(self):
        """Return None when frontmatter YAML is invalid."""
        content = """---
title: Unclosed quote "
invalid: yaml: here
---

# Content"""
        result = NameExtractionService.extract_from_markdown(content, 'title_frontmatter')
        assert result is None
    
    def test_extract_name_filename(self):
        """Extract name using filename method."""
        result = NameExtractionService.extract_name('path/to/myfile.md', 'content', 'filename')
        assert result == "myfile"
    
    def test_extract_name_filename_no_extension(self):
        """Extract name from filename without extension."""
        result = NameExtractionService.extract_name('path/to/README', 'content', 'filename')
        assert result == "README"
    
    def test_extract_name_markdown_h1(self):
        """Extract name from markdown file with H1."""
        content = "# Test Title\n\nContent"
        result = NameExtractionService.extract_name('test.md', content, 'first_h1')
        assert result == "Test Title"
    
    def test_extract_name_markdown_h2(self):
        """Extract name from markdown file with H2."""
        content = "## Test Subtitle\n\nContent"
        result = NameExtractionService.extract_name('test.md', content, 'first_h2')
        assert result == "Test Subtitle"
    
    def test_extract_name_non_markdown_fallback(self):
        """Non-markdown files should fall back to filename."""
        content = "Some content"
        result = NameExtractionService.extract_name('test.txt', content, 'first_h1')
        assert result == "test"
    
    def test_extract_name_markdown_no_header_returns_none(self):
        """Markdown without header should return None (fallback handled by model)."""
        content = "Just plain text, no headers"
        result = NameExtractionService.extract_name('test.md', content, 'first_h1')
        assert result is None
    
    def test_extract_h1_with_whitespace(self):
        """Extract H1 with extra whitespace."""
        content = "#   Title with spaces   \n\nContent"
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "Title with spaces"
    
    def test_extract_h1_multiline_content(self):
        """Extract H1 from content with multiple lines."""
        content = """Some preamble text

# Main Title

More content here
## Subtitle"""
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "Main Title"
    
    def test_extract_with_special_characters(self):
        """Extract headers with special characters."""
        content = "# Title with `code` and **bold**"
        result = NameExtractionService.extract_from_markdown(content, 'first_h1')
        assert result == "Title with `code` and **bold**"
