#!/usr/bin/env python

"""
Usage:

  ./view_docstring.py filename

Aim:

View the contents of a docstring file (a .txt file created by
extract_docstrings.py and then possibly manually edited), as
an ahelp file.

The filename must be "symbol.txt", where symbol is the name of
the Sherpa symbol.

"""

import os
import tempfile

from parsers.sherpa import doc_to_rst, sym_to_sig, unwanted, find_synonyms
from parsers.rst import parse_restructured
from parsers.docutils import convert_docutils
from parsers.ahelp import find_metadata

from helpers import save_doc


def convert_and_view(infile):
    """Convert a docstring file to ahelp format and view.

    Parameters
    ----------
    infile : str
        The name of the file to convert.

    """

    basename = os.path.basename(infile)

    # Just look for the first "token"
    name = basename.split('.')[0]

    sig, sym = sym_to_sig(name, sym=None)

    if unwanted(name, sym):
        print("Note: {} has been marked 'unwanted' by Doug".format(name))
        return

    synonyms, _ = find_synonyms()
    if name in synonyms:
        print("Note: {} is an alias for {}".format(name, synonyms[name]))
        return

    cts = open(infile, 'r').read()

    try:
        ahelp = find_metadata(name)
    except Exception as exc:
        print("SKIPPING AHELP METADATA: {}".format(exc))
        ahelp = None

    sherpa_doc = doc_to_rst(cts)
    rst_doc = parse_restructured(name, sherpa_doc)
    xmldoc = convert_docutils(name, rst_doc, sig,
                              symbol=sym,
                              metadata=ahelp)

    outfile = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
    save_doc(outfile.name, xmldoc)

    os.system("ahelp -f {}".format(outfile.name))

    os.unlink(outfile.name)


help_str = """View a docstring as an ahelp file."""

if __name__ == "__main__":

    import argparse
    import sys

    parser = argparse.ArgumentParser(description=help_str,
                                     prog=sys.argv[0])

    parser.add_argument("infile",
                        help="The docstring file to convert")

    args = parser.parse_args(sys.argv[1:])
    convert_and_view(args.infile)
