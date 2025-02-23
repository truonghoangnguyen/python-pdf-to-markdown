import fitz  # PyMuPDF
from collections import Counter

def get_body_font_size(doc):
    """Determine the most common font size (assumed to be body text)."""
    sizes = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        sizes.append(span["size"])
    # Find the most common size
    counter = Counter(sizes)
    body_size = counter.most_common(1)[0][0]
    return body_size

def get_heading_levels(doc, body_size):
    """Map font sizes larger than body size to heading levels."""
    heading_sizes = set()
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > body_size:
                            heading_sizes.add(span["size"])
    # Sort sizes in descending order and assign levels (largest = 1, etc.)
    heading_sizes = sorted(heading_sizes, reverse=True)
    level_map = {size: i + 1 for i, size in enumerate(heading_sizes)}
    return level_map

def process_span(span, level_map):
    """Convert a text span to Markdown, detecting headings and formatting."""
    text = span["text"].strip()
    if not text:
        return ""

    size = span["size"]
    flags = span["flags"]

    # Check if it's a heading
    if size in level_map:
        level = level_map[size]
        md_text = "#" * level + " " + text
    else:
        md_text = text
        # Apply bold and italic formatting
        is_italic = flags & 2  # Bit 2 for italic
        is_bold = flags & 16   # Bit 4 for bold
        if is_bold and is_italic:
            md_text = "***" + md_text + "***"
        elif is_bold:
            md_text = "**" + md_text + "**"
        elif is_italic:
            md_text = "*" + md_text + "*"

    return md_text

def process_block(block, level_map):
    """Convert a text block to Markdown, joining lines into paragraphs."""
    if block["type"] == 0:  # Text block
        lines = []
        for line in block["lines"]:
            spans = [process_span(span, level_map) for span in line["spans"]]
            spans = [s for s in spans if s]  # Remove empty spans
            if spans:
                line_text = " ".join(spans)
                lines.append(line_text)
        if lines:
            block_text = "\n".join(lines)
            return block_text
    return ""

def main():
    doc = fitz.open("/path/to.pdf")  # Replace with your PDF path
    toc = doc.get_toc()

    if not toc:
        print("No table of contents found. Please clarify if a fallback method is needed.")
        doc.close()
        return

    # Extract chapter ranges from TOC (level 1 entries)
    chapters = []
    for i, entry in enumerate(toc):
        if entry[0] == 3:  # Level 3 (individual chapters/suttas)
            start_page = entry[2] - 1  # Convert to 0-based indexing
            title = entry[1]
            if i < len(toc) - 1:
                next_entry = toc[i + 1]
                end_page = next_entry[2] - 2  # Page before the next entry
            else:
                end_page = doc.page_count - 1
            chapters.append((start_page, end_page, title))
    #print(chapters)
    #return
    # Determine body text size and heading levels
    body_size = get_body_font_size(doc)
    level_map = get_heading_levels(doc, body_size)

    # Process each chapter
    for idx, (start_page, end_page, title) in enumerate(chapters, 1):
        md_text = []

        for page_num in range(start_page, end_page + 1):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]

            # On the first page of the chapter, add the chapter title
            if page_num == start_page:
                md_text.append("# " + title)
                md_text.append("")  # Empty line for spacing

            # Process remaining blocks
            for block in blocks:
                block_text = process_block(block, level_map)
                if block_text:
                    md_text.append(block_text)
                    md_text.append("")  # Empty line for spacing

        # Combine all Markdown text for the chapter
        chapter_md = "\n".join(md_text).strip()

        # Save to file
        filename = f"chapter_{idx}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(chapter_md)
        print(f"Saved chapter {idx} to {filename}")

    doc.close()

main()
