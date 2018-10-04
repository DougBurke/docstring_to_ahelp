#!/usr/bin/env python

"""
Usage:

  ./extract_docstrings.py modulename outdir

Aim:

Given a module name, such as sherpa.astro.ui, extract the docstrings
for all the relevant symbols and write them (one per symbol) to
outdir, as outdir/txt/<symbol>.txt. Some basic metadata is written
out to outdir/metadata.json

This is heavily biased to Sherpa modules.

The module name must be importable.

"""

import json
import os
import time

from parsers.sherpa import syms_from_module


def extract(modulename, outdir):

    if os.path.exists(outdir):
        raise IOError("Output directory exists: {}".format(outdir))

    tval = time.asctime()

    syms = syms_from_module(modulename)
    ndoc = len(syms['docstrings'])
    if ndoc == 0:
        raise ValueError("No docstrings found in {}".format(modulename))

    txtdir = os.path.join(outdir, 'txt')
    os.mkdir(outdir)
    os.mkdir(txtdir)

    metadata = {'time': tval,
                'module': syms['name'],
                'location': syms['file'],
                'number': ndoc}

    mfile = os.path.join(outdir, 'metadata.json')
    open(mfile, 'w').write(json.dumps(metadata))

    for sym in syms['docstrings']:
        outfile = os.path.join(txtdir, '{}.txt'.format(sym['name']))
        open(outfile, 'w').write(sym['docstring'] + '\n')

    print("Created {} with {} txt files".format(outdir, ndoc))


help_str = """Extract the docstrings from a module and write out as text files."""

if __name__ == "__main__":

    import argparse
    import sys

    parser = argparse.ArgumentParser(description=help_str,
                                     prog=sys.argv[0])

    parser.add_argument("modulename",
                        help="The module to use")
    parser.add_argument("outdir",
                        help="Files are written to this directory")

    args = parser.parse_args(sys.argv[1:])
    extract(args.modulename, args.outdir)
