#!/usr/bin/env python

"""

Usage:

  ./list_sherpa_models.py

Aim:

Create the AHELP/XSML table needed by 'ahelp models' to list the
non-XSPEC models. The output is to stdout.

"""

import sys

from sherpa.ui.utils import ModelWrapper
from sherpa.astro.xspec import XSModel
from sherpa.astro import ui


def dump_table(models):
    # Create XML output manually
    print("<item xml:id='sherpa-model-table'>")
    print("<TABLE><CAPTION>Sherpa models (exclding those from XSPEC)</CAPTION>")
    print("<ROW><DATA>Model name</DATA><DATA>Description</DATA></ROW>")
    for name in sorted(models):

        sym = getattr(ui, name).modeltype
        if sym.__doc__ == None:
            # sys.stderr.write("NOTE: no docstring for {}\n".format(name))
            continue

        desc = sym.__doc__.split("\n")[0]

        # limited XML replacements; add as necessary
        desc = desc.replace('&', '&amp;')

        print("<ROW><DATA>{}</DATA><DATA>{}</DATA></ROW>".format(name, desc))

    print("</TABLE>")
    print("</item>")


# Hard-coded list of names to exclude
#
excluded = ['arfmodel', 'arfmodelnopha', 'arfmodelpha',
            'rmfmodel', 'rmfmodelnopha', 'rmfmodelpha',
            'rspmodel', 'rspmodelnopha', 'rspmodelpha',
            'usermodel'
        ]

def list_models():

    models = []

    for name in dir(ui):

        if name in excluded:
            continue

        sym = getattr(ui, name)
        if not isinstance(sym, ModelWrapper):
            continue

        mclass = sym.modeltype
        if issubclass(mclass, XSModel):
            continue

        models.append(name)

    if len(models) == 0:
        raise ValueError("Unable to find any models")

    unexpected = [n for n in models if n.startswith('xs')]
    if len(unexpected) > 0:
        raise ValueError("{}".format(unexpected))

    dump_table(models)


if __name__ == "__main__":

    if len(sys.argv) != 1:
        sys.stderr.write("Usage: {}\n".format(sys.argv[0]))
        sys.exit(1)

    list_models()
