#! /usr/bin/env python3
import argparse
import json
import logging
import os
from pprint import pprint
import re
import shutil
import sys

from triggers import TriggerTemplate

_this_dir = os.path.dirname(os.path.realpath(__file__))


def replace_single_quotes_with_double_outside_comment(data: str) -> str:
    """"
    Replace single quotes in non-comment with double quotes.
    Returns the string with replacements
    """
    r = re.compile(r"^(.*)\/\/.*$|^(.*)$", re.MULTILINE)
    matches = [m.span(m.lastindex) for m in r.finditer(data)]
    for start, end in matches:
        before = data[:start]
        mid = data[start:end]
        after = data[end:]
        mid = mid.replace("'", '"')
        data = before + mid + after
    return data


def convert_actions_to_text(weight:int, actions:list) -> list:
    """
    Convert a list of actions into a list of strings.
    :param weight: The weight of the response block.
    :param actions: The list of actions for that weight.
    :return: a list of strings.
    """
    lines = ["RESPONSE #{}".format(weight)]
    for action in actions:
        if isinstance(action, str):
            lines.append('\t' + action)
        else:
            assert False, "Action contains unknown type"

    out = list()
    for line in lines:
        line = '\t' + replace_single_quotes_with_double_outside_comment(line)
        out.append(line)
    return out


def convert_triggers_to_text(source: list, in_or: bool=False) -> list:
    """
    Convert a list of triggers into a list of strings.
    :param source: The list of triggers from the JSON.
    :param in_or: If True, then processing statements from an OR
    :return: a list of strings.
    """
    lines = list()
    for item in source:
        if isinstance(item, dict):
            assert 1 == len(item), "Detected dict with multiple trigger keys"
            key, value = item.popitem()
            if key.upper() == "OR":
                or_lines = convert_triggers_to_text(value, True)
                lines.append("OR({})".format(len(or_lines)))
                lines += or_lines
            else:
                templ = TriggerTemplate(key)
                template_lines = templ.expand(value)
                lines += template_lines
        elif isinstance(item, str):
            lines.append(item)
        else:
            assert False, "Trigger contains unknown type"

    out = list()
    for line in lines:
        line = '\t' + replace_single_quotes_with_double_outside_comment(line)
        out.append(line)
    return out


def convert_json_to_baf(source: dict) ->str:
    """
    Return a BAF string that represents the JSON provided.
    """
    out = ["IF"] + convert_triggers_to_text(source["if"])

    out.append("THEN")

    for item in source["then"]:
        assert 1 == len(item), "Detected dict with multiple action keys"
        key, value = item.popitem()
        weight = int(key)
        out = out + convert_actions_to_text(weight, value)

    out.append("END")
    return '\n'.join(out) + '\n\n'


def combine_file(source_dir: str, target_file: str):
    """Take snippets and put them back toggether"""
    logging.info("Sorting directory '{}'".format(source_dir))
    files = []
    for file in os.listdir(source_dir):
        file = os.path.join(source_dir, file)
        logging.debug("Examining '{}'".format(file))
        if os.path.isfile(file) and file.endswith(".json"):
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
                # data = fin.read()
                data = convert_json_to_baf(json.load(fin))
                fout.write(data)


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
