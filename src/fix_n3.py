"""
Fix N3 files with IRIs including spaces.

Regardless of how one reads the specs, Blazegraph just wont load such files.

And while one can read exceptions and manually fix things, there are limits to this approach.

That limit for me was chem2bio2rdf's kegg.n3 which is full of spaces in IRIs.
"""
import rdflib
import os
import sys
from rdflib import URIRef, Graph, Namespace
from rdflib.plugins.parsers.notation3 import N3Parser

path = sys.argv[1]
g = Graph()
result = g.parse(file=open(path, "r"), format="n3")

i = 0
def format_n3 (i):
    result = None

    i = i.replace ('"', '\\"')

    if ' ' in i and o.startswith ('http'):
        i = i.replace (' ', '_')
    if i.startswith ('http'):
        result = '<{}>'.format (i)
    else:
        result = '"{}"'.format (i)
    return result

new_path = "{0}{1}".format (path, '.new')
with open (new_path, 'w') as stream:
    for s,p,o in g:
        s = format_n3 (s)
        p = format_n3 (p)
        o = format_n3 (o)
        stream.write ("{0} {1} {2} .\n".format (s,p,o))

