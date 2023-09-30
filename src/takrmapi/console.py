"""CLI entrypoints for product integration api"""
import logging
import json

import click
from libadvian.logging import init_logging

from takrmapi import __version__
from takrmapi.app import get_app


LOGGER = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.pass_context
@click.option("-l", "--loglevel", help="Python log level, 10=DEBUG, 20=INFO, 30=WARNING, 40=CRITICAL", default=30)
@click.option("-v", "--verbose", count=True, help="Shorthand for info/debug loglevel (-v/-vv)")
def cli_group(ctx: click.Context, loglevel: int, verbose: int) -> None:
    """CLI helpers for developers"""
    if verbose == 1:
        loglevel = 20
    if verbose >= 2:
        loglevel = 10

    LOGGER.setLevel(loglevel)
    ctx.ensure_object(dict)


@cli_group.command(name="openapi")
@click.pass_context
def dump_openapi(ctx: click.Context) -> None:
    """
    Dump autogenerate openapi spec as JSON
    """
    app = get_app()
    click.echo(json.dumps(app.openapi()))
    ctx.exit(0)


def takrmapi_cli() -> None:
    """rmfpapi"""
    init_logging(logging.WARNING)
    cli_group()  # pylint: disable=no-value-for-parameter
