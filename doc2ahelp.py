#!/usr/bin/env python

"""
Usage:

  ./doc2ahelp.py outdir [names]
     --debug
     --sxml

Aim:

Extract the docstring information from Sherpa and create ahelp XML
files for these symbols (functions, objects that we treat as
strings/functions in Sherpa, meta data created from these symbols).

The --sxml flag means that the output will use the "SXML" DTD
instead of the AHELP one (at present this only changes the name of
the root element, so there is no attempt to take advantage of the
extra functionality provided by the SXML DTD).

The script requires that a CIAO installation has been initialized,
since it is used to access the Sherpa documentation from

   sherpa.astro.ui
   sherpa.stats
   sherpa.optmethods

The ahelp files in the CIAO documentation are used to create the
ahelp metadata.

The output is to outdir/<key>.xml where <key> is based on the
"ahelp key" (it should be the same but may be different).

The script will over-write any existing file.

TODO:
  - indicate new/missing files
  - create composite pages like 'ahelp models' 'ahelp xs'?

  - how to handle the known problem cases?

  - NEED TO ENSURE DO NOT OVERWRITE EXISTING AHELP FILES (THAT ARE
    NOT SHERPA)

"""

import os

from sherpa.astro import ui

from parsers.sherpa import sym_to_rst, sym_to_sig, unwanted, find_synonyms
from parsers.rst import parse_restructured
from parsers.docutils import convert_docutils
from parsers.ahelp import find_metadata

from helpers import save_doc


def process_symbol(name, sym, dtd='ahelp',
                   ahelp=None, synonyms=None, debug=False):

    sherpa_doc = sym_to_rst(name, sym)
    if sherpa_doc is None:
        print("  - has no doc")
        return None

    sig, _ = sym_to_sig(name, sym)

    if debug:
        print("---- formats")
        print("-- Sherpa:\n{}".format(sherpa_doc))

    rst_doc = parse_restructured(name, sherpa_doc)
    if debug:
        print("-- RestructuredText:\n{}".format(rst_doc))

    doc = convert_docutils(name, rst_doc, sig, dtd=dtd,
                           symbol=sym, metadata=ahelp,
                           synonyms=synonyms)
    return doc


def convert(outdir, dtd='ahelp', debug=False, restrict=None):
    """Convert the symbols.

    Parameters
    ----------
    outdir : string
        The output directory, which must already exist.
    dtd : {'ahelp', 'sxml'}, optional
        The DTD to use for the output
    debug : optional, boool
        If True then print out parsed versions of the symbols
        (expected to be used when restrict is not None but this
        is not enforced).
    restrict : optional, None or list of str
        The set of symbols to use (if not all).
    """

    if not os.path.isdir(outdir):
        sys.stderr.write("ERROR: outdir={} does not exist\n".format(outdir))
        sys.exit(1)

    if dtd not in ['ahelp', 'sxml']:
        raise ValueError("Invalid dtd argument")

    synonyms, originals = find_synonyms()

    # Restrict the symbols that get processed
    #
    names = sorted(list(ui.__all__))
    nproc = 0
    for name in names:

        if restrict is not None and name not in restrict:
            continue

        print("# {}".format(name))

        sym = getattr(ui, name)
        if unwanted(name, sym):
            print(" - skipping as unwanted")
            continue

        if name in synonyms:
            print(" - skipping as a synonym for {}".format(synonyms[name]))
            continue

        try:
            syn_names = originals[name]
        except KeyError:
            syn_names = None

        try:
            ahelp = find_metadata(name, synonyms=syn_names)
        except ValueError as exc:
            print(" - ahelp metadata skipped as {}".format(exc))
            ahelp = None

        xml = process_symbol(name, sym, dtd=dtd, ahelp=ahelp,
                             synonyms=syn_names,
                             debug=debug)
        if xml is None:
            continue

        outfile = os.path.join(outdir, '{}.xml'.format(name))
        save_doc(outfile, xml)
        print("Created: {}".format(outfile))
        nproc += 1

    nskip = len(names) - nproc
    print("\nProcessed {} files, skipped {}.".format(nproc, nskip))

    """

    # extra symbols
    #   statistics
    #   optimisers
    #
    # Be very-restrictive on the accepted symbols
    #
    statnames = ui.list_stats()
    statnames.remove('userstat')  # explicitly remove
    for name in dir(sherpa.stats):
        if not name[0].isupper():
            # this check is only realy needed for methods but include it
            continue

        lname = name.lower()
        if lname not in statnames:
            continue

        symbol = getattr(sherpa.stats, name)
        doit(lname, symbol)

    optnames = ui.list_methods()
    for name in dir(sherpa.optmethods):
        if not name[0].isupper():
            continue

        lname = name.lower()
        if lname not in optnames:
            continue

        symbol = getattr(sherpa.optmethods, name)
        doit(lname, symbol)

    """


help_str = """Convert Sherpa docstrings into CIAO ahelp files."""

if __name__ == "__main__":

    import argparse
    import sys

    import stk

    parser = argparse.ArgumentParser(description=help_str,
                                     prog=sys.argv[0])

    parser.add_argument("outdir",
                        help="Files are written to this directory (must exist)")

    parser.add_argument("names", nargs='?', default=None,
                        help="Restrict to these names (stack syntax)")

    parser.add_argument("--debug", action="store_true",
                        help="Print out parsed output")
    parser.add_argument("--sxml", action="store_true",
                        help="Use the SXML rather than AHELp dtd")

    args = parser.parse_args(sys.argv[1:])
    restrict = args.names
    if restrict is not None:
        restrict = stk.build(restrict)

    dtd = 'sxml' if args.sxml else 'ahelp'

    convert(args.outdir, dtd=dtd,
            debug=args.debug,
            restrict=restrict)
