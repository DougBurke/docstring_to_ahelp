#!/usr/bin/env python

"""

Usage:

  ./list_xspec_models.py

Aim:

Create the AHELP/XSML tables needed by 'ahelp xs' to list the XSPEC
models. The output is to stdout.

"""

import sys

from sherpa.ui.utils import ModelWrapper
from sherpa.astro.xspec import XSAdditiveModel, XSMultiplicativeModel
from sherpa.astro import ui


def dump_table(label, models):
    # Create XML output manually
    print("<item xml:id='xspec-{}-table'>".format(label.lower()))
    print("<TABLE><CAPTION>{} XSPEC models</CAPTION>".format(label))
    print("<ROW><DATA>Model name</DATA><DATA>Description</DATA></ROW>")
    for name in sorted(models):
        sym = getattr(ui, name).modeltype
        desc = sym.__doc__.split("\n")[0]

        # Assume it is 'The XSPEC <> model: ...' but note that <> is
        # not necessarily the <> name (it should be)
        #
        hdr = 'The XSPEC {} model: '.format(name[2:])
        if desc.lower().startswith(hdr.lower()):
            desc = desc[len(hdr):]
        else:
            sys.stderr.write("Name mis-match {} vs {}\n".format(name, desc))
            idx = desc.find(': ')
            if idx == -1:
                raise ValueError(desc)

            desc = desc[idx + 2:]

        # limited XML replacements; add as necessary
        desc = desc.replace('&', '&amp;')

        print("<ROW><DATA>{}</DATA><DATA>{}</DATA></ROW>".format(name, desc))

    print("</TABLE>")
    print("</item>")


def list_models():

    # We loop through the ui symbols rather than directly inspect the
    # contents of sherpa.astro.xspec to make sure we are using the
    # UI-available names.
    #
    add_models = []
    mul_models = []

    for name in dir(ui):

        sym = getattr(ui, name)
        if not isinstance(sym, ModelWrapper):
            continue

        mclass = sym.modeltype
        if issubclass(mclass, XSAdditiveModel):
            add_models.append(name)
        elif issubclass(mclass, XSMultiplicativeModel):
            mul_models.append(name)

    if len(add_models) == 0:
        raise ValueError("Unable to find any additive models")

    if len(mul_models) == 0:
        raise ValueError("Unable to find any multiplicative models")

    unexpected = [n for n in add_models if not n.startswith('xs')]
    if len(unexpected) > 0:
        raise ValueError("Additive: {}".format(unexpected))

    unexpected = [n for n in mul_models if not n.startswith('xs')]
    if len(unexpected) > 0:
        raise ValueError("Multiplicative: {}".format(unexpected))

    dump_table('Additive', add_models)
    dump_table('Multiplicative', mul_models)


if __name__ == "__main__":

    if len(sys.argv) != 1:
        sys.stderr.write("Usage: {}\n".format(sys.argv[0]))
        sys.exit(1)

    list_models()
