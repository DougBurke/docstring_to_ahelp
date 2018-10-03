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

from sphinx.ext.napoleon.docstring import NumpyDocstring


__all__ = ("sherpa_to_restructured", )


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
    out = {'name': name,
           'docstring': NumpyDocstring(cdoc),
           'signature': None}

    try:
        out['signature'] = signature(sym)
    except (TypeError, ValueError):
        pass

    return out
