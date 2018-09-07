#! /usr/bin/env python3
from copy import deepcopy
import json
import logging
import os
import pprint
import re

_this_dir = os.path.dirname(os.path.realpath(__file__))
app_name = "bg2"


def combine_dicts(dict1, dict2):
    """Combine two dicts if there are no duplicate keys.
    :param dict1: First dict to be combined
    :param dict2: Second dict to be combined
    "return" None if duplicate key, otherwise a combined dictionary.
    """
    result = {}
    for key, value in dict1.items():
        result[key] = value
    for key, value in dict2.items():
        if key in result:
            return None
        result[key] = value
    return result


def get_json_path(name: str) -> str:
    """
    Return the path to the JSON file for the provided name.  This
    is hackery because I didn't design things correctly.
    :param name: Name of the template file.
    :return: The path to the template file.
    """
    path = os.path.join(_this_dir, "..", app_name, "if", name + ".json")
    if not os.path.exists(path):
        path = os.path.join(_this_dir, "..", app_name, "then", name + ".json")
    return os.path.realpath(path)


class ElementMatch(object):
    """
    A container for element matches.
    attributes:
    * before : A list of unmatched elements prior to the match
    * fields : A dict of field names and values from the match
    * after  : A list of unmatched elements after the match
    """
    before = None
    fields = {}
    after = None


class ElementRegex(object):
    """
    A regular expression used as a trigger or action element.
    """
    key_regex = re.compile(r"<(\w+)>")

    def __init__(self, element: str):
        assert isinstance(element, str), "Regex element must be a string"
        self.element = element
        self.field_names = ElementRegex.key_regex.findall(element)

        escaped = re.escape(element)  # Turn things like '(' into '\('
        for field in self.field_names:
            named_group = "(?P<{}>.*)".format(field)
            field_name = re.escape("<{}>".format(field))
            escaped = escaped.replace(field_name, named_group)
        self.regex = re.compile(escaped)

    def match(self, element_list: list):
        """
        Look to see if the provided data contains this element.
        :param element_list:  Source data to compare.
        :return: None or an ElementMatch object.
        """
        for i, entry in enumerate(element_list):
            if isinstance(entry, str):
                match = self.regex.search(entry)
                if match:
                    result = ElementMatch()
                    result.before = element_list[:i]
                    result.fields = match.groupdict()
                    result.after = element_list[i + 1:]
                    return result
        return None

    def __str__(self):
        return "ElementRegex({})".format(self.element)


class ElementTemplate(object):
    """
    Another template file used as a trigger or action element.
    """
    def __init__(self, name):
        self.name = name
        self.path = get_json_path(name)
        self.elements = []

        with open(self.path) as file:
            elements = json.load(file)
            assert isinstance(elements, list)

        for element in elements:
            if isinstance(element, str):
                self.elements.append(ElementRegex(element))
            elif isinstance(element, list):
                # TODO : This is an OR list.
                assert False, "TODO : OR"
            elif isinstance(element, dict):
                assert 1 == len(element), "template can only have one dict entry"
                key, value = next(iter(element.items()))
                assert {} == value, "template dict must be empty"
                self.elements.append(ElementTemplate(key))
            else:
                pprint.pprint(element)
                assert False, "unknown data type {} in template file".format(
                    type(element)
                )

    def match(self, element_list):
        """
        Look to see if the provided data matches this element.
        :param element_list:  Source data to compare.
        :return: None or an ElementMatch object.
        """
        input_list = deepcopy(element_list)
        elements = self.elements[:]
        fields = {}

        for i, element in enumerate(elements):
            logging.debug("{}: Examining {}".format(
                self.name, str(element)
            ))

            match = element.match(input_list)
            if not match:
                # All for one and one for all.
                # Since one element didn't match, there is no match.
                logging.debug("Element '{}' does not match".format(element))
                return None
            combined_fields = combine_dicts(fields, match.fields)
            if combined_fields is None:
                # We found a match, but we have a named parameter that
                # holds two different values.  That fails the match.
                logging.debug("Element '{}' has field conflict".format(element))
                logging.debug("match fields = '{}'".format(
                    pprint.pformat(match.fields)
                ))
                logging.debug("fields = '{}'".format(
                    pprint.pformat(fields)
                ))
                return None
            fields = combined_fields
            logging.debug("Element '{}' MATCHES".format(element))
            input_list = match.before + match.after

        result = ElementMatch()
        result.before = []  # Assume templates come first.  *sigh*
        result.fields = fields
        result.after = input_list

        # Now, compare what's left with the original list to figure out
        # a good place to split the list.
        for item in element_list:
            if 0 == len(result.after):
                break
            if item == result.after[0]:
                # Item wasn't taken, it's a "before"
                result.before.append(result.after[0])
                result.after = result.after[1:]
        return result

    def __str__(self):
        return "ElementTemplate({})".format(self.name)


class Substituter(object):
    """
    A Template container.
    """
    def __init__(self, name):
        """
        Create a Substituter.  This loads the template
        from disk so it can be used.
        :param name: The file name of the template.
        """
        self.template = ElementTemplate(name)

    def collapse(self, list_in: list) -> list:
        """
        Scan a list, and substitute ourselves in the
        list if a match is made.
        :return: The (possibly modified) list.
        """
        match = self.template.match(deepcopy(list_in))
        if match is not None:
            replacement = {self.template.name: match.fields}
            return match.before + [replacement] + match.after
        return list_in

    def expand(self, field_data) -> list:
        """
        TODO
        """
        out = list()

        for my_trigger in self.triggers:
            assert isinstance(my_trigger, str), "No ORs or recursion (yet)"
            for key, value in field_data.items():
                search_term = "<{}>".format(key)
                my_trigger = my_trigger.replace(search_term, value)

            out.append(my_trigger)
        return out

    def expand_all(self, triggers: list) -> list:
        """
        Expand the template in the input if found.
        :param triggers: The list of triggers.
        :return: The modified list.
        """
        out = list()
        for trigger in triggers:
            if not isinstance(trigger, dict):
                # Trivial: this isn't a possible template.
                out.append(trigger)
                continue

            if self.name not in trigger:
                # Trivial: This dict isn't our trigger
                out.append(trigger)
                continue

            out += self.expand(trigger[self.name])
        return out

    def __str__(self):
        return str(self.fields)


if __name__ == "__main__":
    test = Substituter("CanUseWand")

    source = os.path.join(_this_dir, "..", "BDDEFAI",
                          "2680-Wand-of-Monster-Summoning.json")
    with open(source) as fp:
        data = json.load(fp)
    temp = data["if"]

    print('*' * 80)
    pprint.pprint(temp)
    temp2 = test.expand_all(temp)

    print('*' * 80)
    pprint.pprint(temp2)
    temp3 = test.collapse(temp2)

    print('*' * 80)
    pprint.pprint(temp3)
    assert temp3 == temp, "collapse + expand failed"
