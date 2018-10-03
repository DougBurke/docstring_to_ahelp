"""
Convert docutils to ahelp DTD for Sherpa documentation.

TODO:
  - references are just converted to <integer> in the text when something
    "nicer" could be done (e.g. links or at least [<integer>]).
    There is some attempt to handle this, but incomplete. A similar
    situation holds for "symbols" - do we add `` around them or not?

"""

import sys

from docutils import nodes

from xml.etree import ElementTree


def splitWhile(pred, xs):
    """Split input when the predicate fails.

    Parameters
    ----------
    pred : function reference
        Elements are let through while pred(x) is True.
    xs : sequence of x

    Returns
    -------
    ls, rs : list, list
        The elements in xs for which pred(x) holds, and then
        the remainder.

    Examples
    --------

    >>> splitWhile(lambda x: x < 5, [1, 2, 5, 3, 4])
    ([1, 2], [5, 3, 4])

    >>> splitWhile(lambda x: x > 5, [1, 2, 5, 3, 4])
    ([], [1, 2, 5, 3, 4])

    >>> splitWhile(lambda x: x > 0, [1, 2, 5, 3, 4])
    ([1, 2, 5, 3, 4], [])

    """

    ls = []
    rs = []
    n = len(xs)
    idx = 0
    while idx < n:
        x = xs[idx]
        if not pred(x):
            break

        ls.append(x)
        idx += 1

    while idx < n:
        rs.append(xs[idx])
        idx += 1

    return ls, rs


def is_para(node):
    """Is this a paragraph node?

    This is a simple wrapper as currently not sure whether we
    want to check on paragraph only, or include sub-classes.

    Parameters
    ----------
    node : docutils.node

    Returns
    -------
    flag : bool

    """

    # return isinstance(node, nodes.paragraph)
    return node.tagname == 'paragraph'


def astext(node):
    """Extract the text contents of the node.

    This is essentially `astext` method on the node but with
    some extra processing to handle some of the tags we can
    handle (e.g. footnote references).

    Parameters
    ----------
    node : docutils.node

    Returns
    -------
    txt : str

    Notes
    -----
    This is not a principled set of conversion rules. It is based
    on the input data.
    """

    if node.tagname == '#text':
        return node.astext()

    if node.tagname == 'footnote':
        assert node[0].tagname == 'label', node
        assert node[1].tagname == 'paragraph', node

        # this drops any links
        return "[{}] {}".format(node[0].astext(), node[1].astext())

    # This check below isn't really sufficient, as need to
    # recurse into elements, such as paragraph nodes. The
    # traverse method did this, at the expense of needing
    # to pass around the context.
    #
    out = []
    for tag in node:
        txt = tag.astext()
        if tag.tagname == 'footnote_reference':
            txt = "[{}]".format(txt)

        elif tag.tagname != '#text':
            print("  - unprocessed {}".format(tag.tagname))

        out.append(txt)

    return " ".join(out)


def make_syntax_block(lines):
    """Create a SYNTAX block.

    Parameters
    ----------
    lines : list of str
        The contents of the SYNTAX block. It can not be empty

    Returns
    -------
    el : ElementTree.Element
        The SYNTAX block
    """

    assert len(lines) > 0

    syn = ElementTree.Element("SYNTAX")
    for l in lines:
        ElementTree.SubElement(syn, 'LINE').text = l

    return syn


def convert_para(para):
    """Add the paragraph to the ahelp PARA block.

    Parameters
    ----------
    para : docutils.node
        The contents to add. It is expected to be paragraph but
        can be other specialized cases

    Returns
    -------
    out : ElementTree.Element

    See Also
    --------
    astext

    Notes
    -----
    This is an expensive way of calling para.astext() but lets me
    note what non-text nodes we have to deal with.
    """

    text = []
    reported = set([])

    if para.tagname != "paragraph":
        print("  - paragraph handling {}".format(para.tagname))

    for n in para:
        name = n.tagname
        # ntxt = n.astext()
        ntxt = astext(n)

        if name == '#text':
            text.append(ntxt)
            continue

        if name == 'footnote_reference':
            text.append("[{}]".format(ntxt))
            continue

        elif name == 'title_reference':
            text.append("`{}`".format(ntxt))
            continue

        elif name == 'literal':
            # For now leave literals alone
            text.append(ntxt)
            continue

        elif name == 'paragraph':
            text.append(ntxt)
            continue

        print("-- debug found [{}] with [{}]\n{}".format(name, ntxt, para))

        text.append(ntxt)
        if name not in reported:
            sys.stderr.write(" - found {} element [{}]\n".format(name,
                                                                 n.astext()))
            reported.add(name)

    out = ElementTree.Element("PARA")
    out.text = "\n".join(text)
    return out


def convert_doctest_block(para):
    """Create a VERBATIM block.

    Parameters
    ----------
    para : docutils.nodes.doctest_block
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    Notes
    -----
    At present this enforces xml:space="preserve".
    """

    assert para.tagname == 'doctest_block', para
    assert para.get('xml:space') == 'preserve', para

    verbatim = ElementTree.Element('VERBATIM')
    verbatim.text = para.astext()
    return verbatim


def convert_literal_block(para):
    """Create a VERBATIM block.

    Parameters
    ----------
    para : docutils.nodes.literal_block
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    See Also
    --------
    convert_doctest_block

    Notes
    -----
    At present this enforces xml:space="preserve".

    """

    assert para.tagname == 'literal_block', para
    assert para.get('xml:space') == 'preserve', para

    verbatim = ElementTree.Element('VERBATIM')
    verbatim.text = para.astext()
    return verbatim


def convert_list_items(para):
    """Convert list_item tags to an ahelp LIST.

    """

    out = ElementTree.Element('LIST')
    for el in para:
        assert el.tagname == 'list_item', el
        ElementTree.SubElement(out, 'ITEM').text = astext(el)

    return out


def convert_block_quote(para):
    """Create the contents of a block_quote.

    Support for bullet_list, enumerated_list, and doctest_block.

    Parameters
    ----------
    para : docutils.nodes.block_quote
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    See Also
    --------
    convert_enumerated_list

    To do
    -----
    This needs to handle complicated cases, where the list
    items contain markup.
    """

    assert para.tagname == 'block_quote', para
    if para[0].tagname in ['bullet_list', 'enumerated_list']:
        assert len(para) == 1, (len(para), para)
        return convert_list_items(para[0])

    if all([p.tagname == 'doctest_block' for p in para]):
        # Treat as a single VERBATIM block
        #
        # Is this sufficient?
        ls = [p.astext() for p in para]
        out = ElementTree.Element('VERBATIM')
        out.text = "\n\n".join(ls)  # note double new line
        return out

    raise ValueError("Unexpected block_quote element in:\n{}".format(para))


def convert_enumerated_list(para):
    """Create a list block.

    Parameters
    ----------
    para : docutils.nodes.enumerated_list
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    See Also
    --------
    convert_block_quote, convert_bullet_list

    To do
    -----
    This needs to handle complicated cases, where the list
    items contain markup.
    """

    assert para.tagname == 'enumerated_list', para
    # assert len(para) == 1, (len(para), para)
    return convert_list_items(para)


def convert_bullet_list(para):
    """Create a list block.

    Parameters
    ----------
    para : docutils.nodes.bullet_list
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    See Also
    --------
    convert_block_quote, convert_enumerated_list

    To do
    -----
    This needs to handle complicated cases, where the list
    items contain markup.
    """

    assert para.tagname == 'bullet_list', para
    # assert len(para) == 1, (len(para), para)
    return convert_list_items(para)


def convert_definition_list(para):
    """Create a definition list.

    This returns a set of paragraphs, with titles being the
    list headers, and the contents being the paragrph contents.

    Parameters
    ----------
    para : docutils.nodes.enumerated_list
        The contents to add.

    Returns
    -------
    out : list of ElementTree.Element

    Notes
    -----
    At present each list item creates a single paragraph. This may
    have to change.
    """

    assert para.tagname == 'definition_list', para

    out = []
    for el in para:
        assert el.tagname == 'definition_list_item', el
        assert el[0].tagname == 'term', el
        assert el[0][0].tagname in ['literal', '#text'], el
        assert el[1].tagname == 'definition', el
        assert el[1][0].tagname == 'paragraph', el
        assert len(el[1]) == 1, el

        xml = convert_para(el[1])
        xml.set('title', el[0].astext())
        out.append(xml)

    return out


def add_table_row(out, el):
    """Given a table row, add it to the table.

    Parameters
    ----------
    out : ElementTree.Element
        A TABLE block.
    el : nodes.thead or nodes.tbody
        The row to add.
    """

    assert el.tagname in ['thead', 'tbody'], el
    for row in el:
        assert row.tagname == 'row'

        xrow = ElementTree.SubElement(out, 'ROW')
        for entry in row:
            assert entry.tagname == 'entry'
            assert len(entry) == 1
            assert entry[0].tagname == 'paragraph'

            ElementTree.SubElement(xrow, 'DATA').text = entry.astext()


def convert_table(tbl):
    """Create a table block.

    Parameters
    ----------
    tbl : docutils.nodes.table
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    """

    assert tbl.tagname == 'table', tbl

    # only one table group
    assert len(tbl) == 1
    tgroup = tbl[0]
    assert tgroup.tagname == 'tgroup', tgroup
    ncols = int(tgroup.get('cols'))
    assert ncols >= 1

    out = ElementTree.Element('TABLE')
    for el in tgroup:
        if el.tagname == 'colspec':
            continue

        if el.tagname in ['thead', 'tbody']:
            add_table_row(out, el)
            continue

        raise ValueError("Unexpected tag: {}".format(el.tagname))

    return out


def convert_note(note):
    """Create a note block.

    Parameters
    ----------
    note : docutils.nodes.note
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    """

    assert note.tagname == 'note', tbl

    # only one paragraph
    assert len(note) == 1
    assert note[0].tagname == 'paragraph'

    out = convert_para(note[0])
    out.set('title', 'Note')
    return out


para_converters = {'doctest_block': convert_doctest_block,
                   'block_quote': convert_block_quote,
                   'enumerated_list': convert_enumerated_list,
                   'definition_list': convert_definition_list,
                   'bullet_list': convert_bullet_list,
                   'table': convert_table,
                   'note': convert_note,
                   'literal_block': convert_literal_block}

# return a list
para_mconverters = ['definition_list']


def make_para_block(para):
    """Create a PARA block.

    Parameters
    ----------
    para : docutils.node
        The paragraph block (or one to be converted to a paragraph block).

    Returns
    -------
    el, flag : ElementTree.Element or list of ElementTree.Element, bool
        The PARA block. The flag is True if the return value is a single
        element (i.e. not a list of elements).

    Notes
    -----
    Unlike add_syntax_block, the input is the docutils element since
    there can be a range of contents.

    FOR NOW DO NOT TRY TO BE TOO CLEVER WITH THE PROCESSING.

    To do
    -----
    Do we want to process <title_reference>text</title_reference>
    in any special way?

    """

    single = True

    if is_para(para):
        converter = convert_para

    else:
        try:
            converter = para_converters[para.tagname]
        except KeyError:
            raise ValueError("Unsupported paragraph type:\ntagname={}\n{}".format(para.tagname, para))

        single = para.tagname not in para_mconverters

    return converter(para), single


def find_syntax(name, sig, indoc):
    """Return the syntax line, if present, and the remaining document.

    Parameters
    ----------
    name : str
        The name of the symbol being processed.
    sig : inspect.Signature or None
        The Python signature of this symbol, if available. It is
        used when there is no syntax line.
    indoc : list of nodes
        The document.

    Returns
    -------
    syntax, remaining : ElementTree.Element or None, list of nodes
        The contents of the syntax block, and the remaining nodes.

    """

    # Use the syntax from the document in preference to the
    # signature line.
    #
    # To do:
    # Improve the conversion of the signature to text, in particular
    # for classes.
    #
    if sig is not None:
        argline = make_syntax_block(["{}{}".format(name, sig)])
    else:
        argline = None

    node = indoc[0]
    if not is_para(node):
        return argline, indoc

    txt = node.astext().strip()
    if not txt.startswith('{}('.format(name)):
        return argline, indoc

    assert txt.endswith(')'), txt

    print("  - using SYNTAX block from file")
    out = make_syntax_block([txt])
    return out, indoc[1:]


def find_synopsis(indoc):
    """Return the synopsis contents, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    synopsis, remaining : ElementTree.Element or None, list of nodes
        The contents of the SYNOPSIS block, and the remaining nodes.

    Notes
    -----
    Assumes the first paragraph is the synopsis. Could restrict to
    only those blocks where the paragraph is a single line, but not
    clear it is worth it (or that is a valid assumption).
    """

    node = indoc[0]
    if not isinstance(node, nodes.paragraph):
        return None, indoc

    out = ElementTree.Element('SYNOPSIS')
    out.text = node.astext().strip()
    return out, indoc[1:]


def find_desc(indoc):
    """Return the basic description, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    desc, remaining : ElementTree.Element or None, list of nodes
        The contents of the DESC block, and the remaining nodes.

    Notes
    -----
    Stops at a rubric, field_list, or container (e.g. see also) block.

    The output does **not** contain any parameter information,
    since this is added lately.
    """

    def want(x):
        return x.tagname not in ['rubric', 'field_list', 'container']

    pnodes, rnodes = splitWhile(want, indoc)
    if len(pnodes) == 0:
        return None, indoc

    out = ElementTree.Element('DESC')
    for para in pnodes:
        p, f = make_para_block(para)
        if f:
            out.append(p)
        else:
            out.extend(p)

    return out, rnodes


def find_fieldlist(indoc):
    """Return the parameter info, if present, and the remaining document.

    It is not clear how object attributes are converted - i.e. do they
    also map to a field_list block?

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    fl, remaining : list or None, list of nodes
        The contents of the field_list block, and the remaining nodes.

    Notes
    -----
    This does not convert to ahelp, since this information may be
    used in multiple places. The assumption is that we have (where
    'name' is the parameter name, or names::

      field_name = 'param name'
      field_name = 'type name'
      field_name = 'returns'
      field_name = 'raises'

    The parsing of the raises block may depend on how the :exc: role
    is parsed - at present it creates a "literal" object which means
    that the exception type is included in the body. Maybe this will
    change if it is handled differently?

    I also need to look at how return information is encoded.
    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'field_list':
        return None, indoc

    out = []
    store = None
    for field in node:
        assert field.tagname == 'field', field

        name = None
        body = None

        for f in field:
            n = f.tagname
            if n == 'field_name':
                # Assume it is okay to remove styling here
                name = f.astext()

            elif n == 'field_body':
                body = f

            else:
                raise ValueError("Unexpected field member:\n{}".format(f))

        if name == 'raises':
            if store is not None:
                out.append(store)
                store = None

            out.append({'type': 'error',
                        'description': body})
            continue

        elif name == 'returns':
            if store is not None:
                out.append(store)
                store = None

            sys.stderr.write("Note: skipping returns for now\n")
            # TODO: will need to support a complex return type too
            break

        # TODO: handle multi-parameter values better
        toks = name.split(' ', 1)
        assert toks[0] in ['param', 'type'], name

        # assume always done in param/type order
        if toks[0] == 'param':
            if store is not None:
                out.append(store)

            store = {'type': 'parameter',
                     'name': toks[1]}

        else:
            assert store is not None
            assert store['name'] == toks[1], (store, name)
            store['description'] = body

    if store is not None:
        out.append(store)

    return out, indoc[1:]


def find_seealso(indoc):
    """Return the See Also info, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    seealso, remaining : list of str or None, list of nodes
        The symbol names (only) in the See Also block, and the
        remaining nodes.

    Notes
    -----
    This does not convert to ahelp. There are expected to be two types:
    a definition_list, which has name and summary, and a collection of
    paragraphs, which just contains the names. The return value is the
    same, in both cases
    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'container':
        return None, indoc

    if node[0].tagname == 'definition_list':
        assert len(node) == 1
        names = []
        for n in node[0]:
            assert n.tagname == 'definition_list_item', n
            assert n[0].tagname == 'term', n
            assert n[0][0].tagname in ['literal', '#text'], n
            names.append(n[0][0].astext())

    elif node[0].tagname == 'paragraph':
        assert len(node) == 1, node  # expected to fail
        names = []
        for n in node[0]:
            assert n.tagname in ['literal', '#text'], n
            names.append(n.astext())

    else:
        raise ValueError("Unexpected see also contents:\n{}".format(node))

    return names, indoc[1:]


def find_notes(indoc):
    """Return the notes section, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    notes, remaining : Element or None, list of nodes
        An ADESC block  and the remaining nodes.

    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'rubric':
        return None, indoc

    if node.astext().strip() != 'Notes':
        return None, indoc

    # look for the next rubric
    #
    lnodes, rnodes = splitWhile(lambda x: x.tagname != 'rubric',
                                indoc[1:])

    out = ElementTree.Element("ADESC", {'title': 'Notes'})
    for para in lnodes:
        p, f = make_para_block(para)
        if f:
            out.append(p)
        else:
            out.extend(p)

    return out, rnodes


def find_references(indoc):
    """Return the references section, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    refs, remaining : Element or None, list of nodes
        An ADESC block  and the remaining nodes.

    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'rubric':
        return None, indoc

    if node.astext().strip() != 'References':
        return None, indoc

    # look for the next rubric
    #
    lnodes, rnodes = splitWhile(lambda x: x.tagname != 'rubric',
                                indoc[1:])

    out = ElementTree.Element("ADESC", {'title': 'References'})
    cts = ElementTree.SubElement(out, 'LIST')

    for footnote in lnodes:
        assert footnote.tagname == 'footnote'

        ElementTree.SubElement(cts, 'ITEM').text = astext(footnote)

    return out, rnodes


def find_examples(indoc):
    """Return the examples section, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    examples, remaining : Element or None, list of nodes
        A QEXAMPLELIST block and the remaining nodes.

    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'rubric':
        return None, indoc

    if node.astext().strip() != 'Examples':
        return None, indoc

    # look for the next rubric
    #
    lnodes, rnodes = splitWhile(lambda x: x.tagname != 'rubric',
                                indoc[1:])

    out = ElementTree.Element("QEXAMPLELIST")

    # Split the example section up into examples. Use several heuristics.
    #
    # Expect an example to be optional text blocks then code. However,
    # if we have code block, text block where text starts with lower case,
    # code block then this is all part of the same example. An example
    # of this last case is 'ignore2d'.
    #
    # Note: I could make a code-only examples use the SYNTAX block
    #       but for now do not bother with this
    #
    desc = None
    for para in lnodes:

        # some repeated checks here and in make_para_block
        #
        name = para.tagname
        assert name in ['paragraph', 'doctest_block',
                        'block_quote', 'literal_block'], para

        p, f = make_para_block(para)
        assert f

        if desc is None:
            if name == 'paragraph' and len(out) > 1 and \
               para.astext()[0].islower():
                qex = out[-1]
                assert qex.tag == 'QEXAMPLE'
                desc = qex[-1]
                assert desc.tag == 'DESC'

            else:
                example = ElementTree.SubElement(out, 'QEXAMPLE')
                desc = ElementTree.SubElement(example, 'DESC')

        desc.append(p)

        # Do we start a new example?
        #
        if name != 'paragraph':
            desc = None

    return out, rnodes


def convert_docutils(indoc):
    """Given the docutils documentation, convert to ahelp DTD.

    Parameters
    ----------
    indoc : dict
        The keys are 'name', 'document', and 'signature'.
        The document field contains the docutils structure
        and signature is None or an inspect.Signature object.

    Returns
    -------
    ahelp
        The ahelp version of the documentation.

    """

    name = indoc['name']

    # Basic idea is parse, augment/fill in, and then create the
    # ahelp structure, but it is likely this is going to get
    # confused.
    #
    nodes = list(indoc['document'])
    syntax, nodes = find_syntax(name, indoc['signature'], nodes)
    synopsis, nodes = find_synopsis(nodes)
    desc, nodes = find_desc(nodes)

    # Can have parameters and then a "raises" section, or just one,
    # or neither. Really they should both be before the See Also
    # block (are they automatically merged in this case?),
    # but that is not currently guaranteed (e.g. fake_pha)
    #
    fieldlist1, nodes = find_fieldlist(nodes)

    seealso, nodes = find_seealso(nodes)

    fieldlist2, nodes = find_fieldlist(nodes)

    notes, nodes = find_notes(nodes)
    refs, nodes = find_references(nodes)
    examples, nodes = find_examples(nodes)

    # assert nodes == [], nodes
    if nodes != []:
        sys.stderr.write(" - ignoring trailing:\n{}\n".format(nodes))
        return nodes

    # Augment the blocks
    #
    if syntax is None:
        # create the syntax block
        sys.stderr.write("TODO: does {} need a SYNTAX block?\n".format(name))

    # Create the output
    #
    root = ElementTree.Element('cxchelptopics')
    outdoc = ElementTree.ElementTree(root)

    xmlattrs = {'pkg': 'sherpa',
                'key': name,
                'refkeywords': '',  # TODO
                'seealsogroups': '',  # TODO
                'displayseealsogroups': '',  # TODO
                'context': 'sherpaish'  # TODO
                }
    entry = ElementTree.SubElement(root, 'ENTRY', xmlattrs)

    for n in [synopsis, syntax, desc, examples, notes, refs]:
        if n is None:
            continue

        entry.append(n)

    # Add the "standard" postamble.
    #
    bugs = ElementTree.SubElement(entry, 'BUGS')
    para = ElementTree.SubElement(bugs, 'PARA')
    para.text = 'See the '
    attrs = {'link': 'http://cxc.harvard.edu/sherpa/bugs/'}
    link = ElementTree.SubElement(para, 'HREF', attrs)
    link.text = 'bugs pages on the Sherpa website'
    link.tail = ' for an up-to-date listing of known bugs.'

    ElementTree.SubElement(entry, 'LASTMODIFIED').text = 'December 2018'

    return outdoc
