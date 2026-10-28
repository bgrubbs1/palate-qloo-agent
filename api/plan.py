"""Vercel entrypoint for PALATE's planning endpoint."""

from app import PalateHandler, configure

configure()
handler = PalateHandler
