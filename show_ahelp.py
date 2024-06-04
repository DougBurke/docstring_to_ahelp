#!/usr/bin/env python

"""
Usage:

  ./show_ahelp.py symbol

Aim:

Create ahelp output based on sherpa documentation. A single-symbol
version of doc2ahelp.py with no output file.

The aim is to make it easy to see if changes to the code affects
the output for a symbol.

"""

import os
import tempfile

from xml.etree.ElementTree import dump

from sherpa.astro import ui

from parsers.sherpa import sym_to_sig, sym_to_rst, unwanted
from parsers.rst import parse_restructured
from parsers.docutils import convert_docutils


def convert_and_view(symbol: str) -> None:
    """Convert a symbol to an ahelp file.

    Parameters
    ----------
    symbol : str
        The name of the symbol to convert.

    """

    sym = getattr(ui, symbol, None)
    if sym is None:
        raise ValueError(f"Unknown symbol <{symbol}>")

    if unwanted(symbol, sym):
        raise ValueError(f"Apparently <{symbol}> is unwanted")

    sig, _ = sym_to_sig(symbol, sym)

    sherpa_doc = sym_to_rst(symbol, sym)
    if sherpa_doc is None:
        raise ValueError(f"symbol <{symbol}> has no documentation!")

    rst_doc = parse_restructured(symbol, sherpa_doc)
    doc = convert_docutils(symbol, rst_doc, sig, dtd='ahelp',
                           symbol=sym, metadata=None,
                           synonyms=None)

    dump(doc)


help_str = """Dump the converted ahelp for a symbol."""

if __name__ == "__main__":

    import argparse
    import sys

    parser = argparse.ArgumentParser(description=help_str,
                                     prog=sys.argv[0])

    parser.add_argument("symbol",
                        help="The symbol to convert")

    args = parser.parse_args(sys.argv[1:])
    convert_and_view(args.symbol)
