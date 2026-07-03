"""The ``lokf`` command-line interface.

Subcommands are registered in :data:`SUBCOMMANDS` (name -> parser
configurator) so future commands slot in beside ``propose``::

    lokf propose examples/acme-knowledge              # dry-run table
    lokf propose examples/acme-knowledge --json       # machine-readable
    lokf propose examples/acme-knowledge --apply      # write frontmatter
"""
from __future__ import annotations

import argparse
import json
import sys

from lokf.model import load_bundle
from lokf.propose import apply, propose
from lokf.schema import vocabulary


def cmd_propose(args: argparse.Namespace) -> int:
    """Run the link-semantics proposer over a bundle directory."""
    bundle = load_bundle(args.bundle_dir)
    if not bundle.concepts:
        print(f"no concepts found in {args.bundle_dir}", file=sys.stderr)
        return 1
    proposals = [
        p
        for p in propose(bundle, vocabulary())
        if p.confidence >= args.min_confidence
    ]
    if args.json:
        rows = [
            {
                "source": p.source.concept_id,
                "link_text": p.link.text,
                "target": bundle.iri(p.link.target),
                "predicate": p.relation.name,
                "curie": p.relation.curie,
                "confidence": round(p.confidence, 2),
                "rationale": p.rationale,
            }
            for p in proposals
        ]
        print(json.dumps(rows, indent=2))
        return 0
    if not proposals:
        print("no proposals.")
        return 0
    _print_table(proposals)
    if args.apply:
        applied = apply(proposals, min_confidence=args.min_confidence)
        print()
        for p in applied:
            print(
                f"wrote {p.relation.name} -> {bundle.iri(p.link.target)} "
                f"in {p.source.path}"
            )
        print(f"applied {len(applied)} of {len(proposals)} proposal(s).")
    return 0


def _print_table(proposals) -> None:
    """Print proposals as an aligned dry-run table."""
    header = ("SOURCE", "LINK", "PREDICATE", "CONF", "RATIONALE")
    rows = [
        (
            p.source.concept_id,
            p.link.text,
            p.relation.curie,
            f"{p.confidence:.2f}",
            p.rationale,
        )
        for p in proposals
    ]
    widths = [max(len(r[i]) for r in (header, *rows)) for i in range(4)]
    for row in (header, *rows):
        cells = [row[i].ljust(widths[i]) for i in range(4)]
        print("  ".join([*cells, row[4]]))


def _add_propose(subparsers) -> None:
    p = subparsers.add_parser(
        "propose",
        help="propose typed relations from markdown links in concept bodies",
    )
    p.add_argument("bundle_dir", help="path to a LOKF bundle directory")
    p.add_argument(
        "--apply",
        action="store_true",
        help="write accepted proposals into concept frontmatter",
    )
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        metavar="F",
        help="drop proposals below this confidence (default: 0.0)",
    )
    p.add_argument(
        "--json", action="store_true", help="emit proposals as JSON instead of a table"
    )
    p.set_defaults(func=cmd_propose)


SUBCOMMANDS = {"propose": _add_propose}


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``lokf`` console script."""
    parser = argparse.ArgumentParser(prog="lokf", description="LOKF toolkit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for add in SUBCOMMANDS.values():
        add(subparsers)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
