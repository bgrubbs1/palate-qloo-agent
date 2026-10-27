"""Command-line front end: run the PALATE agent in a terminal.

    python3 -m palate.cli --city "New York" --mood "cozy but a little weird" \
        --love "Kamasi Washington" --love "Everything Everywhere All at Once"

Add ``--json`` for the full machine-readable run (same payload as the web API).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import APP_NAME, APP_TAGLINE, __version__
from .agent import Concierge, InvalidRequest
from .qloo import MODE_MOCK, QlooConfigError, QlooError, create_client

PHASE_GLYPH = {
    "plan": "◈",
    "resolve": "⌕",
    "query": "◇",
    "critique": "⚖",
    "revise": "↻",
    "recommend": "★",
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="palate",
        description="%s — %s" % (APP_NAME, APP_TAGLINE),
    )
    parser.add_argument("--city", default="New York", help="city for the evening (default: New York)")
    parser.add_argument("--mood", default="cozy but a little weird", help="free-text mood")
    parser.add_argument(
        "--love",
        action="append",
        default=[],
        help="an artist, film, show, book or place you love (repeatable; becomes a Qloo signal)",
    )
    parser.add_argument("--mode", choices=("auto", "mock", "live"), default="auto", help="data source (default: auto)")
    parser.add_argument("--json", action="store_true", help="print the full JSON response instead of the digest")
    parser.add_argument("--quiet-trace", action="store_true", help="hide the agent trace")
    parser.add_argument("--version", action="version", version="%s %s" % (APP_NAME, __version__))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        client, info = create_client(args.mode)
    except QlooConfigError as exc:
        print("config error: %s" % exc, file=sys.stderr)
        return 2

    request = {"city": args.city, "mood": args.mood, "loves": args.love}
    try:
        result = Concierge(client).run(request)
    except InvalidRequest as exc:
        print("invalid request: %s" % exc, file=sys.stderr)
        return 2
    except QlooError as exc:
        print("Qloo error: %s" % exc, file=sys.stderr)
        return 1

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    _print_digest(result, info, show_trace=not args.quiet_trace)
    return 0


def _print_digest(result, info, show_trace=True):
    line = "─" * 74
    print(line)
    print("  %s %s" % (APP_NAME, __version__))
    print("  %s" % APP_TAGLINE)
    print("  data: %s   (%s)" % (result["meta"]["data_source"], result["meta"]["base_url"]))
    print(line)
    if result["mode"] == MODE_MOCK:
        print("  NOTE: running on the bundled synthetic taste graph — NOT live Qloo data.")
        print("        Set QLOO_API_KEY to switch to the real API.\n")

    if show_trace:
        print("AGENT TRACE")
        for event in result["trace"]:
            glyph = PHASE_GLYPH.get(event["phase"], "•")
            print("  %s %-9s %s" % (glyph, event["phase"].upper(), event["title"]))
            print("    %s" % event["detail"])
        print()

    print("YOUR NIGHT — %s" % result["summary"]["headline"])
    for item in result["itinerary"]:
        entity = item.get("entity")
        if not entity:
            print("\n  %s  %-9s (no confident pick — left open)" % (item["time"], item["label"].upper()))
            continue
        print("\n  %s  %-9s %s  [%s confidence]" % (item["time"], item["label"].upper(), entity["name"], item["confidence"]))
        if entity.get("tags"):
            print("             tags: %s" % ", ".join(entity["tags"][:5]))
        print("             %s" % item["why"])

    summary = result["summary"]
    print("\n%s" % line)
    print(
        "  %d/%d slots filled · %d Qloo call%s · %d self-correction%s · confidence: %s"
        % (
            summary["slots_filled"],
            summary["slots_total"],
            summary["qloo_calls"],
            "" if summary["qloo_calls"] == 1 else "s",
            summary["revisions"],
            "" if summary["revisions"] == 1 else "s",
            summary["confidence"],
        )
    )
    if summary["taste_threads"]:
        print("  taste threads: %s" % ", ".join(summary["taste_threads"][:6]))
    print("  generated in %d ms" % result["meta"]["duration_ms"])
    print(line)


if __name__ == "__main__":
    sys.exit(main())
