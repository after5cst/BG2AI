#! /usr/bin/env python3
import json
import os
import pprint
import re

_this_dir = os.path.dirname(os.path.realpath(__file__))
app_name = "bg2"


class TriggerTemplate(object):
    """
    A Template container for triggers.
    """
    def __init__(self, name):
        """
        Create a TriggerTemplate.  This loads the template
        from disk so it can be used.
        :param name: The file name of the template.
        """
        self.name = name
        path = os.path.join(_this_dir, "..", app_name, "if", name + ".json")
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

    def collapse(self, triggers: list) -> list:
        """
        Scan a list of triggers, and substitute ourselves in the
        list of triggers if a match is made.
        :return: a list of triggers, and a dict of fields.
        """
        pprint.pprint(triggers)
        fields = {}
        for i in range(1 + len(triggers) - len(self.regex)):
            found = True  # optimism!
            for j in range(len(self.regex)):
                if not found:
                    # The match has failed.  Move along.
                    break

                k = i + j
                if isinstance(triggers[k], dict):
                    # An OR statement.  We don't currently do this.
                    found = False
                    break

                print('*' * 10)
                pprint.pprint(triggers[k])
                pprint.pprint(self.triggers[j])
                match = self.regex[j].search(triggers[k])
                if not match:
                    # Nope, no good.  Start over with the next 'i'
                    found = False
                    break

                found_fields = match.groupdict()
                for key in found_fields:
                    if key in fields:
                        if found_fields[key] != fields[key]:
                            # Uh, keys must be consistent.
                            found = False
                            break
                    else:
                        fields[key] = found_fields[key]

            if found:
                before = triggers[:i]
                mid = [{ self.name : fields }, ]
                after = triggers[i+len(self.regex):]
                return before + mid + after

        # No match, just return the original input.
        return triggers

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
    test = TriggerTemplate("CanUseWand")

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
