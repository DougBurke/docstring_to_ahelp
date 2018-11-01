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

from importlib import import_module
from inspect import cleandoc, isclass, signature

from sherpa.ui.utils import ModelWrapper
from sherpa.astro.instrument import ARFModel, RMFModel, RSPModel, \
    PileupRMFModel
from sherpa.instrument import ConvolutionModel, PSFModel
from sherpa.data import BaseData
from sherpa.models.basic import TableModel, UserModel
from sherpa.models.template import TemplateModel, \
    InterpolatingTemplateModel

from sherpa.astro import ui

from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import NumpyDocstring


__all__ = ("sym_to_rst", "sym_to_sig", "doc_to_rst", "unwanted")


# Any special configuration for the parsing?
#
# This uses ivar rather than attribute when parsing
# attributes - and I can not easily work out how to process
# the latter.
#
config = Config(napoleon_use_ivar=True)


def sym_to_docstring(name, sym):
    """Return the docstring for the symbol.

    This is needed to work around some subtleties in how models
    are wrapped. It also applies known "corrections" to the docstring.

    Parameters
    ----------
    name : str
        The name of the symbol
    sym
        The Sherpa symbol.

    Returns
    -------
    result : str or None
        The docstring (after removal of excess indentation).

    """

    if isinstance(sym, ModelWrapper):
        doc = str(sym)
    else:
        doc = sym.__doc__

    if doc is None:
        return None

    cdoc = cleandoc(doc)

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

    return cdoc


def sym_to_rst(name, sym):
    """Return the docstring for the symbol.

    This is needed to work around some subtleties in how models
    are wrapped. It also applies known "corrections" to the docstring.

    Parameters
    ----------
    name : str
        The name of the symbol
    sym
        The Sherpa symbol.

    Returns
    -------
    result : str or None
        The docstring (after removal of excess indentation).

    """

    doc = sym_to_docstring(name, sym)
    if doc is None:
        return None

    return doc_to_rst(doc)


def sym_to_sig(name, sym):
    """Return the 'signature' for the symbol.

    Parameters
    ----------
    name : str
        The name of the symbol
    sym
        The Sherpa symbol. This can be None, in which case we
        grab it ourselves (currently only sherpa.astro.ui cases).

    Returns
    -------
    result, sym : str or None, symbol
        The signature and the symbol.

    Notes
    -----
    At present there is no "clever" processing of the
    signature.
    """

    if sym is None:
        sym = getattr(ui, name)

    if isinstance(sym, ModelWrapper):
        # TODO: do we want to say "powlaw1d.name" or "powlaw1d"?
        sig = name.lower()
    else:
        sig = signature(sym)
        if sig is not None:
            sig = "{}{}".format(name, sig)

    return sig, sym


def doc_to_rst(doc):
    """Return the RestructuredText version.

    Parameters
    ----------
    doc : str
        The docstring (after cleaning so that the excess indention
        has been removed).

    Returns
    -------
    result : docstring
        The parsed docstring.

    """

    return NumpyDocstring(doc, config)


unwanted_classes = (ARFModel, RMFModel, RSPModel, PileupRMFModel,
                    ConvolutionModel, PSFModel,
                    TableModel, UserModel,
                    TemplateModel, InterpolatingTemplateModel)


def unwanted(name, sym):
    """Is this a symbol we do not want to process?

    Use simple heuristics to remove unwanted symbols.

    Parameters
    ----------
    name : str
        The name of the symbol
    sym
        The Sherpa symbol.

    Returns
    -------
    flag : bool
        This is True if the symbol should not be used to create an
        ahelp file.

    """

    if name.startswith('_'):
        return True

    if name in ['create_arf']:
        print("  - skipping {} as a known problem case".format(name))
        return True

    if isclass(sym) and issubclass(sym, BaseData):
        return True

    # Does isclass handle 'class or subclass' so we don't need to?
    #
    if type(sym) == ModelWrapper and \
       (sym.modeltype in unwanted_classes or
        issubclass(sym.modeltype, unwanted_classes)):
        return True

    # Don't bother with objects
    #
    if type(sym) == type(object):
        return True

    return False


def syms_from_module(modulename):
    """Create docstrings from the symbols in modulename.

    Parameters
    ----------
    modulename : str
        The module to load - e.g. 'sherpa.astro.ui'.

    Returns
    -------
    out : dict
        The keys are 'name', 'file', and 'docstrings'. The name
        and file are the "dunder" versions of the module, and
        docstrings is a list of dicts. Each of these dicts has
        keys of 'name', 'symbol', 'signature', and 'docstring'.

    """

    module = import_module(modulename)
    out = {'name': module.__name__,
           'file': module.__file__,
           'docstrings': []}

    # Ideally module.__all__ would be a unique list, but this is
    # not true at the time of writing for sherpa.astro.ui, which
    # contains 'erf' twice.
    #
    for name in sorted(set(module.__all__)):

        sym = getattr(module, name)
        if unwanted(name, sym):
            continue

        store = {'name': name,
                 'symbol': sym,
                 'signature': sym_to_sig(name, sym)[0],
                 'docstring': sym_to_docstring(name, sym)}

        out['docstrings'].append(store)

    return out
