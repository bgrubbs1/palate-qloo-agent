"""Vercel entrypoint for PALATE's health endpoint."""

from app import PalateHandler, configure

configure()
handler = PalateHandler
