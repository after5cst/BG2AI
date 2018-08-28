#! /usr/bin/env python3
import argparse
import logging
import os
from pprint import pprint
import re
import shutil
import sys

_this_dir = os.path.dirname(os.path.realpath(__file__))


def combine_file(source_dir: str, target_file: str):
    """Take snippets and put them back toggether"""
    logging.info("Sorting directory '{}'".format(source_dir))
    files = []
    for file in os.listdir(source_dir):
        file = os.path.join(source_dir, file)
        logging.debug("Examining '{}'".format(file))
        if os.path.isfile(file) and file.endswith(".txt"):
            files.append(file)

    if 0 == len(files):
        logging.warning("No files found for combine")
        return

    files.sort()

    logging.debug("Writing file '{}'".format(target_file))
    with open(target_file, "w") as fout:
        for file in files:
            with open(file) as fin:
                # fout.write("// {}\n".format(file))
                data = fin.read()
                fout.write(data)
                fout.write('\n\n')


if __name__ == "__main__":
    source = os.path.join(_this_dir, "..", "BDDEFAI")
    source = os.path.realpath(source)
    target = source + ".TXT"

    parser = argparse.ArgumentParser()
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

    combine_file(source, target)
