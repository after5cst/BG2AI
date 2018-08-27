#! /usr/bin/env python
import argparse
import logging
import os
import shutil
import sys

_this_dir =  os.path.dirname(os.path.realpath(__file__))


def split_file(source_file: str, target_dir: str):
    """Split a script file into component pieces"""
    logging.info("Creating directory '{}'".format(target))
    os.makedirs(target_dir)

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
    split_file(source, target)
