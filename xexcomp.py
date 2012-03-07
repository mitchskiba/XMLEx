#!/usr/bin/python3
import sys
from exparser import ExParser
from xml.dom import minidom
import optparse

parser = optparse.OptionParser(usage="inputfile outputfile")
parser.add_option("-l","--lib", dest="library",
                  action="append",help="library to consult for macros")
parser.add_option("--force-numeric",action="store_true", dest="numonly",
                  default=False, help="Force use of numeric capture groups only")
parser.add_option("-a","--lang", dest="language",
                  help='Language to target. Options are [ruby|python|.NET|pcre]',
                  default="ruby")

a,b = parser.parse_args()
if len(b)!=2:
    parser.print_help()
    exit()

e = ExParser(language=a.language, keep_names = not a.numonly)
if a.library:
    for filename in a.library:
        lib = minidom.parse(open(filename))
        if(lib.firstChild):
            e.process_dom(lib.firstChild)

target = minidom.parse(open(b[0]))
o = e.process_dom(target.firstChild,root=True)
o.render(open(b[1],'w'))
