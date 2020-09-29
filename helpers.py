"""Utility routines."""

import os
import sys

from xml.etree import ElementTree

from sherpa.ui.utils import ModelWrapper
from sherpa.astro.xspec import XSModel, XSAdditiveModel, XSMultiplicativeModel, XSConvolutionKernel
from sherpa.astro import ui

from parsers.ahelp import find_metadata
from parsers.docutils import merge_metadata


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


def is_xspec_1211_model(sym):
    """Is this a model introduced in XSPEC 12.11.0?"""

    if sym.__doc__ is None:
        return False

    return sym.__doc__.find('This model is only available when used with XSPEC 12.11.0 or later.') > -1


def add_model_list(caption, models, xspec=True):
    """Return a TABLE element describing the models."""

    tbl = ElementTree.Element('TABLE')
    ElementTree.SubElement(tbl, 'CAPTION').text = caption

    is_convolution = isinstance(getattr(ui, models[0]).modeltype(), XSConvolutionKernel)

    row0 = ElementTree.SubElement(tbl, 'ROW')

    has_new = False
    if xspec and is_convolution:
        has_new = True

    if 'voigt1d' in models:
        has_new = True

    if has_new:
        ElementTree.SubElement(row0, 'DATA').text = 'New'

    ElementTree.SubElement(row0, 'DATA').text = 'Model name'
    ElementTree.SubElement(row0, 'DATA').text = 'Description'

    for name in sorted(models):
        sym = getattr(ui, name).modeltype
        desc = sym.__doc__.split("\n")[0]

        # Unfortunately for CIAO 4.13 we need to stay with XSPEC 12.10.1,
        # so we have to ignore the 12.11.0 models.
        #
        if is_xspec_1211_model(sym):
            raise RuntimeError(f"SHOULD NOT HAVE GOT HERE: {name}")

        # Assume it is 'The XSPEC <> model: ...' but note that <> is
        # not necessarily the <> name (it should be)
        #
        hdr = 'The XSPEC {} model: '.format(name[2:])
        hdr2 = 'The XSPEC {} convolution model: '.format(name[2:])
        if desc.lower().startswith(hdr.lower()):
            desc = desc[len(hdr):]
        elif desc.lower().startswith(hdr2.lower()):
            desc = desc[len(hdr2):]

        # else:
        #     sys.stderr.write("Name mis-match {} vs {}\n".format(name, desc))
        #     idx = desc.find(': ')
        #     if idx == -1:
        #         raise ValueError(desc)
        #
        #     desc = desc[idx + 2:]

        row = ElementTree.SubElement(tbl, 'ROW')

        # HACKY way to determine if this is new or not - I would like to
        # query the model's metadata but we don't encode this information.
        # So I just have to look for the string
        # 'This model is only available when used with XSPEC 12.11.0 or later.'
        # OR if this is a convolution kernel
        #
        """
        if xspec:
            # We don't have the 12.11.0 models in CIAO 4.13
            #
            # new = isinstance(sym(), XSConvolutionKernel) or sym.__doc__.find('This model is only available when used with XSPEC 12.11.0 or later.') > -1

            new = isinstance(sym(), XSConvolutionKernel)

            ElementTree.SubElement(row, 'DATA').text = 'NEW' if new else ''
        """

        if xspec and is_convolution:
            ElementTree.SubElement(row, 'DATA').text = 'NEW'
        elif has_new:
            ElementTree.SubElement(row, 'DATA').text = 'NEW' if name in ['pseudovoigt1d', 'voigt1d'] else ''

        ElementTree.SubElement(row, 'DATA').text = name
        ElementTree.SubElement(row, 'DATA').text = desc

    return tbl


def list_xspec_models(outdir, dtd='ahelp'):
    """Create the xs ahelp page.

    Parameters
    ----------
    outdir : string
        The output directory, which must already exist.
    dtd : {'ahelp', 'sxml'}, optional
        The DTD to use.

    Returns
    -------
    outfile
        The name of the file.
    """

    if not os.path.isdir(outdir):
        sys.stderr.write("ERROR: outdir={} does not exist\n".format(outdir))
        sys.exit(1)

    if dtd not in ['ahelp', 'sxml']:
        raise ValueError("Invalid dtd argument")

    # We loop through the ui symbols rather than directly inspect the
    # contents of sherpa.astro.xspec to make sure we are using the
    # UI-available names.
    #
    add_models = []
    mul_models = []
    con_models = []

    for name in dir(ui):

        sym = getattr(ui, name)
        if not isinstance(sym, ModelWrapper):
            continue

        mclass = sym.modeltype
        if is_xspec_1211_model(mclass):
            continue

        if issubclass(mclass, XSAdditiveModel):
            add_models.append(name)
        elif issubclass(mclass, XSMultiplicativeModel):
            mul_models.append(name)
        elif issubclass(mclass, XSConvolutionKernel):
            con_models.append(name)

    def check(label, models):
        if len(models) == 0:
            raise ValueError("Unable to find any {} models".format(label))

        unexpected = [n for n in models if not n.startswith('xs')]
        if len(unexpected) > 0:
            raise ValueError("{}: {}".format(label, unexpected))

    check('additive', add_models)
    check('multiplicative', mul_models)
    check('convolution', con_models)

    atbl = add_model_list('Additive XSPEC models', add_models)
    mtbl = add_model_list('Multiplicative XSPEC models', mul_models)
    ctbl = add_model_list('Convolution XSPEC models', con_models)

    rootname = None
    if dtd == 'ahelp':
        rootname = 'cxchelptopics'
    elif dtd == 'sxml':
        rootname = 'cxcdocumentationpage'
    else:
        raise RuntimeError('unknown dtd={}'.format(dtd))

    metadata = find_metadata('xs')
    if metadata is None:
        raise IOError('no ahelp for XS')

    xmlattrs = merge_metadata({'pkg': 'sherpa',
                               'key': 'xs',
                               'refkeywords': 'xspec models',
                               'seealsogroups': 'sh.models',
                               'displayseealsogroups': 'xsmodels',
                               'context': None},
                              metadata)

    if xmlattrs['context'] is None:
        raise IOError("No context for XS!")

    def add_para(parent, text, title=None):
        out = ElementTree.SubElement(parent, 'PARA')
        out.text = text
        if title is not None:
            out.set('title', title)

        return out

    xspec_major_version = '12.10.1'
    xspec_version = f'{xspec_major_version}s'

    root = ElementTree.Element(rootname)

    root.append(ElementTree.Comment("THIS IS AUTO-GENERATED TEXT"))

    outdoc = ElementTree.ElementTree(root)
    entry = ElementTree.SubElement(root, 'ENTRY', xmlattrs)
    ElementTree.SubElement(entry, 'SYNOPSIS').text = 'XSPEC model functions.'

    desc = ElementTree.SubElement(entry, 'DESC')

    add_para(desc, f'''Sherpa in CIAO 4.13 includes the "additive", "multiplicative", and "convolution"
    models of XSPEC version {xspec_version}, and are available by adding the prefix
    "xs" before the XSPEC model name (in lower case). As examples: in Sherpa the XSPEC
    phabs model is called "xsphabs", the vapec model is "xcvapec", and the cflux model
    is "xscflux".
    ''')

    add_para(desc, '''The additive (atable) and multiplicative (mtable) XSPEC
    table models are supported by the load_xstable_model command.''',
             title='XSPEC table models')

    add_para(desc, '''XSPEC models based on physical processes (e.g. line models
        such as raymond or absorption models such as wabs) assume that
        the dataspace is defined in keV.  On the other hand, Sherpa
        models are always calculated based on the input data scale.
        Thus when XSPEC models are combined with Sherpa models, the
        user should be careful to ensure that both components have the
        same dataspace units; otherwise, calculated model amplitudes
        may be incorrect.''',
             title='Important note:')

    add_para(desc, '''These models also expect that the x-values will always be
        energy bins.  When the analysis setting is using non-energy
        bins and an XSPEC model is defined, Sherpa converts the bins
        to energy before sending them to the XSPEC model.  After the
        XSPEC model finishes, Sherpa converts back to the original
        units. Sherpa also scales the model values appropriately
        (e.g., if counts/keV came out of the XSPEC model and Sherpa is
        working with wavelength, then Sherpa scales the output of the
        XSPEC model to counts/Angstrom).''')

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Unavailable XSPEC models')
    add_para(adesc, f'''The "smaug" model, "etable" table models, and the
        mixing-model components of XSPEC {xspec_version}
        are NOT included in CIAO.''')

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Available XSPEC models')
    para = add_para(adesc, f'''The available XSPEC models are listed below.  Refer to the
        ahelp page for each model (e.g. "ahelp xsabsori") or the ''')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', "https://heasarc.gsfc.nasa.gov/docs/xanadu/xspec/manual/manual.html")
    href.text = "XSPEC User's Guide"

    # ugly way to add this text
    href.tail = '''for more information.  Note that the ahelp
       files describe the version of the XSPEC model included in
       CIAO, while the XSPEC User's Guide may reference a newer
       version with different options. If the first column is labelled NEW then
       the model is new to CIAO 4.13.'''

    adesc.append(atbl)
    adesc.append(mtbl)
    adesc.append(ctbl)

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Parameter names')
    para = add_para(adesc, f'''Sherpa uses names, rather than numbers, to access parameter values (e.g.
        to set them, change whether a parameter is frozen, adjust the limits,
        or access the latest value). Prior to XSPEC version 12.9.0, the parameter
        names for the XSPEC models were not guaranteed to be valid Python
        symbols, and so Sherpa has converted the problematic names.
        The names used by Sherpa are given in the ahelp page for the model
        - e.g.''')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', "https://cxc.harvard.edu/sherpa/ahelp/xspowerlaw.html")
    href.text = "ahelp xspowerlaw"

    # add to end of href
    href.tail = "- and by printing the model component:"

    verb = ElementTree.SubElement(adesc, 'VERBATIM')
    verb.text = """
sherpa> set_source(xsphabs.gal * xspowerlaw.pl)
sherpa> print(gal)
xsphabs.gal
   Param        Type          Value          Min          Max      Units
   -----        ----          -----          ---          ---      -----
   gal.nH       thawed            1            0       100000 10^22 atoms / cm^2
sherpa> print(pl)
xspowerlaw.pl
   Param        Type          Value          Min          Max      Units
   -----        ----          -----          ---          ---      -----
   pl.PhoIndex  thawed            1           -2            9
   pl.norm      thawed            1            0        1e+24
    """

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Changing the chatter level of XSPEC models')

    add_para(adesc, '''The default chatter level for XSPEC models - i.e. how much information
        they will print to the screen when evaluated - is set to 0, which
        is lower than the default value used by XSPEC itself (10).
        To check that the model is being evaluated correctly - e.g.
        in case of a probem - then the set_xschatter routine can be
        used to change the level. For example:''')

    para = add_para(adesc, '')
    syntax = ElementTree.SubElement(para, 'SYNTAX')
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> set_xschatter(10)'
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> plot_fit()'
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> set_xschatter(0)'

    add_para(adesc, '''The current XSPEC chatter level is returned by the
        get_xschatter level.''')

    add_para(adesc, '''The Python docstrings for these functions provide more
        information, and can be read with the help() function:''')

    para = add_para(adesc, '')
    syntax = ElementTree.SubElement(para, 'SYNTAX')
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> help(set_xschatter)'
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> help(get_xschatter)'

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Accessing the XSPEC state')

    add_para(adesc, '''Several routines are provided to change (or report) the
        XSPEC state (i.e. settings that may influence the model
        calculations). These include (please use the Python help
        command for more information on these functions):''')

    add_para(adesc, 'The get_xsabund() and set_xsabund() routines.',
             title='Abundance')

    add_para(adesc, 'The get_xsxsect() and set_xsxsect() routines.',
             title='Cross section')

    add_para(adesc, 'The get_xscosmo() and set_xscosmo() routines.',
             title='Cosmology')

    add_para(adesc, '''The XSPEC SET command is handled by the set_xsxset()
        routine, and once a value is set it can be retrieved
        with get_xsxset().''',
             title='Using the SET command')

    add_para(adesc, '''The sherpa.astro.xspec module contains the get_xspath_manager()
        and get_xspath_model() to return the current paths to the
        XSPEC directories, and set_xspath_manager() to change the path.''',
             title='Manager and model paths')

    add_para(adesc, '''The sherpa.astro.xspec module contains the get_xsstate() and
        set_xsstate() routines which can be used to find and set all
        of the above values.''',
             title='All XSPEC settings')

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Checking the XSPEC module version')

    add_para(adesc, '''The XSPEC module contains the get_xsversion routine, which returns a string
        containing the XSPEC patch level used in Sherpa. As an example:''')

    para = add_para(adesc, '')
    syntax = ElementTree.SubElement(para, 'SYNTAX')
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> from sherpa.astro import xspec'
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> xspec.get_xsversion()'
    ElementTree.SubElement(syntax, 'LINE').text = f"'{xspec_version}'"

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Changes in CIO 4.13')

    add_para(adesc, '''The XSPEC models bave been updated to release 12.10.1s
    in CIAO 4.13, from version 12.10.1n in CIAO 4.12. Anyone who wants to use
    models from XSPEC 12.11.1 will have to use the standalone version of Sherpa.
    ''',
             title='XSPEC model updates')

    add_para(adesc, '''XSPEC convolution models, such as xscflux and xszashift,
    are now supported in Sherpa. Please review the ahelp files for these models
    as they behave somewhat differently to additive and multiplicative models.''',
             title='Convolution models')

    # Not yet ready
    # add_para(adesc, '''XSPEC models can now be regridded, that is, evaluated with a
    # finer energy response or cover a larer range than the instrument response.
    # The regrid method is used to create a new version of the model which evaluates
    # the model on the higher-resolution grid and then resamples it to match the
    # instrument model.''',
    #          title='Changing the energy grid of a model')

    bugs = ElementTree.SubElement(entry, 'BUGS')

    para = add_para(bugs, 'For a list of known bugs and issues with the XSPEC models, please visit the')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'https://heasarc.gsfc.nasa.gov/docs/xanadu/xspec/bugs.html')
    href.text = 'XSPEC bugs page.'

    add_para(bugs, '''To check the XSPEC version used by Sherpa, use the
    get_xsversion routine from the xspec module:''')

    para = add_para(bugs, '')
    syntax = ElementTree.SubElement(para, 'SYNTAX')
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> from sherpa.astro import xspec'
    ElementTree.SubElement(syntax, 'LINE').text = 'sherpa> xspec.get_xsversion()'
    ElementTree.SubElement(syntax, 'LINE').text = f"'{xspec_version}'"


    lastmod = ElementTree.SubElement(entry, 'LASTMODIFIED')
    lastmod.text = 'December 2020'

    suffix = 'sxml' if dtd == 'sxml' else 'xml'
    outfile = os.path.join(outdir, 'xs.{}'.format(suffix))
    save_doc(outfile, outdoc)

    return outfile


def list_sherpa_models(outdir, dtd='ahelp'):
    """Create the models ahelp page.

    Parameters
    ----------
    outdir : string
        The output directory, which must already exist.
    dtd : {'ahelp', 'sxml'}, optional
        The DTD to use.

    Returns
    -------
    outfile
        The name of the file.
    """

    if not os.path.isdir(outdir):
        sys.stderr.write("ERROR: outdir={} does not exist\n".format(outdir))
        sys.exit(1)

    if dtd not in ['ahelp', 'sxml']:
        raise ValueError("Invalid dtd argument")

    # Hard-coded list of names to exclude
    #
    excluded = ['arfmodel', 'arfmodelnopha', 'arfmodelpha',
                'rmfmodel', 'rmfmodelnopha', 'rmfmodelpha',
                'rspmodel', 'rspmodelnopha', 'rspmodelpha',
                'pileuprmfmodel',
                'multiresponsesummodel',
                'knninterpolator',
                'psfmodel',
                'convolutionmodel',
                'tablemodel',
                'template', 'templatemodel', 'usermodel',
                'integrate1d'  # WHAT TO DO ABOUT THIS
    ]

    models1 = []
    models2 = []
    for name in dir(ui):
        if name in excluded:
            continue

        sym = getattr(ui, name)
        if not isinstance(sym, ModelWrapper):
            continue

        mclass = sym.modeltype
        if issubclass(mclass, XSModel):
            continue

        if mclass.__doc__ is None:
            raise ValueError(f"Name={name}")

        if mclass.ndim == 1:
            models1.append(name)
        elif mclass.ndim == 2:
            models2.append(name)
        elif name in ['absorptionvoigt', 'emissionvoigt']:
            models1.append(name)
        else:
            raise ValueError((name, mclass.ndim))

    def check(label, models):
        if len(models) == 0:
            raise ValueError("Unable to find any {} models".format(label))

    check('sherpa 1D', models1)
    check('sherpa 2D', models2)

    stbl1 = add_model_list('One-dimensional Sherpa models', models1, xspec=False)
    stbl2 = add_model_list('Two-dimensional Sherpa models', models2, xspec=False)

    rootname = None
    if dtd == 'ahelp':
        rootname = 'cxchelptopics'
    elif dtd == 'sxml':
        rootname = 'cxcdocumentationpage'
    else:
        raise RuntimeError('unknown dtd={}'.format(dtd))

    metadata = find_metadata('models')
    if metadata is None:
        raise IOError('no ahelp for XS')

    xmlattrs = merge_metadata({'pkg': 'sherpa',
                               'key': 'models',
                               'refkeywords': 'sherpa models',
                               'seealsogroups': 'sh.models',
                               'displayseealsogroups': 'shmodels',
                               'context': None},
                              metadata)

    if xmlattrs['context'] is None:
        raise IOError("No context for XS!")

    def add_para(parent, text, title=None):
        out = ElementTree.SubElement(parent, 'PARA')
        out.text = text
        if title is not None:
            out.set('title', title)

        return out

    root = ElementTree.Element(rootname)

    root.append(ElementTree.Comment("THIS IS AUTO-GENERATED TEXT"))

    outdoc = ElementTree.ElementTree(root)
    entry = ElementTree.SubElement(root, 'ENTRY', xmlattrs)
    ElementTree.SubElement(entry, 'SYNOPSIS').text = 'Summary of Sherpa models (excluding XSPEC).'

    desc = ElementTree.SubElement(entry, 'DESC')

    para = add_para(desc, '''The following table lists most of the models available within Sherpa.
        See ''')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'https://cxc.harvard.edu/sherpa/ahelp/xs.html')
    href.text = '"ahelp xs"'

    href.tail = ' for those models provided by XSPEC, '

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'https://cxc.harvard.edu/sherpa/ahelp/tablemodel.html')
    href.text = '"ahelp tablemodel"'

    href.tail = ' for table models, and '

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'https://cxc.harvard.edu/sherpa/ahelp/load_user_model.html')
    href.text = '"ahelp load_user_model"'

    href.tail = ' for user-supplied models, respectively.'

    # Tables galore
    desc.append(stbl1)
    desc.append(stbl2)

    adesc = ElementTree.SubElement(entry, 'ADESC')
    adesc.set('title', 'Are models evaluated at a point or across a bin?')

    para = add_para(adesc, '''The integration of models in Sherpa is controlled by an
     integration flag in each model structure.  Refer to''')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'https://cxc.harvard.edu/sherpa/ahelp/integrate.html')
    href.text = '"ahelp integrate"'

    href.tail = ' for information on integrating model components.'

    bugs = ElementTree.SubElement(entry, 'BUGS')

    para = add_para(bugs, 'See the')

    href = ElementTree.SubElement(para, 'HREF')
    href.set('link', 'htps://cxc.harvard.edu/sherpa/bugs/')
    href.text = 'bugs pages on the Sherpa website'

    href.tail = ' for an up-to-date listing of known bugs.'

    lastmod = ElementTree.SubElement(entry, 'LASTMODIFIED')
    lastmod.text = 'December 2020'

    suffix = 'sxml' if dtd == 'sxml' else 'xml'
    outfile = os.path.join(outdir, 'models.{}'.format(suffix))
    save_doc(outfile, outdoc)

    return outfile
