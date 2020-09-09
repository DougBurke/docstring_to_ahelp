"""
Convert docutils to ahelp or SXML DTD for Sherpa documentation.

TODO:
  - references are just converted to <integer> in the text when something
    "nicer" could be done (e.g. links or at least [<integer>]).
    There is some attempt to handle this, but incomplete. A similar
    situation holds for "symbols" - do we add `` around them or not?

"""

from collections import OrderedDict
import sys

from docutils import nodes

from xml.etree import ElementTree

from sherpa.ui.utils import ModelWrapper
from sherpa.astro.xspec import XSAdditiveModel, XSMultiplicativeModel


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

    if node.tagname == 'system_message':
        sys.stderr.write(" - skipping message: {}\n".format(node))
        return ''

    if node.tagname == '#text':
        return node.astext()

    if node.tagname == 'reference':
        return node.astext()

    # assume that the footnote contains a single item of
    # text
    if node.tagname == 'footnote':
        assert node[0].tagname == 'label', node
        ctr = "[{}]".format(node[0].astext())

        # handle different variants; should these use astext()?
        #
        if node[1].tagname == 'paragraph':
            # this drops any links
            cts = astext(node[1])
        elif node[1].tagname == 'enumerated_list':
            # not sure if going to want to handle differently
            # to above.
            cts = astext(node[1])
        else:
            raise ValueError("Unexpected node {} in {}".format(node[1].tagname, node))

        return "{} {}".format(ctr, cts)

    elif node.tagname == 'footnote_reference':
        return "[{}]".format(node.astext())

    elif node.tagname == 'title_reference':
        return "`{}`".format(node.astext())

    elif node.tagname == 'literal':
        # what should be done here?
        return node.astext()

    elif node.tagname == 'emphasis':
        # what should be done here?
        return node.astext()

    elif node.tagname == 'strong':
        # what should be done here?
        return node.astext()

    assert node.tagname in ['paragraph', 'list_item',
                            'enumerated_list'], node

    # Recurse into this "container".
    #
    out = []
    for tag in node:
        # print("DBG: [{}] tag={}".format(node.tagname, tag.tagname))
        out.append(astext(tag))

    out = " ".join(out)
    return out


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
    # reported = set([])

    if para.tagname != "paragraph":
        print("  - paragraph handling {}".format(para.tagname))

    for n in para:
        text.append(astext(n))
        # name = n.tagname
        # ntxt = astext(n)

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

    # Do we need to worry about multi-paragraph blocks?
    #
    if para[0].tagname == 'paragraph':
        assert len(para) == 1, (len(para), para)
        out = ElementTree.Element('VERBATIM')
        out.text = astext(para[0])
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


"""

<definition_list_item>
  <term>The pre-defined abundance tables are:</term>
  <definition>
    <bullet_list bullet="-">
      <list_item>
        <paragraph>'angr', from <footnote_reference ids="id2" refname="2">2</footnote_reference></paragraph>
      </list_item>
      <list_item>
        <paragraph>'aspl', from <footnote_reference ids="id3" refname="3">3</footnote_reference></paragraph></list_item><list_item><paragraph>'feld', from <footnote_reference ids="id4" refname="4">4</footnote_reference>, except for elements not listed which
are given 'grsa' abundances</paragraph></list_item><list_item><paragraph>'aneb', from <footnote_reference ids="id5" refname="5">5</footnote_reference></paragraph></list_item><list_item><paragraph>'grsa', from <footnote_reference ids="id6" refname="6">6</footnote_reference></paragraph></list_item><list_item><paragraph>'wilm', from <footnote_reference ids="id7" refname="7">7</footnote_reference>, except for elements not listed which
are given zero abundance</paragraph></list_item><list_item><paragraph>'lodd', from <footnote_reference ids="id8" refname="8">8</footnote_reference></paragraph></list_item></bullet_list></definition></definition_list_item>

"""


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
            # an entry can be empty
            if len(entry) == 0:
                txt = ''
            else:
                assert len(entry) == 1, len(entry)
                assert entry[0].tagname == 'paragraph'
                txt = entry.astext()

            ElementTree.SubElement(xrow, 'DATA').text = txt


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

    assert note.tagname == 'note'

    # Assume:
    #  1 paragraph - text
    #  2 paragrahs - first is title, second is text
    #
    # could be mode though
    assert all([n.tagname == 'paragraph' for n in note]), note

    # could handle this, but would need to return [Element]
    #
    assert len(note) < 3, (len(note), note)

    if len(note) == 1:
        title = 'Note'
        out = convert_para(note[0])
    else:
        title = astext(note[0])
        out = convert_para(note[1])

    out.set('title', title)
    return out


def convert_field_body(fbody):
    """Create a field_body block.

    Parameters
    ----------
    fbody : docutils.nodes.field_body
        The contents to add.

    Returns
    -------
    out : ElementTree.Element

    """

    assert fbody.tagname == 'field_body'

    assert all([n.tagname == 'paragraph' for n in fbody]), fbody

    # could handle multiple blocks, but would need to return [Element]
    #
    n = len(fbody)
    if n == 0:
        # do we want this?
        return ElementTree.Element('PARA')
    elif n == 1:
        return convert_para(fbody[0])
    else:
        raise ValueError("Need to handle {} blocks".format(n))


para_converters = {'doctest_block': convert_doctest_block,
                   'block_quote': convert_block_quote,
                   'enumerated_list': convert_enumerated_list,
                   'definition_list': convert_definition_list,
                   'bullet_list': convert_bullet_list,
                   'table': convert_table,
                   'note': convert_note,
                   'field_body': convert_field_body,
                   'literal_block': convert_literal_block}

# return a list
para_mconverters = ['definition_list']


def make_para_blocks(para):
    """Create one or more PARA blocks.

    Parameters
    ----------
    para : docutils.node
        The paragraph block (or one to be converted to a paragraph block).

    Returns
    -------
    el, flag : list of ElementTree.Element
        The PARA block(s), which can be empty.

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

    if para.tagname == 'system_message':
        print(" - skipping message: {}".format(para.astext()))
        return []

    # TODO: convert all the "conversion" routines to return a list
    single = True

    if is_para(para):
        converter = convert_para

    else:
        try:
            converter = para_converters[para.tagname]
        except KeyError:
            raise ValueError("Unsupported paragraph type:\ntagname={}\n{}".format(para.tagname, para))

        single = para.tagname not in para_mconverters

    out = converter(para)
    if single:
        out = [out]

    return out


def find_syntax(name, sig, indoc):
    """Return the syntax line, if present, and the remaining document.

    Parameters
    ----------
    name : str
        The name of the symbol being processed.
    sig : str or None
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
        argline = make_syntax_block([sig])
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


def add_pars_to_syntax(syntax, fieldlist):
    """Do we add a summary of the parameter information to SYNTAX?

    """

    if syntax is None or fieldlist is None:
        return syntax

    partypes = []
    for par in fieldlist['params']:
        try:
            partypes.append((par['name'], par['type']))
        except KeyError:
            continue

    if len(partypes) == 0:
        return syntax

    ElementTree.SubElement(syntax, 'LINE').text = ''

    # TODO: Do we need a header line?
    for pname, ptype in partypes:
        ps = make_para_blocks(ptype)
        assert len(ps) == 1
        ptxt = '{} - {}'.format(pname, ps[0].text)
        ElementTree.SubElement(syntax, 'LINE').text = ptxt

    return syntax


def add_synonyms_to_syntax(syntax, synonyms):
    """Do we note any synonyms?

    """

    if syntax is None or synonyms is None:
        return syntax

    # Could handle multiple, but only expect 1 so note if this
    # changes.
    assert len(synonyms) == 1, synonyms

    ElementTree.SubElement(syntax, 'LINE').text = ''
    ElementTree.SubElement(syntax, 'LINE').text = 'Alias: ' + synonyms[0]

    return syntax


def augment_examples(examples, symbol):
    """Add in examples based on the symbol (at present models only).

    """

    if symbol is None:
        return examples

    if not isinstance(symbol, ModelWrapper):
        return examples

    mtype = symbol.modeltype.__name__.lower()
    strval = str(symbol.modeltype('mdl'))

    if examples is None:
        examples = ElementTree.Element('QEXAMPLELIST')

    example = ElementTree.Element('QEXAMPLE')

    syn = ElementTree.SubElement(example, 'SYNTAX')
    line = ElementTree.SubElement(syn, 'LINE')
    line.text = '>>> create_model_component("{}", "mdl")'.format(mtype)
    line = ElementTree.SubElement(syn, 'LINE')
    line.text = '>>> print(mdl)'

    desc = ElementTree.SubElement(example, 'DESC')
    para = ElementTree.SubElement(desc, 'PARA')
    para.text = 'Create a component of the {} model'.format(mtype) + \
                ' and display its default parameters. The output is:'

    verb = ElementTree.SubElement(desc, 'VERBATIM')
    verb.text = strval

    examples.insert(0, example)

    return examples


def find_synopsis(indoc):
    """Return the synopsis contents, if present, and the remaining document.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    synopsis, tags, remaining : ElementTree.Element or None, list of str, list of nodes
        The contents of the SYNOPSIS block, words which can be used in the
        refkeywords attribute, and the remaining nodes.

    Notes
    -----
    Assumes the first paragraph is the synopsis. Could restrict to
    only those blocks where the paragraph is a single line, but not
    clear it is worth it (or that is a valid assumption).
    """

    node = indoc[0]
    if not isinstance(node, nodes.paragraph):
        return None, '', indoc

    syn = node.astext().strip()

    def clean(v):
        # assuming only have one of these conditions to process, so the
        # order of operations does not matter
        for c in [',', '.', ':', '"', "'"]:
            if v.endswith(c):
                v = v[:-1]
            if v.startswith(c):
                v = v[1:]

        return v

    # return a sorted list of keys to make comparisons easier
    #
    keys = [clean(k) for k in syn.lower().split()]
    keywords = sorted(list(set(keys)))

    out = ElementTree.Element('SYNOPSIS')
    out.text = syn
    return out, keywords, indoc[1:]


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
        return x.tagname not in ['rubric', 'field_list', 'container', 'seealso']

    pnodes, rnodes = splitWhile(want, indoc)
    if len(pnodes) == 0:
        return None, indoc

    out = ElementTree.Element('DESC')
    for para in pnodes:
        for b in make_para_blocks(para):
            out.append(b)

    # assert len(out) > 0
    if len(out) == 0:
        print("NOTE: no text in DESC block")

    return out, rnodes


def find_fieldlist(indoc):
    """Return the parameter info, if present, and the remaining document.

    It is not clear how object attributes are converted - i.e. do they
    also map to a field_list block? I have switched the default
    Napoleon configuration so that theyt use ivar blocks for the
    model attributes.

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

      field_name = 'ivar'

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

    # Use an OrderedDict rather than a list, with the idea that
    # the field_name value can be used to determine whether we are
    # adding a new entry or appending to an existing entry.
    #
    # This means that raises and returns have a "fake" name added,
    # and will contain multiple elements.
    #
    params = OrderedDict()
    returns = []
    raises = []

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

        toks = name.split(' ', 1)
        t0 = toks[0]
        ntoks = len(toks)
        assert t0 in ['param', 'ivar', 'type', 'rtype', 'raises', 'returns'], name
        if t0 == 'raises':
            # Has there been a change in how the raises section is
            # encoded, or is it more that when I originally wrote
            # this I had no examples which returned several tokens?
            #
            # It looks like we don't do anything with this at the moment
            # anyway.
            if ntoks == 1:
                raises.append(body)
            else:
                raises.append({'tokens': toks[1:], 'body': body})

            continue

        elif t0 in ['returns', 'rtype']:
            assert ntoks == 1, (toks, name)
            returns.append((t0, body))
            continue

        assert ntoks == 2, name
        pname = toks[1]

        # NOTE: for attributes (and parameters, but don't think have any
        # like this), can have multiple "ivar p1", "ivar p2" lines
        # before the description. Need to amalgamate.
        #
        # Heuristic
        #    preceding name ends in a comma
        #    field_body of preceding is empty
        #    assume this happens at most once
        #
        if t0 == 'ivar' and len(params) > 0:
            prev_key = list(params.keys())[-1]
            prev_val = params[prev_key]

            # strip() is probably not needed, but just in case
            if prev_key.strip().endswith(',') and len(prev_val['ivar']) == 0:

                # edit the params structure, but as removing the
                # last item it is okay (ie ordering is maintained).
                #
                del params[prev_key]
                new_key = "{} {}".format(prev_key, pname)

                prev_val['name'] = new_key
                prev_val['ivar'] = body
                params[new_key] = prev_val
                continue

        try:
            store = params[pname]
        except KeyError:
            params[pname] = {'name': pname}
            store = params[pname]

        store[t0] = body

    out = list(params.values())
    return {'params': out, 'returns': returns, 'raises': raises}, \
        indoc[1:]


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
    if node.tagname != 'seealso':
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

    # Strip out "," fragments.
    #
    names = [n for n in names if n.strip() != ',']

    # Some names can contain the full module path, so clean them
    # up, and then remove duplicates (shouldn't be any).
    #
    # I don't think there should be any see also symbol with a '.' in it
    # for any other reason than it is part of a module path.
    #
    out = []
    for n in names:
        if n.startswith('sherpa.'):
            n = n.split('.')[-1]
        elif n.find('.') != -1:
            print("ERROR: invalid seealso {}".format(names))
            sys.exit(1)

        if n not in out:
            out.append(n)

    if len(names) != len(out):
        print(" - see also contains duplicates: {}".format(names))

    return out, indoc[1:]


def find_notes(name, indoc):
    """Return the notes section, if present, and the remaining document.

    Parameters
    ----------
    name : str
        The name of the symbol being documented.
    indoc : list of nodes
        The document.

    Returns
    -------
    notes, remaining : Element or None, list of nodes
        An ADESC block  and the remaining nodes.

    Notes
    -----
    If this is a note to say that this model is only available with
    XSPEC >= n then we strip it out, since the CIAO build has a known
    version.

    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]

    # TODO: should this use isinstance instead?
    if node.tagname != 'rubric':
        return None, indoc

    if node.astext().strip() != 'Notes':
        return None, indoc

    # look for the next rubric that is not a 'Notes' section
    #
    lnodes, rnodes = splitWhile(lambda x: x.tagname != 'rubric',
                                indoc[1:])

    # Strip out any paragraph which matches:
    #
    # This model is only available when used with XSPEC 12.9.1 or later.
    # This model is only available when used with XSPEC 12.10.0 or later.
    #
    # Note that (at present) there is no attempt to remove the
    # sentence from a block of text (ie if there is additional material),
    # since it looks like it doesn't happen (but it could).
    #
    # Actually, changing the "only in 12.10.0 or later" to a
    # "new in CIAO 4.11" section. Unfortunately do not seem to have
    # any like this.
    #
    def version(v):
        return 'This model is only available when used with ' + \
            'XSPEC {} or later.'.format(v)

    v1291 = version('12.9.1')
    v12100 = version('12.10.0')
    v12101 = version('12.10.1')

    def wanted(n):
        txt = n.astext()
        return n.astext() not in [v1291, v12100]

    lnodes = list(filter(wanted, lnodes))
    if len(lnodes) == 0:
        # print(" - NOTE section is about XSPEC version")
        return None, rnodes

    if len(lnodes) == 1 and lnodes[0].astext() == v12101:

        out = ElementTree.Element("ADESC", {'title': 'New in CIAO 4.12'})
        para = ElementTree.SubElement(out, 'PARA')
        para.text = 'The {} model '.format(name) + \
                    '(added in XSPEC 12.10.1) is new in CIAO 4.12'

        return out, rnodes

    out = ElementTree.Element("ADESC", {'title': 'Notes'})
    for para in lnodes:
        for b in make_para_blocks(para):
            out.append(b)

    assert len(out) > 0
    return out, rnodes


def find_warning(indoc):
    """Extract a warning section, if it exists.

    Parameters
    ----------
    indoc : list of nodes
        The document.

    Returns
    -------
    warning, remaining : Element or None, list of nodes
        An DESC block and the remaining nodes.

    """

    if len(indoc) == 0:
        return None, indoc

    node = indoc[0]
    if node.tagname != 'warning':
        return None, indoc

    assert len(node.children) == 1

    # This probably needs to handle more-complocated structures,
    # but stay simple for now.
    #
    out = ElementTree.Element("ADESC", {'title': 'Warning'})
    cts = ElementTree.SubElement(out, 'PARA')
    cts.text = astext(node.children[0])

    return out, indoc[1:]


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

    # Support Example as well as Examples
    txt = node.astext().strip()
    if txt not in ['Examples', 'Example']:
        return None, indoc

    if txt == 'Example':
        print(" - has an Example, not Examples, block")

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

        # some repeated checks here and in make_para_blocks
        #
        name = para.tagname
        assert name in ['paragraph', 'doctest_block',
                        'block_quote', 'literal_block'], para

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

        for p in make_para_blocks(para):
            desc.append(p)

        # Do we start a new example?
        #
        if name != 'paragraph':
            desc = None

    return out, rnodes


def extract_params(fieldinfo):
    """Extract the parameter information from a fieldlist.

    """

    if fieldinfo is None:
        return None

    parinfo = fieldinfo['params']
    retinfo = fieldinfo['returns']

    is_attrs = any(['ivar' in p for p in parinfo])

    nparams = len(parinfo)
    nret = len(retinfo)
    if nparams == 0 and nret == 0:
        assert len(fieldinfo['raises']) != 0
        print(" - looks like only has a raises block, so skipping")
        return None

    if is_attrs:
        name = 'object'
        value = 'attribute'
    else:
        name = 'function'
        value = 'parameter'

    adesc = ElementTree.Element("ADESC",
                                {'title': '{}S'.format(value.upper())})

    p = ElementTree.SubElement(adesc, 'PARA')
    if nparams == 0:
        p.text = 'This {} has no {}s'.format(name, value)
    elif nparams == 1:
        p.text = 'The {} for this {} is:'.format(value, name)
    else:
        p.text = 'The {}s for this {} are:'.format(value, name)

    for par in parinfo:

        # Keys are name, param, and type. At present type is not used.
        #          name, ivar
        #
        if 'param' in par:
            ps = make_para_blocks(par['param'])
            assert len(ps) > 0
            ps[0].set('title', par['name'])

        elif 'ivar' in par:
            ps = make_para_blocks(par['ivar'])
            assert len(ps) > 0
            ps[0].set('title', par['name'])

        else:
            # Not description, so an empty paragraph.
            p = ElementTree.SubElement(adesc, 'PARA', {'title': par['name']})
            ps = [p]

        for p in ps:
            adesc.append(p)

    if nret == 0:
        return adesc

    p = ElementTree.SubElement(adesc, 'PARA', {'title': 'Return value'})
    p.text = 'The return value from this function is:'

    # For now only handle the simple case
    #
    rvals = [r[1] for r in retinfo if r[0] == 'returns']
    assert len(rvals) == 1, retinfo

    adesc.append(convert_para(rvals[0]))

    return adesc


def create_seealso(name, seealso):
    """Come up with the seealsogroups metadata.

    Parameters
    ----------
    name : str
        The name of the symbol being documented.
    seealso : list of str
        The symbols that have been manually selected as being related
        to name.

    Returns
    -------
    seealso, displayseealso : str, str
        The proposed seealsogroup and displayseealsogroup settings
        in the ahelp file.

    Notes
    -----
    The idea is to create pairs of tokens (name, s) where s is each
    element of seealso, so that ahelp can match the two. This could be
    changed to handle all routines, but we do not have a symmetrical
    relationship in the manual "See Also" sections, so this would miss
    out. It may be that we need to use displayseealsogroup instead;
    let's see.
    """

    if seealso is None:
        print("  - {} has no SEE ALSO".format(name))
        return '', ''

    # remove case and sort lexicographically.
    #
    def convert(t1, t2):
        if t1 < t2:
            toks = (t1, t2)
        else:
            toks = (t2, t1)

        return "{}{}".format(*toks)

    nlower = name.lower()
    pairs = [convert(nlower, s.lower()) for s in seealso]

    out = ' '.join(pairs)
    return out, ''


def find_context(name, symbol=None):
    """What is the ahelp context for this symbol?

    If we can not find a context, use sherpaish so that it can
    be easily identified.

    Parameters
    ----------
    name : str
    symbol
        The symbol to document (e.g. sherpa.astro.ui.load_table or
        sherpa.astro.ui.xsapec) or None.

    Returns
    -------
    context : str

    """

    if symbol is not None:
        if isinstance(symbol, ModelWrapper):
            return 'models'

    # Hard code some values: the CIAO 4.10 contexts for Sherpa are
    #
    #   confidence
    #   contrib
    #   data
    #   filtering
    #   fitting
    #   info
    #   methods
    #   modeling
    #   models
    #   plotting
    #   psfs
    #   saving
    #   sherpa
    #   statistics
    #   utilities
    #   visualization
    #
    # NOTE: some of these should get picked up from ahelp files
    #       (ie this is unneeded)
    #
    if name in ['get_conf_results', 'get_conf_opt',
                'get_covar_results', 'get_covar_opt',
                'get_proj_results', 'get_proj_opt']:
        return 'confidence'

    if name.startswith('get_method'):
        return 'methods'

    if name in ['fit_bkg', 'get_fit_results']:
        return 'fitting'

    if name in ['ignore2d_image', 'notice2d_image']:
        return 'filtering'

    if name in ['get_bkg_model', 'get_bkg_source',
                'get_model_pars', 'get_model_type',
                'get_num_par_frozen', 'get_num_par_thawed',
                'get_xsabund',
                'get_xscosmo',
                'get_xsxsect',
                'get_xsxset',
                'load_template_interpolator',
                'load_xstable_model',
                'get_xschatter', 'set_xschatter',
                'set_bkg_full_model']:
        return 'modeling'

    if name in ['get_sampler_name', 'get_sampler_opt',
                'get_stat_name']:
        return 'statistics'

    if name.startswith('plot_') or name.find('_plot') != -1:
        return 'plotting'

    if name.startswith('group') or \
       name in ['create_arf', 'create_rmf',
                'get_bkg_arf', 'get_bkg_rmf']:
        return 'data'

    if name in ['multinormal_pdf', 'multit_pdf']:
        return 'utilities'

    if name in ['get_data_contour', 'get_data_contour_prefs',
                'get_data_image', 'get_fit_contour',
                'get_kernel_contour', 'get_kernel_image',
                'get_model_contour', 'get_model_contour_prefs',
                'get_model_image',
                'get_psf_contour', 'get_psf_image',
                'get_ratio_contour', 'get_ratio_image',
                'get_resid_contour', 'get_resid_image',
                'get_source_contour', 'get_source_image']:
        return 'visualization'

    if name == 'get_functions':
        return 'info'

    return 'sherpaish'


def convert_docutils(name, doc, sig,
                     symbol=None, metadata=None, synonyms=None,
                     dtd='ahelp'):
    """Given the docutils documentation, convert to ahelp DTD.

    Parameters
    ----------
    name : str
    doc
        The document (resturctured text)
    sig : str or None
        The signature of the name (will be over-ridden by the
        document, if given).
    symbol
        The symbol to document (e.g. sherpa.astro.ui.load_table or
        sherpa.astro.ui.xsapec) or None.
    metadata : dict or None, optional
        The AHELP metadata for this file (the return value of
        parsers.ahelp.find_metadata).
    synonmys : list of str or None
        The synonums available for this symbol. It is expected that,
        if given, the array has one element but do not require it
        (but the array must not be empty if given).
    dtd : {'ahelp', 'sxml'}, optional
        The DTD to use.

    Returns
    -------
    ahelp
        The ahelp version of the documentation.

    Notes
    -----
    Should synonyms be added to the SYNTAX block?

    At the moment there is limited support for the "sxml" DTD - i.e.
    all that is changed is the top element; there is no attempt to
    take advantage of the extra features that the cxcdocumentationpage
    DTD affords.
    """

    if dtd not in ['ahelp', 'sxml']:
        raise ValueError("Unrecognized dtd value")

    assert synonyms is None or len(synonyms) > 0, synonyms

    # Basic idea is parse, augment/fill in, and then create the
    # ahelp structure, but it is likely this is going to get
    # confused.
    #
    nodes = list(doc)
    syntax, nodes = find_syntax(name, sig, nodes)
    synopsis, refkeywords, nodes = find_synopsis(nodes)
    desc, nodes = find_desc(nodes)

    # For XSPEC models, add a note about additive or multiplicative to
    # the SYNTAX block (could go in the description but let's try
    # here for now).
    #
    # TODO: XSConvolutionKernel/Model
    if isinstance(symbol, ModelWrapper) and \
       issubclass(symbol.modeltype, (XSAdditiveModel, XSMultiplicativeModel)):
        assert syntax is not None

        ElementTree.SubElement(syntax, 'LINE').text = ''

        mline = 'The {} model is '.format(name)
        if issubclass(symbol.modeltype, XSAdditiveModel):
            mline += 'an additive'
        elif issubclass(symbol.modeltype, XSMultiplicativeModel):
            mline += 'a multiplicative'
        else:
            raise RuntimeError("Unexpected XSPEC model component: {}".format(name))

        mline += ' model component.'
        ElementTree.SubElement(syntax, 'LINE').text = mline

    # Can have parameters and then a "raises" section, or just one,
    # or neither. Really they should both be before the See Also
    # block (are they automatically merged in this case?),
    # but that is not currently guaranteed (e.g. fake_pha)
    #
    # Note that I have edited fake_pha and plot_pvalue so that
    # fieldlist2 should now always be None, but this has not
    # yet made it into the distribution. So the assumption is
    # to skip fieldlist2 if set, but should probably have some
    # safety check to warn if it shouldn't be (i.e. contents are
    # not a raises block), and we also need to remove raises
    # from fieldlist1, as this isn't wanted for ahelp.
    #
    # ^^^ The paragraph above needs reviewing for CIAO 4.12
    #
    fieldlist1, nodes = find_fieldlist(nodes)

    warnings, nodes = find_warning(nodes)

    seealso, nodes = find_seealso(nodes)

    fieldlist2, nodes = find_fieldlist(nodes)

    if fieldlist2 is not None:
        sys.stderr.write(" - ignoring section fieldlist\n")

    # This has been separated fro the extraction of the field list
    # to support experimentation.
    #
    params = extract_params(fieldlist1)
    add_synonyms_to_syntax(syntax, synonyms)
    add_pars_to_syntax(syntax, fieldlist1)

    # support see-also here
    #
    if seealso is None:
        seealso, nodes = find_seealso(nodes)
        if seealso is not None:
            print(" - seealso is in wrong place")

    notes, nodes = find_notes(name, nodes)

    # hack to merge notes if duplicate (seen in testing; should be fixed
    # in the docstring)
    #
    notes2, nodes = find_notes(name, nodes)
    if notes2 is not None:
        print(" - error, multiple NOTES sections")

    refs, nodes = find_references(nodes)
    examples, nodes = find_examples(nodes)

    # Do we augment the examples?
    #
    examples = augment_examples(examples, symbol)

    if refs is None:
        refs, nodes = find_references(nodes)
        if refs is not None:
            print(" - References after EXAMPLES")

    # assert nodes == [], nodes
    if nodes != []:
        sys.stderr.write(" - ignoring trailing:\n{}\n".format(nodes))
        return nodes

    # Augment the blocks
    #
    if syntax is None:
        # create the syntax block
        sys.stderr.write("TODO: does {} need a SYNTAX block?\n".format(name))

    # Try and come up with an automated 'See Also' solution
    #
    seealsotags, displayseealsotags = create_seealso(name, seealso)

    # Create the output
    #
    rootname = None
    if dtd == 'ahelp':
        rootname = 'cxchelptopics'
    elif dtd == 'sxml':
        rootname = 'cxcdocumentationpage'
    else:
        raise RuntimeError('unknown dtd={}'.format(dtd))

    root = ElementTree.Element(rootname)
    outdoc = ElementTree.ElementTree(root)

    xmlattrs = {'pkg': 'sherpa',
                'key': name,
                'refkeywords': ' '.join(refkeywords),
                'seealsogroups': seealsotags,
                'displayseealsogroups': displayseealsotags,
                'context': None
                }

    if metadata is not None:
        for k, v in metadata.items():
            if k in ['seealsogroups', 'displayseealsogroups']:
                continue

            assert k in xmlattrs

            # special case refkeywords to append to the existing
            # set
            #
            if k == 'refkeywords':
                # repeats aren't really a problem but clean them up
                # anyway
                newkeys = (xmlattrs[k] + ' ' + v).split()
                newkeys = sorted(list(set(newkeys)))
                xmlattrs[k] = ' '.join(newkeys)
            else:
                xmlattrs[k] = v

    if xmlattrs['context'] is None:
        context = find_context(name, symbol)
        xmlattrs['context'] = context
        if context == 'sherpaish':
            print(" - fall back context=sherpaish for {}".format(name))

    # Add in any synonyms to the refkeywords (no check is made to
    # see if they are already there).
    #
    if synonyms is not None:
        xmlattrs['refkeywords'] = ' '.join(synonyms) + ' ' + \
                                  xmlattrs['refkeywords']

    entry = ElementTree.SubElement(root, 'ENTRY', xmlattrs)

    for n in [synopsis, syntax, desc, examples, params,
              warnings, notes, notes2, refs]:
        if n is None:
            continue

        entry.append(n)

    # Add the "standard" postamble.
    #
    # VERY HACKY way to determine talking about an XSPEC routine
    #
    if name.find('xs') != -1:
        xspec = ElementTree.SubElement(entry, 'ADESC',
                                       {'title': 'XSPEC version'})
        xpara = ElementTree.SubElement(xspec, 'PARA')
        xpara.text = 'CIAO 4.12 comes with support for version ' + \
                     '12.10.1n of the XSPEC models. This can be ' + \
                     'checked with the following:'

        cstr = "% python -c 'from sherpa.astro import xspec; " + \
               "print(xspec.get_xsversion())'"

        xpara2 = ElementTree.SubElement(xspec, 'PARA')
        xsyn = ElementTree.SubElement(xpara2, 'SYNTAX')
        ElementTree.SubElement(xsyn, 'LINE').text = cstr
        ElementTree.SubElement(xsyn, 'LINE').text = '12.10.1n'

    bugs = ElementTree.SubElement(entry, 'BUGS')
    para = ElementTree.SubElement(bugs, 'PARA')
    para.text = 'See the '
    attrs = {'link': 'https://cxc.harvard.edu/sherpa/bugs/'}
    link = ElementTree.SubElement(para, 'HREF', attrs)
    link.text = 'bugs pages on the Sherpa website'
    link.tail = ' for an up-to-date listing of known bugs.'

    ElementTree.SubElement(entry, 'LASTMODIFIED').text = 'December 2020'

    return outdoc
