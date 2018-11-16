"""Utility routines."""


def save_doc(outfile, xmldoc):
    """Write the ahelp XML to a file.

    The DTD needs to be passed in as we manually hack it in,
    and have lost it in xmldoc, which could partly be me but is
    partly ElementTree too.
    """

    root = xmldoc.getroot().tag
    if root == 'cxchelptopics':
        dtdname = 'CXCHelp.dtd'
    elif root == 'cxcdocumentationpage':
        dtdname = '/data/da/Docs/sxml_manuals/dtds/CXCDocPage.dtd'
    else:
        raise ValueError("Unrecognized root element: {}".format(root))

    docstr = '<!DOCTYPE {} SYSTEM "{}">'.format(root, dtdname)

    # See https://stackoverflow.com/a/43922805
    #
    with open(outfile, 'wb') as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>'.encode('utf8'))
        f.write(docstr.encode('utf8'))
        xmldoc.write(f, 'utf-8')
