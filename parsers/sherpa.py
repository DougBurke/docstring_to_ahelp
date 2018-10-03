"""
Extract the documentation from the Sherpa docstring,
returning restructured text format.

To do
-----

1. add more logic on where the documentation from the symbol
   comes from.

2. parse the ahelp documentation (or the pre-parsed data)
   for the necessary metadata. If it is pre-parsed then maybe
   it belongs in a different module.

"""

from inspect import cleandoc, signature

from sherpa.ui.utils import ModelWrapper
from sherpa.astro import ui

from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import NumpyDocstring


__all__ = ("sherpa_to_restructured", )


# Any special configuration for the parsing?
#
# This uses ivar rather than attribute when parsing
# attributes - and I can not easily work out how to process
# the latter.
#
config = Config(napoleon_use_ivar=True)


def sherpa_to_restructured(name):
    """Given the name of a Sherpa symbol, return reStructuredText.

    Parameters
    ----------
    name : str
        The name of a function in sherpa.astro.ui. Limited checking
        is done to make sure it is sensible.

    Returns
    -------
    result : dict or None
        The keys of the dict are 'name', 'docstring', and 'signature',
        the latter of which is either an inspect.Signature object
        or None.

    """

    sym = getattr(ui, name)

    if isinstance(sym, ModelWrapper):
        print(" trying [{}] as model".format(name))
        doc = str(sym)
    else:
        doc = sym.__doc__

    if doc is None:
        return None

    cdoc = cleandoc(doc)

    # HACK
    if name == 'set_xsabund':
        sterm = 'The pre-defined abundance tables are:'
        idx = cdoc.find(sterm)
        if idx == -1:
            raise ValueError("Unable to find {} in set_xsabund".format(sterm))

        idx += len(sterm)
        ldoc = cdoc[:idx]
        rdoc = cdoc[idx:]
        assert rdoc[0:2] == "\n ", rdoc[0:10]

        # add in an extra new-line character
        #
        cdoc = ldoc + "\n" + rdoc

    out = {'name': name,
           'docstring': NumpyDocstring(cdoc, config),
           'signature': None}

    try:
        out['signature'] = signature(sym)
    except (TypeError, ValueError):
        pass

    return out
