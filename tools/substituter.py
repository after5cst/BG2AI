#! /usr/bin/env python3
from copy import deepcopy
import json
import os
import pprint
import re

_this_dir = os.path.dirname(os.path.realpath(__file__))
app_name = "bg2"


def combine_dicts(dict1, dict2):
    """Combine two dicts if there are no duplicate keys.
    :param dict1: First dict to be combined
    :param dict2: Second dict to be conbined
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

    def match(self, data):
        """
        Look to see if the provided data matches this element.
        :param data:  Source data to compare.
        :return: None or a dict of matched fields.
        """
        result = None
        if isinstance(data, str):
            match = self.regex.search(data)
            if match:
                result = match.groupdict()
        return result



class FoundInRegexList(object):
    """
    An object returned from find_*_in_regex_list in the Subustituter class
    """
    index = -1
    fields = {}


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
        self.name = name
        self.elements = []
        self.fields = []
        self.path = None

        path = os.path.join(_this_dir, "..", app_name, "if", name + ".json")
        if not os.path.exists(path):
            path = os.path.join(_this_dir, "..", app_name, "then", name + ".json")
        self.path = os.path.realpath(path)

        elements = []
        with open(self.path) as file:
            elements = json.load(file)
            assert isinstance(elements, list)

        for element in elements:
            if isinstance(element, str):
                self.elements.append(ElementRegex(element))
            else:
                pprint.pprint(element)
                assert False, "unknown data type {} in template file".format(
                    type(element)
                )

    def collapse(self, list_in: list) -> list:
        """
        Scan a list, and substitute ourselves in the
        list if a match is made.
        :return: a list, and a dict of fields.
        """
        input_list = deepcopy(list_in)
        elements = self.elements[:]
        first_match = None
        unmatched = []
        fields = {}

        for input_item in input_list:
            for i, element in enumerate(elements):
                temp_fields = element.match(input_item)
                if temp_fields:
                    # We matched the record.  Check for field collisions.
                    temp_fields = combine_dicts(temp_fields, fields)
                if temp_fields:
                    fields = temp_fields
                    del elements[i]
                    if first_match is None:
                        first_match = len(unmatched)

        if 0 == len(elements):
            # Found all items, this is a match.  Make the substitution
            # at the earliest point.
            replacement = {self.name: fields}
            unmatched.insert(first_match, replacement)
            return unmatched

        # We didn't match every regex line somewhere.  This fails
        # the match as a whole and we will just return the original
        # list of items.
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
