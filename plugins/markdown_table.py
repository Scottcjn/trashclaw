"""
TrashClaw Plugin — Markdown Table Formatter

Converts CSV data or raw text into clean markdown tables.
Useful for formatting output from other tools into readable reports.
"""

TOOL_DEF = {
    "name": "markdown_table",
    "description": "Convert CSV text or structured data into a formatted markdown table. Supports alignment and header detection.",
    "parameters": {
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "description": "CSV or tab-separated data. First row treated as headers."
            },
            "delimiter": {
                "type": "string",
                "description": "Field delimiter (default: auto-detect comma or tab)"
            },
            "align": {
                "type": "string",
                "description": "Column alignment: 'left', 'right', 'center' (default: left)"
            }
        },
        "required": ["data"]
    }
}


def run(data: str = "", delimiter: str = "", align: str = "left", **kwargs) -> str:
    """Convert structured text data into a markdown table."""
    try:
        lines = [l.strip() for l in data.strip().split("\n") if l.strip()]
        if not lines:
            return "Error: No data provided"

        # Auto-detect delimiter
        if not delimiter:
            if "\t" in lines[0]:
                delimiter = "\t"
            elif "," in lines[0]:
                delimiter = ","
            elif "|" in lines[0]:
                delimiter = "|"
            else:
                delimiter = ","

        rows = []
        for line in lines:
            cells = [c.strip() for c in line.split(delimiter)]
            rows.append(cells)

        if not rows:
            return "Error: Could not parse data"

        # Normalize column count
        max_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < max_cols:
                r.append("")

        # Calculate column widths
        widths = [max(len(r[i]) for r in rows) for i in range(max_cols)]
        widths = [max(w, 3) for w in widths]  # minimum 3 chars

        # Build alignment markers
        if align == "right":
            sep = ["-" * (w - 1) + ":" for w in widths]
        elif align == "center":
            sep = [":" + "-" * (w - 2) + ":" for w in widths]
        else:
            sep = ["-" * w for w in widths]

        # Format header
        header = "| " + " | ".join(rows[0][i].ljust(widths[i]) for i in range(max_cols)) + " |"
        separator = "| " + " | ".join(sep) + " |"

        # Format data rows
        table_rows = []
        for row in rows[1:]:
            formatted = "| " + " | ".join(row[i].ljust(widths[i]) for i in range(max_cols)) + " |"
            table_rows.append(formatted)

        result = [header, separator] + table_rows
        return "\n".join(result)
    except Exception as e:
        return f"Table formatting failed: {e}"
