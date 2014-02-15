#!/usr/bin/env python

"""
txt2opml.py -- convert plain text outlines to OPML

Adapted from: https://github.com/semk/Org2OPML/blob/master/org2opml.py
"""

import os
import re
import time
import datetime
import argparse
from lxml import etree


class Node(object):

    """
    An outline node and its children.
    """

    def __init__(self, text):
        self.text = text
        self.children = []

    def __iter__(self):
        return iter(self.children)

    def add_child(self, node):
        self.children.append(node)


def add_header(head, key, value):
    """
    Set the header key to value.
    """
    etree.SubElement(head, key).text = value


def stat_to_timestamp(s):
    """
    Convert UNIX epoch timestamp to RFC 822.
    """
    utc = time.gmtime(s)
    d = datetime.datetime(*(utc[:6]))
    return d.strftime('%a, %d %b %Y %H:%M:%S') + ' GMT'


def build_opml(nodes, meta, output):
    """
    Build a complete OPML document.
    """
    opml_root = etree.Element('opml', version='2.0')
    opml_head = etree.SubElement(opml_root, 'head')
    add_header(opml_head, 'title', meta['title'])
    add_header(opml_head, 'dateModified', meta['dateModified'])
    opml_body = etree.SubElement(opml_root, 'body')

    def process_children(parent, node):
        """
        Recursively attach each node's child to the parent.
        """
        for child in node:
            el = etree.SubElement(parent, 'outline', text=child.text)
            process_children(el, child)

    # For each summit, build a summit node then recursively attach its
    # children to it.
    for summit in nodes[0]:
        opml_summit = etree.SubElement(opml_body, 'outline', text=summit.text)
        process_children(opml_summit, summit)

    with open(output, 'wb') as fp:
        content = etree.tostring(opml_root, xml_declaration=True,
                                 pretty_print=True, encoding='UTF-8')
        fp.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    parser.add_argument('input')
    args = parser.parse_args()

    if not args.output:
        (base, ext) = os.path.splitext(args.input)
        args.output = base + '.opml'

    meta = {
        'title': args.output,
        'dateModified': stat_to_timestamp(os.stat(args.input).st_mtime),
    }
    nodes = []

    with open(args.input) as fp:
        for line in fp:
            if not line.strip(): continue

            match = re.search(r'^(\W+)? (.+)$', line)
            assert match, "'%s' didn't match regex" % line

            marker, text = match.groups()

            if len(marker) == 1:
                # If marker is a single char, its a summit node.
                level = 0
            elif ' ' in marker:
                # If using 'sparse' indentation, count the number of
                # double spaces as the level.
                level = marker.count('  ')
            else:
                # If using 'dense' indentation, count the number of
                # leading chars and subtract one to make it
                # zero-indexed.
                level = len(marker) - 1

            node = Node(text.strip())

            if level > 0:
                # If we're beyond the summits, go to the preceding level
                # and use the last appended node as the parent.
                parent = nodes[level - 1][-1]
                parent.add_child(node)

            # Add the current node to its level. Create a new list if
            # the level doesn't exist.
            try:
                nodes[level].append(node)
            except IndexError:
                nodes.append([node])

    build_opml(nodes, meta, args.output)

if __name__ == '__main__':
    main()
