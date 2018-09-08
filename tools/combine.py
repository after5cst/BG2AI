#! /usr/bin/env python3
import argparse
import collections
from copy import deepcopy
import json
import logging
import os
from pprint import pprint, pformat
import re
import shutil
import sys

from substituter import Substituter

_this_dir = os.path.dirname(os.path.realpath(__file__))


def replace_single_quotes_with_double_outside_comment(data: str) -> str:
    """"
    Replace single quotes in non-comment with double quotes.
    Returns the string with replacements
    """
    logging.debug("rsq: {}".format(pformat(data)))
    r = re.compile(r"^(.*)\/\/.*$|^(.*)$", re.MULTILINE)
    matches = [m.span(m.lastindex) for m in r.finditer(data)]
    for start, end in matches:
        before = data[:start]
        mid = data[start:end]
        after = data[end:]
        mid = mid.replace("'", '"')
        data = before + mid + after
    return data


def convert_actions_to_text(weight: int, actions: list, fields_in: dict) -> list:
    """
    Convert a list of actions into a list of strings.
    :param weight: The weight of the response block.
    :param actions: The list of actions for that weight.
    :param fields_in: A dict of field values.
    :return: a list of strings.
    """
    lines = ["RESPONSE #{}".format(weight)]
    for action in actions:
        if isinstance(action, dict):
            assert 1 == len(action), "Detected dict with multiple trigger keys"
            key, value = action.popitem()

            if value:
                value.update(fields_in)
            else:
                value = fields_in

            template = Substituter(key)
            template_lines = template.expand(value)
            for template_line in template_lines:
                lines.append('\t' + template_line)

        elif isinstance(action, str):
            for key, value in fields_in.items():
                search_term = "<{}>".format(key)
                action = action.replace(search_term, value)
            lines.append('\t' + action)
        else:
            assert False, "Action contains unknown type"

    out = list()
    for line in lines:
        line = '\t' + replace_single_quotes_with_double_outside_comment(line)
        out.append(line)
    return out


def convert_triggers_to_text(source_in: list, fields_in: dict, in_or: bool=False) -> list:
    """
    Convert a list of triggers into a list of strings.
    :param source_in: The list of triggers from the JSON.
    :param fields_in: A dict of substitutable fields.
    :param in_or: If True, then processing statements from an OR
    :return: a list of strings.
    """
    lines = list()

    deque = collections.deque(source_in)

    while deque:
        item = deque.popleft()
        if isinstance(item, list):
            logging.debug("T2T: LIST {}".format(pformat(item)))
            logging.debug("Converting OR block to text")
            assert not in_or, "Nested OR block found"
            # A list within a list is an OR block.
            or_lines = convert_triggers_to_text(item, fields_in, True)
            or_statement = "OR({})".format(len(or_lines))
            while or_lines:
                deque.appendleft(or_lines.pop())
            deque.appendleft(or_statement)

        elif isinstance(item, dict):
            logging.debug("T2T: DICT {}".format(pformat(item)))
            assert 1 == len(item), "Detected dict with multiple trigger keys"
            key, value = item.popitem()
            if value:
                value.update(fields_in)
            else:
                value = fields_in

            data = Substituter(key).expand(value)
            while data:
                deque.appendleft(data.pop())

        elif isinstance(item, str):
            logging.debug("T2T: STR {}".format(pformat(item)))
            lines += [item]
        else:
            assert False, "Trigger contains unknown type"
        logging.debug("T2T: END {}".format(pformat(item)))

    out = list()
    for line in lines:
        line = '\t' + replace_single_quotes_with_double_outside_comment(line)
        out.append(line)
    return out


def convert_json_to_baf(source: dict) ->str:
    """
    Return a BAF string that represents the JSON provided.
    """
    if 1 < len(source["fields"]):
        if "name" in source:
            logging.info ("Combining multi-part {} ({})".format(
                source["name"], len(source["fields"])
            ))
        else:
            logging.info ("Combining multi-part <unnamed> ({})".format(
                len(source["fields"])
            ))
    else:
        if "name" in source:
            logging.info ("Combining single-part {} ({})".format(
                source["name"], len(source["fields"])
            ))
        else:
            logging.info ("Combining single-part <unnamed> ({})".format(
                len(source["fields"])
            ))

    result = ""

    for fields in source["fields"]:
        fields = deepcopy(fields)
        logging.debug("Handling fields {}".format(pformat(fields)))
        out = ["IF"] + convert_triggers_to_text(
            deepcopy(source["if"]), fields)

        out.append("THEN")

        for item in source["then"]:
            item = deepcopy(item)
            assert 1 == len(item), "Detected dict with multiple action keys"
            key, value = item.popitem()
            weight = int(key)
            out = out + convert_actions_to_text(weight, value, fields)

        out.append("END")
        result = result + '\n'.join(out) + '\n\n'
    return result


def combine_file(source_dir: str, target_file: str):
    """Take snippets and put them back together"""
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
                logging.info("Processing file '{}'".format(file))
                # fout.write("// {}\n".format(file))
                # data = fin.read()
                data = convert_json_to_baf(json.load(fin))
                fout.write(data)


if __name__ == "__main__":
    source = os.path.join(_this_dir, "..", "BDDEFAI")
    source = os.path.realpath(source)
    target = source + ".TXT"

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0)

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
