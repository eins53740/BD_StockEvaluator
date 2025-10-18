package com.bdfinance.stockevaluator.util

private const val MERMAID_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { margin: 0; background-color: transparent; }
            .mermaid { width: 100%%; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    </head>
    <body>
        <div class="mermaid">%s</div>
        <script>
            mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });
        </script>
    </body>
    </html>
"""

fun flowchartHtml(definition: String?): String? =
    definition?.let { MERMAID_TEMPLATE.format(it) }
