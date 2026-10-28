"""Vercel entrypoint for PALATE's health endpoint."""

from app import PalateHandler, configure

configure()


class handler(PalateHandler):
    """Vercel's Python runtime requires a declared handler class."""
