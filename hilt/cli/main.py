"""Command line entry point for the HILT toolkit."""

from __future__ import annotations

import click


@click.group()
@click.version_option()
def cli() -> None:
    """HILT CLI - Human-IA Log Trace toolkit."""
