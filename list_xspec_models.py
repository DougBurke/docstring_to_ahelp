#!/usr/bin/env python

"""

Usage:

  ./list_xspec_models.py outdir

Aim:

Create the AHELP/XSML tables needed by 'ahelp xs' to list the XSPEC
models. The output is to outdir/xs.xml and outdir must exist.

It is expected that the file is created by doc2ahelp.py but this is
provided for testing and special cases.

"""

import sys

from helpers import list_xspec_models


if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.stderr.write("Usage: {} outdir\n".format(sys.argv[0]))
        sys.exit(1)

    outfile = list_xspec_models(outdir=sys.argv[1])
    print(f"Created: {outfile}")
