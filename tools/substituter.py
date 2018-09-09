#! /usr/bin/env python3
from copy import deepcopy
import json
import logging
import os
import pprint
import re

_this_dir = os.path.dirname(os.path.realpath(__file__))
app_name = "xseries"


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
        if key in result and result[key] != value:
            return None
        result[key] = value

    logging.debug("combine: dict1 = {}".format(pprint.pformat(dict1)))
    logging.debug("combine: dict2 = {}".format(pprint.pformat(dict2)))
    logging.debug("combine: result = {}".format(pprint.pformat(result)))
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

        escaped = '^' + re.escape(element) + '$'  # Turn things like '(' into '\('
        for field in self.field_names:
            named_group = "(?P<{}>.*)".format(field)
            field_name = re.escape("<{}>".format(field))
            escaped = escaped.replace(field_name, named_group)
        self.regex = re.compile(escaped)

    def match(self, inputs_in: list, fields_in: dict) -> ElementMatch:
        """
        Look to see if the provided data matches this element.
        :param inputs_in:  Source data to compare.
        :param fields_in:  Source fields to compare.
        :return: None or an ElementMatch object.
        """
        fields = deepcopy(fields_in)

        for i, entry in enumerate(inputs_in):
            if isinstance(entry, str):
                match = self.regex.search(entry)
                if match:

                    combined_fields = combine_dicts(fields, match.groupdict())
                    if combined_fields is None:
                        # We found a match, but we have a named parameter that
                        # holds two different values.  That fails the match.
                        logging.debug("{}: Element has conflict".format(
                            self.element))
                        logging.debug("match fields = '{}'".format(
                            pprint.pformat( match.groupdict())
                        ))
                        logging.debug("fields = '{}'".format(
                            pprint.pformat(fields)
                        ))
                        continue

                    logging.debug("'{}' == '{}'".format(
                        self.element, entry))
                    result = ElementMatch()
                    result.before = inputs_in[:i]
                    result.fields = combined_fields
                    result.after = inputs_in[i + 1:]
                    return result
                logging.debug("'{}' != '{}'".format(
                    self.element, entry))
        return None

    def format(self, fields: dict):
        """
        Return a formatted string with the field data.
        :param fields: The key/values for substitutions
        :return: The formmated string.
        """
        data = self.element
        for key, value in fields.items():
            search_term = "<{}>".format(key)
            data = data.replace(search_term, value)
        return [data]

    def line_count(self) -> int:
        """
        Get the number of lines this element contains.
        Used to sort elements by size.
        :return: The number of lienes.
        """
        return 1

    def __str__(self):
        return "ElementRegex({})".format(self.element)


class ElementOR(object):
    """
    A list of elements joined together as an OR
    """
    def __init__(self, elements):
        self.elements = []

        for element in elements:
            if isinstance(element, str):
                self.elements.append(ElementRegex(element))
            elif isinstance(element, list):
                assert False, "Nested OR detected"
            elif isinstance(element, dict):
                assert 1 == len(element), "template can only have one dict entry"
                key, value = next(iter(element.items()))
                assert {} == value, "template dict must be empty"
                self.elements.append(ElementTemplate(key))
            else:
                pprint.pprint(element)
                assert False, "unknown data type {} in OR list".format(
                    type(element)
                )
        logging.debug("ElementOR(): Added {}".format(pprint.pformat(
            self.elements)))

    def match(self, inputs_in: list, fields_in: dict) -> ElementMatch:
        """
        Look to see if the provided data matches this element.
        :param inputs_in:  Source data to compare.
        :param fields_in:  Source fields to compare.
        :return: None or an ElementMatch object.
        """
        fields = deepcopy(fields_in)

        # Narrow our possibilities to lists.
        candidates = {}
        for i, element in enumerate(inputs_in):
            if isinstance(element, list):
                candidates[i] = deepcopy(element)

        for i, candidate in candidates.items():
            if len(candidate) != len(self.elements):
                # Can't be an exact match: not the same length
                continue

            for element in self.elements:
                match = element.match(candidate, fields)
                if not match:
                    # All for one and one for all.
                    # Since one element didn't match, there is no match.
                    logging.debug("OR: Element '{}' does not match".format(element))
                    break
                combined_fields = combine_dicts(fields, match.fields)
                if combined_fields is None:
                    # We found a match, but we have a named parameter that
                    # holds two different values.  That fails the match.
                    logging.debug("OR: Element '{}' has conflict".format(element))
                    logging.debug("match fields = '{}'".format(
                        pprint.pformat(match.fields)
                    ))
                    logging.debug("fields = '{}'".format(
                        pprint.pformat(fields)
                    ))
                    break
                fields = combined_fields
                logging.debug("OR: Element '{}' MATCHES".format(element))
                candidate = match.before + match.after

            if 0 == len(candidate):
                result = ElementMatch()
                result.before = inputs_in[:i]
                result.fields = fields
                result.after = inputs_in[i+1:]
                return result
        return None

    def format(self, fields: dict):
        """
        Return a formatted string with the field data.
        :param fields: The key/values for substitutions
        :return: The formmated string.
        """
        result = []
        for element in self.elements:
            element_fmt = element.format(fields)
            result += element_fmt
        logging.debug("OR: format {}".format(pprint.pformat(result)))
        return [result]

    def line_count(self) -> int:
        """
        Get the number of lines this element contains.
        Used to sort elements by size.
        :return: The number of lienes.
        """
        result = 0
        for element in self.elements:
            result += element.line_count()
        return result

    def __str__(self):
        return "ElementOR({})".format(len(self.elements))


class ElementTemplate(object):
    """
    Another template file used as a trigger or action element.
    """
    def __init__(self, name):
        self.name = name
        self.path = get_json_path(name)
        self.elements = []

        with open(self.path) as file:
            logging.debug("Loading {}".format(self.path))
            elements = json.load(file)
            assert isinstance(elements, list)

        for element in elements:
            if isinstance(element, str):
                self.elements.append(ElementRegex(element))
            elif isinstance(element, list):
                self.elements.append(ElementOR(element))
            elif isinstance(element, dict):
                assert 1 == len(element), "template can only have one dict entry"
                key, value = next(iter(element.items()))
                assert {} == value or None == value, \
                    "template dict must be empty: {}".format(value)
                self.elements.append(ElementTemplate(key))
            else:
                pprint.pprint(element)
                assert False, "unknown data type {} in template file".format(
                    type(element)
                )

    def match(self, inputs_in: list, fields_in: dict) -> ElementMatch:
        """
        Look to see if the provided data matches this element.
        :param inputs_in:  Source data to compare.
        :param fields_in:  Source fields to compare.
        :return: None or an ElementMatch object.
        """
        input_list = deepcopy(inputs_in)
        elements = self.elements[:]
        fields = deepcopy(fields_in)
        logging.debug("1: fields={}".format(pprint.pformat(fields)))

        for i, element in enumerate(elements):
            logging.debug("{}: Examining {}".format(
                self.name, str(element)
            ))

            match = element.match(input_list, fields)
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
            logging.debug("2: fields={}".format(pprint.pformat(fields)))
            logging.debug("{}: Element '{}' MATCHES".format(
                self.name, element))
            input_list = match.before + match.after

        result = ElementMatch()
        result.before = []  # Assume templates come first.  *sigh*
        logging.debug("3: fields={}".format(pprint.pformat(fields)))
        result.fields = fields
        result.after = input_list

        # Now, compare what's left with the original list to figure out
        # a good place to split the list.
        logging.debug("FindLoc: {}".format(pprint.pformat(inputs_in)))
        for item in inputs_in:
            if 0 == len(result.after):
                logging.debug("FindLoc: End of results.after")
                break
            if item == result.after[0]:
                # Item wasn't taken, it's a "before"
                logging.debug("FindLoc: Moving {} to results.before".format(
                    pprint.pformat(result.after[0])
                ))
                result.before.append(result.after[0])
                result.after = result.after[1:]
            else:
                logging.debug("FindLoc: End found at '{}'".format(
                    pprint.pformat(result.after[0])
                ))
                break

        logging.debug("4: fields={}".format(pprint.pformat(result.fields)))
        return result

    def format(self, fields: dict):
        """
        Return a formatted string with the field data.
        :param fields: The key/values for substitutions
        :return: The formatted string.
        """
        result = []
        logging.debug("{}: START format".format(self.name))
        for element in self.elements:
            element_fmt = element.format(fields)
            logging.debug("{}: format {}".format(
                self.name, pprint.pformat(element_fmt)))
            result += element_fmt
        logging.debug("{}: END format {}".format(
            self.name, pprint.pformat(result)))
        return result

    def line_count(self) -> int:
        """
        Get the number of lines this element contains.
        Used to sort elements by size.
        :return: The number of lines.
        """
        result = 0
        for element in self.elements:
            result += element.line_count()
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

    def collapse(self, list_in: list, fields_in: dict) -> (list, dict):
        """
        Scan a list, and substitute ourselves in the
        list if a match is made.
        :return: The (possibly modified) list.
        """
        match = self.template.match(deepcopy(list_in), fields_in)
        if match is not None:
            replacement = {self.template.name: None}
            return match.before + [replacement] + match.after, match.fields
        return list_in, fields_in

    def expand(self, field_data) -> list:
        """
        TODO
        """
        logging.debug("{}: expand {}".format(
            self.template.name, pprint.pformat(field_data)
        ))
        result = self.template.format(field_data)
        logging.debug("{}: expanded {}".format(
            self.template.name, pprint.pformat(result)
        ))

        return result

    def line_count(self) -> int:
        """
        :return: The number of lines in contained items.
        """
        return self.template.line_count()

    def __str__(self):
        return str(self.fields)
