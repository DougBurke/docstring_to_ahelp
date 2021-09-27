#!/usr/bin/env python

"""
Usage:

  ./doc2ahelp.py outdir [names]
     --debug
     --sxml
     --models

Aim:

Extract the docstring information from Sherpa and create ahelp XML
files for these symbols (functions, objects that we treat as
strings/functions in Sherpa, meta data created from these symbols).

The --sxml flag means that the output will use the "SXML" DTD
instead of the AHELP one (at present this only changes the name of
the root element, so there is no attempt to take advantage of the
extra functionality provided by the SXML DTD).

The script requires that a CIAO installation has been initialized,
since it is used to access the Sherpa documentation from

   sherpa.astro.ui
   sherpa.stats            CURRENTLY UNUSED
   sherpa.optmethods       CURRENTLY UNUSED

The ahelp files in the CIAO documentation are used to create the
ahelp metadata.

The following files are auto-created:

   models
   xs

The output is to outdir/<key>.<suffix> where <key> is based on the
"ahelp key" (it should be the same but may be different), and
<suffix> is 'xml' or 'sxml' depending on the DTD.

The script will over-write any existing file.

TODO:
  - indicate new/missing files

  - how to handle the known problem cases?

  - NEED TO ENSURE DO NOT OVERWRITE EXISTING AHELP FILES (THAT ARE
    NOT SHERPA)

"""

from collections import defaultdict
import os

from sherpa.ui.utils import ModelWrapper
from sherpa.astro import ui

from parsers.sherpa import sym_to_rst, sym_to_sig, unwanted, find_synonyms
from parsers.rst import parse_restructured
from parsers.docutils import convert_docutils
from parsers.ahelp import find_metadata

from helpers import save_doc, list_xspec_models, list_sherpa_models


def process_symbol(name, sym, dtd='ahelp',
                   ahelp=None, synonyms=None, debug=False):

    sherpa_doc = sym_to_rst(name, sym)
    if sherpa_doc is None:
        print("  - has no doc")
        return None

    sig, _ = sym_to_sig(name, sym)

    if debug:
        print("---- formats")
        print("-- Sherpa:\n{}".format(sherpa_doc))

    rst_doc = parse_restructured(name, sherpa_doc)
    if debug:
        print("-- RestructuredText:\n{}".format(rst_doc))

    doc = convert_docutils(name, rst_doc, sig, dtd=dtd,
                           symbol=sym, metadata=ahelp,
                           synonyms=synonyms)
    return doc


def convert(outdir, dtd='ahelp', modelsonly=False,
            skip_synonyms=False,
            debug=False, restrict=None):
    """Convert the symbols.

    Parameters
    ----------
    outdir : string
        The output directory, which must already exist.
    dtd : {'ahelp', 'sxml'}, optional
        The DTD to use for the output
    modelsonly : bool, optional
        Only process Sherpa models (this will subset any values given
        in the restrict parameter if both are specified).
    skip_synonyms : bool, optional
        Should synonyms be skipped or not?
    debug : optional, boool
        If True then print out parsed versions of the symbols
        (expected to be used when restrict is not None but this
        is not enforced).
    restrict : optional, None or list of str
        The set of symbols to use (if not all).
    """

    if not os.path.isdir(outdir):
        sys.stderr.write("ERROR: outdir={} does not exist\n".format(outdir))
        sys.exit(1)

    if dtd not in ['ahelp', 'sxml']:
        raise ValueError("Invalid dtd argument")

    synonyms, originals = find_synonyms()

    # Restrict the symbols that get processed
    #
    names = sorted(list(ui.__all__))
    to_process = []
    for name in names:

        if restrict is not None and name not in restrict:
            continue

        print("# {}".format(name))

        sym = getattr(ui, name)

        if modelsonly and not isinstance(sym, ModelWrapper):
            print(" - skipping as not a model")
            continue

        if unwanted(name, sym):
            print(" - skipping as unwanted")
            continue

        if name in synonyms and skip_synonyms:
            print(" - skipping as a synonym for {}".format(synonyms[name]))
            continue

        # Skip AbsorptionVoigt and EmissionVoigt from the list
        #
        if name in ['absorptionvoigt', 'emissionvoigt']:
            print(' - skipping absorption/emissionvoigt symbols')
            continue

        to_process.append(name)

    # Find potential mappings to identify multi-keyword files.
    # We could store the find_metadata call to avoid calling it twice,
    # but let's not bother.
    #
    filemaps = defaultdict(set)
    for name in to_process:

        sym = getattr(ui, name)

        try:
            syn_names = originals[name]
        except KeyError:
            syn_names = None

        if name in synonyms:
            # We want to treat this as if the synonym is the
            # other way around (to get the 'Synonym: ...' output
            # included).
            #
            assert syn_names is None
            syn_names = [synonyms[name]]

        try:
            ahelp = find_metadata(name, synonyms=syn_names)
        except ValueError as exc:
            continue

        # we want to store a mapping from the keyword to this file
        #
        for key in ahelp['refkeywords'].split(' '):
            key = key.lower()
            if key in to_process and key != name:
                filemaps[key].add(name)

    nproc = 0
    error_list = []
    for name in to_process:

        print("## {}".format(name))

        sym = getattr(ui, name)

        try:
            syn_names = originals[name]
        except KeyError:
            syn_names = None

        if name in synonyms:
            # We want to treat this as if the synonym is the
            # other way around (to get the 'Synonym: ...' output
            # included).
            #
            assert syn_names is None
            syn_names = [synonyms[name]]

        try:
            ahelp = find_metadata(name, synonyms=syn_names)
        except ValueError as exc:

            # See if we can use the "parent" ahelp file. This is based on
            # the assumption that for multi-command ahelp files the
            # refkeywords would contain the "other" commands (those
            # extra ones documented in the file), and so hopefully
            # we can use the mapping we created to identify these
            # commands.
            #
            fmaps = list(filemaps[name])
            if len(fmaps) == 1:
                ahelp = find_metadata(fmaps[0])
                if ahelp is None:
                    raise ValueError("Expected to have a usable metadata copy!")
                else:
                    print(f" - using metadata from {fmaps[0]}")
                    ahelp['key'] = name  # important!
            else:
                print(" - ahelp metadata skipped as {}".format(exc))
                ahelp = None

        try:
            xml = process_symbol(name, sym, dtd=dtd, ahelp=ahelp,
                                 synonyms=syn_names,
                                 debug=debug)
        except Exception as exc:
            print(" - ERROR PROCESSING: {}".format(exc))
            error_list.append(name)
            continue

        if xml is None:
            continue

        out_name = 'group_sherpa' if name == 'group' else name
        suffix = 'sxml' if dtd == 'sxml' else 'xml'
        outfile = os.path.join(outdir, '{}.{}'.format(out_name, suffix))
        save_doc(outfile, xml)
        print("Created: {}".format(outfile))
        nproc += 1

    nskip = len(names) - nproc
    print("\nProcessed {} files, skipped {}.".format(nproc, nskip))
    if error_list != []:
        print("Errored out: {}".format(error_list))

    # Create the model lists:
    #    models.suffix
    #    xs.suffix
    #
    print("\nAlso:")
    for outfile in [list_sherpa_models(outdir, dtd=dtd),
                    list_xspec_models(outdir, dtd=dtd)]:
        print(f"  {outfile}")

    print("")

    """

    # extra symbols
    #   statistics
    #   optimisers
    #
    # Be very-restrictive on the accepted symbols
    #
    statnames = ui.list_stats()
    statnames.remove('userstat')  # explicitly remove
    for name in dir(sherpa.stats):
        if not name[0].isupper():
            # this check is only realy needed for methods but include it
            continue

        lname = name.lower()
        if lname not in statnames:
            continue

        symbol = getattr(sherpa.stats, name)
        doit(lname, symbol)

    optnames = ui.list_methods()
    for name in dir(sherpa.optmethods):
        if not name[0].isupper():
            continue

        lname = name.lower()
        if lname not in optnames:
            continue

        symbol = getattr(sherpa.optmethods, name)
        doit(lname, symbol)

    """


help_str = """Convert Sherpa docstrings into CIAO ahelp files."""

if __name__ == "__main__":

    import argparse
    import sys

    import stk

    parser = argparse.ArgumentParser(description=help_str,
                                     prog=sys.argv[0])

    parser.add_argument("outdir",
                        help="Files are written to this directory (must exist)")

    parser.add_argument("names", nargs='?', default=None,
                        help="Restrict to these names (stack syntax)")

    parser.add_argument("--debug", action="store_true",
                        help="Print out parsed output")
    parser.add_argument("--sxml", action="store_true",
                        help="Use the SXML rather than AHELp dtd")
    parser.add_argument("--models", action="store_true",
                        help="Restrict to Sherpa models only")

    args = parser.parse_args(sys.argv[1:])
    restrict = args.names
    if restrict is not None:
        restrict = stk.build(restrict)

    dtd = 'sxml' if args.sxml else 'ahelp'

    convert(args.outdir, dtd=dtd, modelsonly=args.models,
            debug=args.debug,
            restrict=restrict)
