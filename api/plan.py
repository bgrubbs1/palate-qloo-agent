"""Vercel entrypoint for PALATE's planning endpoint."""

from app import PalateHandler, configure

configure()


class handler(PalateHandler):
    """Vercel's Python runtime requires a declared handler class."""
