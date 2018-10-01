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

__all__ = ("parse_restructured", )


class SeeAlso(rst.Directive):
    """Handle ..seealso sections.

    Can we just ignore it for now?
    """

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}
    has_content = True

    def run(self):

        self.assert_has_content()
        seealso_node = nodes.container(rawsource=self.block_text)
        self.state.nested_parse(self.content, self.content_offset,
                                seealso_node)
        return [seealso_node]


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

rst.roles.register_local_role('obj', obj_role)
rst.roles.register_local_role('exc', exc_role)


def parse_restructured(label, txt):
    """Convert from the cleaned-up docstring to docutils.

    It apparently doesn't like the ..see also:: directive
    and also the exc role.
    """

    default_settings = OptionParser(components=(rst.Parser,)).get_default_values()
    document = new_document(label, default_settings)
    parser = rst.Parser()
    parser.parse(txt, document)
    return document
