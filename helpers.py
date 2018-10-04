"""Utility routines."""

import os


def save_doc(outfile, xmldoc):
    """Write the ahelp XML to a file."""

    # See https://stackoverflow.com/a/43922805
    #
    with open(outfile, 'wb') as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>'.encode('utf8'))
        f.write('<!DOCTYPE cxchelptopics SYSTEM "CXCHelp.dtd">'.encode('utf8'))
        xmldoc.write(f, 'utf-8')
