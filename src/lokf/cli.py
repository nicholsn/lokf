"""The ``lokf`` command-line interface (Typer).

    lokf convert path/to/concept.md --format ttl      # markdown -> RDF
    lokf query examples/acme-knowledge "SELECT ..."   # SPARQL over a bundle
    lokf serve examples/acme-knowledge                # local SPARQL endpoint + viz
    lokf propose examples/acme-knowledge --apply      # typed relations from links
    lokf vocab                                        # the relation vocabulary
    lokf skills                                        # bundled agent skills
    lokf mcp                                           # run the MCP server
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="lokf",
    help="LOKF toolkit — author, convert, query, serve, and automate "
    "linked-open knowledge bundles.",
    no_args_is_help=True,
    add_completion=False,
)


def _err(message: str) -> None:
    typer.echo(message, err=True)


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------
@app.command()
def convert(
    source: Path = typer.Argument(
        ..., exists=True, help="A concept .md file or a bundle directory."
    ),
    format: str = typer.Option(
        "ttl", "--format", "-f", help="ttl | nt | jsonld | xml | n3 | trig."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write to this file instead of stdout."
    ),
) -> None:
    """Convert markdown (a concept or whole bundle) to RDF."""
    from lokf import rdf

    try:
        data = rdf.serialize(source, format)
    except ValueError as exc:
        _err(str(exc))
        raise typer.Exit(2)
    except OSError as exc:
        _err(f"could not read {source}: {exc}")
        raise typer.Exit(1)
    if output is not None:
        output.write_text(data, encoding="utf-8")
        typer.echo(f"wrote {output}")
    else:
        typer.echo(data, nl=False)


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------
@app.command()
def tables(
    source: Path = typer.Argument(
        ..., exists=True, help="A bundle directory to project to tables."
    ),
    format: str = typer.Option(
        "csv", "--format", "-f",
        help="csv | parquet | sqlite | bigquery | athena",
    ),
    output: Path = typer.Option(
        Path("lokf-tables"), "--output", "-o",
        help="Output directory (or a .db path for sqlite).",
    ),
    engine: str = typer.Option("pandas", help="DataFrame engine: pandas | polars."),
    location: str = typer.Option(
        "gs://your-bucket/lokf", "--location",
        help="Parquet location referenced by the bigquery/athena DDL.",
    ),
) -> None:
    """Project a bundle to linked tables: one per concept type + a relations edge table.

    csv/parquet/sqlite write the data; bigquery/athena write the Parquet and
    print CREATE EXTERNAL TABLE DDL that registers it as a lakehouse.
    """
    from lokf import tables as t
    from lokf.model import load_bundle

    try:
        frames = t.to_frames(load_bundle(source), engine=engine)
    except ModuleNotFoundError as exc:
        _err(str(exc))
        raise typer.Exit(1)

    if format == "csv":
        typer.echo(f"wrote {t.write_csv(frames, output)}/")
    elif format == "parquet":
        typer.echo(f"wrote {t.write_parquet(frames, output)}/")
    elif format == "sqlite":
        typer.echo(f"wrote {t.to_sqlite(frames, output)}")
    elif format in ("bigquery", "athena"):
        t.write_parquet(frames, output)
        _err(f"# wrote Parquet to {output}/ ; register it with the DDL below")
        typer.echo(t.external_table_ddl(frames, format, location))
    else:
        _err(f"unknown format: {format} (csv | parquet | sqlite | bigquery | athena)")
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------
@app.command()
def query(
    source: Path = typer.Argument(
        ..., exists=True, help="A bundle directory or concept file to load."
    ),
    sparql: str = typer.Argument(..., help="A SPARQL query (schema prefixes preset)."),
    format: str = typer.Option(
        "table", "--format", "-f", help="table | json | csv | tsv | ttl (CONSTRUCT)."
    ),
) -> None:
    """Run SPARQL over a knowledge base loaded into an in-memory store."""
    from lokf.store import GraphStore, query_form

    store = GraphStore.from_bundle(source)
    form = query_form(sparql)
    try:
        if form in ("construct", "describe"):
            fmt = "ttl" if format == "table" else format
            typer.echo(store.construct(sparql, fmt=fmt), nl=False)
        elif format == "table":
            _print_rows(store.select(sparql))
        else:
            typer.echo(store.serialize_results(sparql, format).decode("utf-8"), nl=False)
    except Exception as exc:  # noqa: BLE001 — surface SPARQL errors to the user
        _err(f"query failed: {exc}")
        raise typer.Exit(1)


def _print_rows(rows: list[dict]) -> None:
    if not rows:
        typer.echo("(no results)")
        return
    cols = list(dict.fromkeys(k for row in rows for k in row))
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    typer.echo("  ".join(c.ljust(widths[c]) for c in cols))
    for row in rows:
        typer.echo("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------
@app.command()
def serve(
    source: Path = typer.Argument(
        ..., exists=True, help="A bundle directory or concept file to publish."
    ),
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Publish a knowledge base locally: SPARQL endpoint + live graph viz."""
    from lokf.server import serve as run_server

    run_server(source, host=host, port=port)


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------
@app.command()
def propose(
    bundle_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="A LOKF bundle directory."
    ),
    apply_: bool = typer.Option(
        False, "--apply", help="Write accepted proposals into frontmatter."
    ),
    min_confidence: float = typer.Option(
        0.0, "--min-confidence", metavar="F", help="Drop proposals below this."
    ),
    json_: bool = typer.Option(
        False, "--json", help="Emit JSON instead of a table (composes with --apply)."
    ),
) -> None:
    """Propose typed relations from markdown links in concept bodies."""
    from lokf.model import load_bundle
    from lokf.propose import apply, proposal_row
    from lokf.propose import propose as propose_relations
    from lokf.schema import vocabulary

    bundle = load_bundle(bundle_dir)
    if not bundle.concepts:
        _err(f"no concepts found in {bundle_dir}")
        raise typer.Exit(1)
    proposals = [
        p
        for p in propose_relations(bundle, vocabulary())
        if p.confidence >= min_confidence
    ]
    applied: list = []
    if apply_:
        applied = apply(proposals, min_confidence=min_confidence)
    applied_ids = {id(p) for p in applied}

    if json_:
        ids = applied_ids if apply_ else None
        rows = [proposal_row(p, ids) for p in proposals]
        typer.echo(json.dumps(rows, indent=2))
        return

    if not proposals:
        typer.echo("no proposals.")
        return
    _print_proposals(proposals)
    if apply_:
        typer.echo("")
        for p in applied:
            typer.echo(f"wrote {p.relation.name} -> {p.target_iri} in {p.source.path}")
        typer.echo(f"applied {len(applied)} of {len(proposals)} proposal(s).")


def _print_proposals(proposals) -> None:
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
        typer.echo("  ".join([*cells, row[4]]))


# ---------------------------------------------------------------------------
# vocab
# ---------------------------------------------------------------------------
@app.command()
def vocab(
    json_: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Show the typed-relation vocabulary derived from the schema."""
    from lokf.schema import vocabulary

    v = vocabulary()
    relations = sorted(v.relation_types.values(), key=lambda r: r.name)
    if json_:
        typer.echo(json.dumps([r.as_row() for r in relations], indent=2))
        return
    name_w = max(len(r.name) for r in relations)
    curie_w = max(len(r.curie) for r in relations)
    for r in relations:
        key = "slot" if r.is_slot else "rel "
        typer.echo(
            f"{r.name.ljust(name_w)}  {key}  {r.curie.ljust(curie_w)}  {r.description}"
        )


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------
@app.command()
def skills(
    action: str = typer.Argument("list", help="list | path | install"),
    dest: Optional[Path] = typer.Option(
        None, "--dest", help="Target for `install` (default: .claude/skills)."
    ),
) -> None:
    """List, locate, or install the bundled agent skills."""
    from lokf import agentskills

    if action == "path":
        typer.echo(str(agentskills.skills_dir()))
    elif action == "list":
        for name, summary in agentskills.list_skills():
            typer.echo(f"{name}\t{summary}")
    elif action == "install":
        target = agentskills.install(dest)
        count = len(list(target.glob("*/SKILL.md")))
        typer.echo(f"installed {count} skills into {target}")
    else:
        _err(f"unknown action {action!r}; choose list | path | install")
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# mcp
# ---------------------------------------------------------------------------
@app.command()
def export(
    bundle_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="A LOKF bundle directory."
    ),
    out_dir: Path = typer.Option(
        ..., "--out-dir", "-d", help="Directory to write graph.json + datasets.jsonld."
    ),
    source_base: Optional[str] = typer.Option(
        None, "--source-base", help="URL prefix for a node's source file (graph meta)."
    ),
) -> None:
    """Export a bundle's graph + Dataset JSON-LD for a static site to consume.

    Writes ``graph.json`` (cytoscape.js elements, typed-relation edges, plus
    ``meta.source_base``) and ``datasets.jsonld`` (schema.org Dataset docs for
    Google Dataset Search). This is the data step behind the docs site.
    """
    from lokf.export import dataset_search_jsonld, to_cytoscape
    from lokf.model import load_bundle

    bundle = load_bundle(bundle_dir)
    graph = to_cytoscape(bundle)
    graph["meta"] = {"source_base": source_base} if source_base else {}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (out_dir / "datasets.jsonld").write_text(
        json.dumps(dataset_search_jsonld(bundle), indent=2), encoding="utf-8"
    )
    typer.echo(
        f"wrote {out_dir}/graph.json ({len(graph['nodes'])} nodes, "
        f"{len(graph['edges'])} edges) and {out_dir}/datasets.jsonld"
    )


@app.command()
def mcp() -> None:
    """Run the LOKF MCP server (stdio) so agents can drive the toolkit."""
    from lokf.mcp_server import main as run_mcp

    run_mcp()


def main(argv: list[str] | None = None) -> int:
    """Programmatic entry point (tests use ``typer.testing.CliRunner``).

    Runs the app in standalone mode so Typer converts ``typer.Exit`` and
    argument errors into ``SystemExit`` (with a printed message); the code is
    returned here so ``python -m lokf.cli`` and ``sys.exit(main())`` report
    failures correctly instead of always exiting 0.
    """
    try:
        app(args=argv, standalone_mode=True)
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)


if __name__ == "__main__":
    sys.exit(main())
