#! /usr/bin/env python
import argparse
import logging
import os
from pprint import pprint
import re
import shutil
import sys

_this_dir = os.path.dirname(os.path.realpath(__file__))

# This breaks a file into a series of statements
_stmt_regex = r"(?P<statement>IF(.|\n)*?END)"
# This breaks a statement into an if and a then block
_if_then_regex = r"(?P<statement>IF(?P<if>(.|\n)*?)^THEN$(?P<then>(.|\n)*?)END)"


def split_file(source_file: str, target_dir: str) -> list:
    """Split a script file into component pieces"""
    logging.info("Creating directory '{}'".format(target))
    os.makedirs(target_dir)

    logging.debug("Loading file '{}'".format(source_file))
    with open(source_file) as f:
        source_text = f.read()
    logging.debug("Read {} bytes".format(len(source_text)))

    r = re.compile(_stmt_regex)
    count = 0
    outputs = []
    for m in r.finditer(source_text):
        count = count + 1
        output_name = os.path.join(target_dir, "{:03}.txt".format(count))
        with open(output_name, "w") as f:
            f.write(m.groupdict()["statement"])
        outputs.append(output_name)
    logging.info("Found {} statements".format(count))

    return outputs


def split_if_then(source_file: str) -> dict:
    """Split a script file into component pieces"""
    logging.debug("Splitting '{}' into IF/THEN blocks".format(source_file))
    with open(source_file) as f:
        source_text = f.read()
    logging.debug("Read {} bytes".format(len(source_text)))

    r = re.compile(_if_then_regex, flags=re.MULTILINE)
    count = 0
    output = {}
    for m in r.finditer(source_text):
        count = count + 1
        pprint(m.group('if'))
        # output = dict(m.group_dict())

    if count > 1:
        raise RuntimeError("IF/THEN Parse found multiple matches in '{}'"
                           .format(source_file))
    return output


if __name__ == "__main__":
    source = os.path.join(_this_dir, "..", "BDDEFAI.TXT")
    source = os.path.realpath(source)
    target = os.path.splitext(source)[0]

    parser = argparse.ArgumentParser()
    parser.add_argument('--auto_delete', action='store_true', default=True)
    parser.add_argument('-v', '--verbose', action='count', default=logging.DEBUG)

    args = parser.parse_args()
    if args.verbose == 0:
        level = logging.WARNING
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(stream=sys.stdout, level=level)
    logging.info("Verbosity = {}".format(logging.getLevelName(level)))
    logging.info("Source = '{}'".format(source))
    logging.info("Target = '{}'".format(target))

    if args.auto_delete and os.path.isdir(target):
        logging.warning("Removing directory '{}'".format(target))
        shutil.rmtree(target, ignore_errors=True)
    files = split_file(source, target)

    for file in files:
        if_then = split_if_then(file)
        pprint(if_then)
        break
