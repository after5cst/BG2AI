#! /usr/bin/env python3
import argparse
import json
import logging
import os
import pprint
import re
import shutil
import sys

from substituter import Substituter
from globals import tools_dir, project_name


# This breaks a statement into an if and a then block
_if_then_regex = r"(?P<statement>IF(?P<if>(.|\n)*?)^THEN$(?P<then>(.|\n)*?)END)"


def _load_templates(which: str):
    """
    Return a list of applicable templates
    :param which: Which template set to load, "if" or "then"
    """
    out = []
    dir_name = os.path.join(tools_dir, "..", project_name, which)
    for file_name in os.listdir(dir_name):
        prefix, suffix = os.path.splitext(file_name)
        if ".json" == suffix:
            out.append(Substituter(prefix))
    out.sort(key=lambda x: x.line_count(), reverse=True)

    for item in out:
        logging.debug("{} : {} lines".format(item.template.name,
                                             item.line_count()))
    return out


def promote_trigger(source: list, trigger: str) -> list:
    """Move items matching the trigger regex to the start of the returned list"""
    result = []
    r = re.compile(trigger)
    for item in source:
        if isinstance(item, str) and r.match(item):
            result = [item] + result
        else:
            result.append(item)
    return result


def split_file(source_file: str, target_dir: str) -> list:
    """Split a script file into component pieces"""
    logging.info("Creating directory '{}'".format(target_dir))
    os.makedirs(target_dir)

    logging.debug("Loading file '{}'".format(source_file))
    with open(source_file) as f:
        source_text = f.read()
    logging.debug("Read {} bytes".format(len(source_text)))

    r = re.compile(_if_then_regex, flags=re.MULTILINE)
    count = 0
    outputs = []
    for m in r.finditer(source_text):
        count = count + 1
        # It's not json... yet.  But it will be after split_if_then.
        output_name = os.path.join(target_dir, "{:04}.json".format(count*10))
        with open(output_name, "w") as f:
            f.write(m.groupdict()["statement"])
        outputs.append(output_name)
    logging.info("Found {} statements".format(count))

    return outputs


def replace_double_quotes_with_single_outside_comment(data: str) -> str:
    """"
    Replace double quotes in non-comment with single quotes.
    Returns the string with replacements
    """
    r = re.compile(r"^(.*)\/\/.*$|^(.*)$", re.MULTILINE)
    matches = [m.span(m.lastindex) for m in r.finditer(data)]
    for start, end in matches:
        before = data[:start]
        mid = data[start:end]
        after = data[end:]
        assert "'" not in mid
        mid = mid.replace('"', "'")
        data = before + mid + after
    return data


def get_name_from_actions(regex, actions: list):
    """
    Return the name from a set of actions, using a regular expression.
    :param regex:  The regular expression to be used.
    :param actions:  The list of actions
    :return:  The NAME parameter from the regular expression, or None
    """
    for action in actions:
        assert 1 == len(action)
        lines = action[list(action.keys())[0]]
        for line in lines:
            if isinstance(line, str):
                m = regex.match(line)
                if m:
                    groupdict = m.groupdict()
                    if 'NAME' in groupdict:
                        return groupdict['NAME']
            else:
                assert isinstance(line, dict), "Bad entry in action list"
    return None


def get_name(actions: list):
    """
    Return the 'name' of the block if it can be parsed from triggers.
    :param actions: The actions list to interrogate
    :return: The name or None
    """
    # "Spell(Myself,WIZARD_VOCALIZE)  // SPWI219.SPL (Vocalize)"
    r = re.compile(r"Spell\(.*\)\s*//(.*)\((?P<NAME>(.*))\)")
    name = get_name_from_actions(r, actions)
    if name is None:
        r = re.compile(r"SpellRES\(.*\)\s*//\s*(?P<NAME>(.*))")
        name = get_name_from_actions(r, actions)
    if name is None:
        r = re.compile(r"UseItem\(.*\)\s*//\s*(?P<NAME>(.*))")
        name = get_name_from_actions(r, actions)

    if name is not None:
        name = name.replace(' ', '-')
        name = re.sub('[^0-9a-zA-Z\-]+', '', name)

    return name


def split_if_then(source_file: str) -> dict:
    """Split a script file into component pieces"""
    logging.debug("Splitting '{}' into IF/THEN blocks".format(source_file))
    with open(source_file) as f:
        source_text = f.read()
    logging.debug("Read {} bytes".format(len(source_text)))

    r = re.compile(_if_then_regex, flags=re.MULTILINE)
    r_or = re.compile(r"OR\((\d+)\)")
    r_resp = re.compile(r"RESPONSE #(\d+)")

    # Replace all double quotes outside comments with single quotes.
    source_text = replace_double_quotes_with_single_outside_comment(
        source_text)

    count = 0
    triggers = []
    actions = []
    for m in r.finditer(source_text):
        count = count + 1

        or_count = 0
        # Break if conditions into separate lines.
        for line in m.group("IF").split('\n'):
            line = line.strip()
            or_check = r_or.match(line)

            if 0 == len(line):
                pass
            # elif 0 == or_count and "ActionListEmpty()" == line:
            #     output["ActionListEmpty"] = True
            elif or_check:
                or_count = int(or_check.group(1))
                triggers.append([])
            elif or_count > 0:
                triggers[-1].append(line)
                or_count = or_count - 1
            else:
                triggers.append(line)

        # Break then conditions into separate lines.
        action_list = []
        response_value = None
        for line in m.group("THEN").split('\n'):
            line = line.strip()
            response_check = r_resp.match(line)
            if 0 == len(line):
                pass
            elif response_check:
                if response_value:
                    actions.append({response_value: action_list})
                response_value = response_check.group(1)
                action_list = []
            else:
                action_list.append(line)
        if response_value:
            actions.append({response_value: action_list})

    if count > 1:
        raise RuntimeError("IF/THEN Parse found multiple matches in '{}'"
                           .format(source_file))

    # triggers = promote_trigger(triggers, "^HaveSpell")
    # triggers = promote_trigger(triggers, "^ActionListEmpty")
    result = {"IF": triggers, "THEN": actions}
    name = get_name(actions)
    if name:
        result["name"] = name
    return result


def get_history_names(snips_dir: str) -> dict:
    """
    Build a dictionary of names to if-then pairs from a previous run.
    This allows us to keep names from run-to-run, which helps build meaningful
    file names.
    :param snips_dir: Path to snips dir.
    :return: A list { name : if_then dict }
    """
    result = []
    sources = []
    try:
        for file_name in os.listdir(snips_dir):
            if file_name.lower().endswith('.json'):
                sources.append(file_name)
    except FileNotFoundError:
        pass

    required_keys = ("name", "IF", "THEN")
    for file_name in sources:
        path = os.path.join(snips_dir, file_name)
        with open(path) as fp:
            logging.debug("Loading history from {}".format(path))
            data = json.load(fp)
        if all(k in data for k in required_keys):
            new_entry = {}
            for key in required_keys:
                new_entry[key] = data[key]
            result.append(new_entry)
    return result


def split(source: str, auto_delete: bool):
    """
    Split a source file into a subdirectory of similar name.
    :param source: The source file, including path.
    :param auto_delete: If true, the snips directory will be removed.
    :return: None.
    """
    target = os.path.splitext(source)[0]

    logging.info("Source = '{}'".format(source))
    logging.info("Target = '{}'".format(target))

    history = get_history_names(target)
    # logging.debug("History = {}".format(pprint.pformat(history)))

    if args.auto_delete and os.path.isdir(target):
        logging.warning("Removing directory '{}'".format(target))
        shutil.rmtree(target, ignore_errors=True)
    files_to_split = split_file(source, target)

    trigger_templates = _load_templates("if")
    action_templates = _load_templates("then")

    files_to_merge = []

    for file in files_to_split:
        data = split_if_then(file)
        fields = {}
        for template in trigger_templates:
            data["IF"], fields = template.collapse(data["IF"], fields)
        for template in action_templates:
            for response in data["THEN"]:
                assert 1 == len(response)
                for key, value in response.items():
                    response[key], fields = template.collapse(
                        value, fields)
        data["fields"] = [fields]

        # If this was in the history with a name, keep the name.
        for item in history:
            if data["IF"] == item["IF"] and data["THEN"] == item["THEN"]:
                data["name"] = item["name"]
                break

        if "name" in data:
            source = file
            prefix, postfix = os.path.splitext(file)
            dest = prefix + "-" + data["name"] + postfix
            file = dest
            os.remove(source)

        with open(file, "w") as fp:
            json.dump(data, fp, indent=4)
            files_to_merge.append(file)

    prev_file = None
    prev_data = None
    for curr_file in files_to_merge:
        with open(curr_file) as fp:
            curr_data = json.load(fp)

        if prev_data and prev_data["IF"] == curr_data["IF"] and \
                prev_data["THEN"] == curr_data["THEN"]:
            logging.debug("left: {}".format(pprint.pformat(
                curr_data["fields"]
            )))
            logging.debug("right: {}".format(pprint.pformat(
                prev_data["fields"]
            )))
            curr_data["fields"] = prev_data["fields"] + curr_data["fields"]
            logging.debug("both: {}".format(pprint.pformat(
                curr_data["fields"]
            )))
            with open(curr_file, "w") as fp:
                json.dump(curr_data, fp, indent=4, sort_keys=True)
            os.remove(prev_file)

        prev_file = curr_file
        prev_data = curr_data


if __name__ == "__main__":

    search_dir = os.path.join(tools_dir, "..", project_name)
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto_delete', action='store_true', default=True)
    parser.add_argument('-v', '--verbose', action='count', default=2)
    parser.add_argument('-d', '--search_dir', default=search_dir)

    args = parser.parse_args()
    if args.verbose == 0:
        level = logging.WARNING
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(stream=sys.stdout, level=level)
    logging.info("Verbosity = {}".format(logging.getLevelName(level)))

    for file_name in os.listdir(args.search_dir):
        if file_name.lower().endswith('.baf'):
            file_path = os.path.realpath(os.path.join(args.search_dir, file_name))
            split(file_path, args.auto_delete)
