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


def find_metadata(name):
    """Extract the metadata from the ahelp for name.

    Parameters
    ----------
    name : str
        The symbol (key of the ahelp file) that is used in an
        'ahelp name' call.

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

    infile = os.path.join(home, 'share/doc/xml',
                          '{}.xml'.format(name))
    if not os.path.isfile(infile):
        raise IOError("Unable to find {}".format(infile))

    tree = ElementTree.parse(infile)
    entry = tree.find('ENTRY')

    pkg = entry.get('pkg')
    if pkg != 'sherpa':
        raise IOError("Expected pkg=sherpa not {}".format(pkg))

    key = entry.get('key')
    if key != name:
        raise IOError("Key/Name difference: {}/{}".format(key, name))

    refkeywords = entry.get('refkeywords')
    seealso = entry.get('seealsogroups')
    display = entry.get('displayseealsogroups')
    context = entry.get('context')

    def clean(v):
        if v is None:
            return ''
        else:
            return v

    return {'key': key,
            'refkeywords': clean(refkeywords),
            'seealsogroups': clean(seealso),
            'displayseealsogroups': clean(display),
            'context': clean(context)}
