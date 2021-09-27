#!/usr/bin/env python

"""

Usage:

  ./compare_ahelp_files xml_dir

Aim:

Check the ahelp files generated in xml_dir against the CIAO
setup. Checks are

 - if the file exists in both they "match", comparing
   key, pkg, context
 - if the file does not exist, note it
 - what sherpa ahelp files from CIAO are we missing?

"""

import glob
import os
import sys

from parsers.ahelp import find_metadata, read_metadata


def find_xml_files(indir):

    path = os.path.join(indir, '*.xml')
    matches = glob.glob(path)
    if len(matches) == 0:
        raise ValueError(f"Directory contains no XML files: {indir}")

    return matches


ciao_dir = os.getenv('ASCDS_INSTALL')
if ciao_dir is None:
    raise ImportError('ASCDS_INSTALL is not set!')


def check(xml_dir):

    for d in [ciao_dir, xml_dir]:
        if not os.path.isdir(d):
            raise ValueError(f"Not a directory: {d}")

    xml_files = find_xml_files(xml_dir)
    print(f"Processing {len(xml_files)} XML files.")
    nmatch = 0
    miss = []
    diff = []
    failed = []
    unknown = []
    found = set()
    for xmlfile in xml_files:
        name = os.path.basename(xmlfile)
        assert name.endswith('.xml')
        name = name[:-4]

        try:
            ahelp = find_metadata(name)
        except ValueError as ve:
            miss.append((name, str(ve)))
            continue
        except IOError as ie:
            msg = str(ie)
            if msg.startswith('Expected pkg=sherpa not'):
                diff.append((name, msg))
            else:
                failed.append((name, msg))
            continue

        new = read_metadata(xmlfile)

        def cmp(k):
            return new[k] == ahelp[k]

        flags = [cmp(k) for k in ['key', 'context']]
        if all(flags):
            nmatch += 1
            found.add(ahelp['key'])
        else:
            diff.append((name, flags))

    ahelp_dir = os.path.join(ciao_dir, 'share', 'doc', 'xml')
    ahelp_files = find_xml_files(ahelp_dir)
    for xmlfile in ahelp_files:
        name = os.path.basename(xmlfile)
        assert name.endswith('.xml')
        name = name[:-4]

        try:
            ahelp = find_metadata(name)
        except IOError as ie:
            msg = str(ie)
            if msg.startswith('Expected pkg=sherpa not '):
                continue

        key = ahelp['key']
        if key in found:
            continue

        unknown.append((name, key))

    if len(miss) > 0:
        print(f"# There were {len(miss)} new file(s).")

        flags = [m[1].startswith('Unable to find ahelp for ') for m in miss]
        if not all(flags):
            print(" - there are suprising errors")

        for i, m in enumerate(miss):
            print(f"  {i:2d}  name={m[0]}")

        print("")

    if len(diff) > 0:
        print(f"# There were {len(diff)} difference(s).")

    if len(failed) > 0:
        print(f"# There were {len(failed)} failure(s).")

    if len(unknown) > 0:
        print(f"# There were {len(unknown)} file(s) Sherpa found in CIAO but not new.")
        for i, (name, key) in enumerate(unknown):
            print(f"  {i:2d}  name={name}  key={key}")

if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.stderr.write(f"Usage: {sys.argv[0]} xml_dir\n")
        sys.exit(1)

    check(sys.argv[1])
