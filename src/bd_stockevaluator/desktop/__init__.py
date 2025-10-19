"""
Desktop-oriented presentation layers for BD Finance.

Modules in this package provide Streamlit wrappers that sit on top of the
core analytics engine without modifying existing Flask routes.
"""

from .overview import main, render_dashboard

__all__ = ["main", "render_dashboard"]
