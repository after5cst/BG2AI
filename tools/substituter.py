#! /usr/bin/env python3
from copy import deepcopy
import json
import os
import pprint
import re

_this_dir = os.path.dirname(os.path.realpath(__file__))
app_name = "bg2"


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
        path = os.path.join(_this_dir, "..", app_name, "if", name + ".json")
        if not os.path.exists(path):
            path = os.path.join(_this_dir, "..", app_name, "then", name + ".json")
        self.path = os.path.realpath(path)
        with open(self.path) as fp:
            self.triggers = json.load(fp)

        # Go find any field names in our template data.
        # Also compile regex for searches in the template data.
        self.fields = list()
        self.regex = list()
        regex = re.compile(r"<(\w+)>")
        for trigger in self.triggers:
            fields = regex.findall(trigger)
            self.fields += fields

            escaped = re.escape(trigger) # Turn things like '(' into '\('
            for field in fields:
                named_group = "(?P<{}>.*)".format(field)
                field_name = re.escape("<{}>".format(field))
                escaped = escaped.replace(field_name, named_group)
            self.regex.append(re.compile(escaped))

    @staticmethod
    def find_str_in_regex_list(item: str, regexes: list, fields: dict)\
            -> FoundInRegexList:
        """
        Test item against regular expressions for a match.
        :param item: The string to be checked against the regular expressions.
        :param regexes: The list of regular expressions.
        :return: None if not found, otherwise a FoundInRegexList object.
        """
        regex_inputs = deepcopy(regexes)
        for i, regex in enumerate(regex_inputs):
            # Since I'm new to 'enumerate':
            #   i is the current index in regex_inputs
            #   regex is the actual item from regex_inputs
            match = regex.search(item)
            if match:
                out = FoundInRegexList()
                out.index = i
                out.fields = match.groupdict()

                field_collision = False
                for key in out.fields:
                    if key in fields:
                        if out.fields[key] != fields[key]:
                            field_collision = True
                            break
                if not field_collision:
                    out.fields.update(fields)
                    return out
        return None

    def collapse(self, list_in: list) -> list:
        """
        Scan a list, and substitute ourselves in the
        list if a match is made.
        :return: a list, and a dict of fields.
        """
        input_list = deepcopy(list_in)
        regexes = deepcopy(self.regex)
        first_match = None
        unmatched = []
        fields = {}

        for input_item in input_list:
            if isinstance(input_item, str):
                match = self.find_str_in_regex_list(
                    input_item, regexes, fields)
            else:
                match = None
            if match is None:
                unmatched.append(input_item)
            else:
                if first_match is None:
                    first_match = len(unmatched)
                fields = match.fields
                del regexes[match.index]

        if 0 == len(regexes):
            # Found all items in th regex list, this
            # is a match.  Make the substitution at the
            # earliest point.
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
