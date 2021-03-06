"""
Convert restructured text - as created by Sphinx - into
the docutils structured documentation.

This is based on [1]_, [2]_, and [3]_.

References
----------

.. [1] https://eli.thegreenplace.net/2017/a-brief-tutorial-on-parsing-restructuredtext-rest/

.. [2] http://docutils.sourceforge.net/docs/howto/rst-directives.html

.. [3] http://docutils.sourceforge.net/docs/howto/rst-roles.html

"""

from docutils.frontend import OptionParser
from docutils.parsers import rst
from docutils.utils import new_document
from docutils import nodes

from docutils.parsers.rst.directives.admonitions import BaseAdmonition

from sphinx import addnodes

# import sphinx.domains.python
#

from .docutils import set_parent

'''
# Try and hack in support for the Sphinx-provided roles and directives
#
from sphinx.registry import SphinxComponentRegistry

import sphinx.roles
import sphinx.directives
import sphinx.directives.code
import sphinx.directives.other
import sphinx.directives.patches
import sphinx.domains.python

sphinx.directives.code.setup(app)
sphinx.directives.other.setup(app)
sphinx.directives.patches.setup(app)
sphinx.directives.setup(app)

sphinx.roles.setup(app)

sphinx.domains.python.setup(app)

class App(object):
    """Trying to hack in app support, but I can't see how
    this will help (i.e. although it calls "the correct" thing,
    the whole structure isn't in place to get it to actually
    work).
    """

    def __init__(self):
        self.registry = SphinxComponentRegistry()

    def add_domain(self, domain):
        self.registry.add_domain(domain)


app = App()

'''

__all__ = ("parse_restructured", )



# Based on sphinx/directives/other.py
#
class SeeAlso(BaseAdmonition):
    """
    An admonition mentioning things to look at as reference.
    """
    node_class = addnodes.seealso


# Unlike sphinx treat version changed and added separately.
# Started with sphinx.domains.changeset.VersionChange
# but simplified greatly.
#
class versionnode(addnodes.versionmodified):
    """Not really needed but helps documention"""


class versionchanged(versionnode):
    """versionchanged"""


class versionadded(versionnode):
    """versionadded"""


class VersionChanged(BaseAdmonition):
    """versionchanged"""
    node_class = versionchanged


class VersionAdded(BaseAdmonition):
    """versionadded"""
    node_class = versionadded


# The use of register_generic_role didn't seem to work, so
# do it manually.
#
def obj_role(role, rawtext, text, lineno, inliner,
             options={}, content=[]):
    """Assume :obj:`foo bar`."""

    # No error checking for now
    node = nodes.literal(rawtext, text)
    return [node], []


def exc_role(role, rawtext, text, lineno, inliner,
             options={}, content=[]):
    """Assume :exc:`foo bar`."""

    # No error checking for now
    node = nodes.literal(rawtext, text)
    return [node], []


# Register the helper code in this module
#
rst.directives.register_directive('seealso', SeeAlso)
rst.directives.register_directive('versionadded', VersionAdded)
rst.directives.register_directive('versionchanged', VersionChanged)

# can not seem to find these in Sphinx
#
rst.roles.register_local_role('obj', obj_role)
rst.roles.register_local_role('exc', exc_role)


def parse_restructured(name, sdoc):
    """Convert from the cleaned-up docstring to docutils.

    Parameters
    ----------
    name : str
        The symbol name.
    sdoc :
        The docstring in restructured text.

    Returns
    -------
    retval
        The document in restructured text format.

    """

    set_parent(name)
    default_settings = OptionParser(components=(rst.Parser,)).get_default_values()
    document = new_document(name, default_settings)
    parser = rst.Parser()
    parser.parse(str(sdoc), document)
    return document
