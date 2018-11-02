"""
Extract information from a CIAO ahelp file.

The assumption is that the metadata from the ahelp file can
be "copied over" to the new version of the ahelp file, modulo
some possible changes.

I thought about loading the CIAO ahelp library, but decided
just to query the ahelp file directly.
"""

import os

from xml.etree import ElementTree


home = os.getenv('ASCDS_INSTALL')
if home is None:
    raise ImportError("ASCDS_INSTALL environment variable must be set")


def find_metadata(name, synonyms=None):
    """Extract the metadata from the ahelp for name.

    Parameters
    ----------
    name : str
        The symbol (key of the ahelp file) that is used in an
        'ahelp name' call.
    synonym : list of str or None, optional
        The synonyms for this routine (to be looked for if
        name has no ahelp file).

    Returns
    -------
    metadata : dict
        The keywords are 'key', 'refkeywords', 'seelasogroups',
        'displayseealsogroups', and 'context'.

    Notes
    -----
    Requires CIAO to have been started.

    The ahelp file must be located in $ASCDS_INSTALL/share/doc/xml/<name>.xml.
    """

    # Special case problem cases ...
    #
    #    group is really a different group
    #
    if name == 'group':
        name = 'group_sherpa'

    names = [name]
    if synonyms is not None:
        names += synonyms

    tree = None
    for n in names:
        infile = os.path.join(home, 'share/doc/xml',
                              '{}.xml'.format(n))
        if os.path.isfile(infile):
            expected_key = n
            tree = ElementTree.parse(infile)
            break

    if tree is None:
        raise ValueError("Unable to find ahelp for {}".format(names))

    if name == 'group_sherpa':
        name = 'group'
        expected_key = 'group'

    entry = tree.find('ENTRY')

    pkg = entry.get('pkg')
    if pkg != 'sherpa':
        raise IOError("Expected pkg=sherpa not {} in {}".format(pkg,
                                                                names))

    # Need to deal with synonyms
    key = entry.get('key')
    if key != expected_key:
        raise IOError("Key/Name difference: {}/{}".format(key,
                                                          expected_key))

    refkeywords = entry.get('refkeywords')
    seealso = entry.get('seealsogroups')
    display = entry.get('displayseealsogroups')
    context = entry.get('context')

    def clean(v):
        if v is None:
            return ''
        else:
            return v

    # NOTE: do not return the key retrieved from the file, in case it
    #       is a synonym
    #
    return {'key': name,
            'refkeywords': clean(refkeywords),
            'seealsogroups': clean(seealso),
            'displayseealsogroups': clean(display),
            'context': clean(context)}
