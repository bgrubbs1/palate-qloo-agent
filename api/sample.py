"""Vercel entrypoint for PALATE's sample profiles endpoint."""

from app import PalateHandler, configure

configure()
handler = PalateHandler
