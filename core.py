#!/usr/bin/env python

from __future__ import print_function
import os
import re
import copy
import json
import codecs

import sys


def guess_is_colon_separated(env_name):
    # type: (str) -> bool

    if not hasattr(guess_is_colon_separated, "pattern"):
        guess_is_colon_separated.pattern = re.compile("""
            ^(?:.+)(            # ==== Match the specific prefixes ====
                PATH |          # MANPATH, INFOPATH, LD_LIBRARY_PATH, LIBRARY_PATH, PKG_CONFIG_PATH 
                _DIR |
                _DIRS |         # XDG_CONFIG_DIRS, XDG_DATA_DIRS
                _DIRECTORY |
                _COLORS |       # GCC_COLORS, LS_COLORS
                _MODULES        # GTK_MODULES
            )$ 
            | ^(                # ==== Match full names ====
                PATH |
                INTEL_LICENSE_FILE
            )$""", re.IGNORECASE | re.VERBOSE)

    match = guess_is_colon_separated.pattern.match(env_name)
    return bool(match)


def list_substract(left, right):
    # type: (list[T], list[T]) -> list[T]
    right_set = set(right)
    return list(filter(lambda item: item not in right_set, left))


def list_try_remove(lst, item):
    # type: (list[T], T) -> None
    try:
        lst.remove(item)
    except ValueError:
        pass


class EnvironDifference:

    def __init__(self, old, new):
        # type: (Environ, Environ) -> EnvironDiff

        if (old is None) and (new is None):
            return
        assert old is not None
        assert new is not None

        self.Added = {}
        self.Removed = {}
        self.Modified = {}

        for env_name in old:
            if env_name not in new:
                self.Removed[env_name] = copy.deepcopy(old[env_name])
            else:
                if old[env_name] == new[env_name]:
                    continue
                assert len(old[env_name]) >= 1
                assert len(new[env_name]) >= 1
                self.Modified[env_name] = {
                    "Remove": list_substract(old[env_name], new[env_name]),
                    "Add": list_substract(new[env_name], old[env_name])
                }

        for env_name in new:
            if env_name not in old:
                self.Added[env_name] = copy.deepcopy(new[env_name])

    def dump(self, file_path):
        # type: (str) -> None
        with codecs.open(file_path, "w", "utf-8") as fp:
            json.dump(self.__dict__, fp, encoding="utf-8", sort_keys=True, indent=2)

    @staticmethod
    def load(file_path):
        # type: (str) -> EnvironDifference
        with codecs.open(file_path, "r", "utf-8") as fp:
            ret = EnvironDifference(None, None)
            ret.__dict__ = json.load(fp, encoding="utf-8")
            return ret

    def __str__(self):
        return json.dumps(self.__dict__, encoding="utf-8", sort_keys=True, indent=2)


class Environ:

    def __init__(self, env_dict=os.environ):
        # type: (dict[str, str]) -> Environ

        self.Envs = {}  # type: dict[str, list[str]]

        if env_dict is None:
            return

        for env_name in env_dict:
            assert isinstance(env_dict[env_name], str)
            if guess_is_colon_separated(env_name):
                self[env_name] = list(env_dict[env_name].split(":"))
            else:
                self[env_name] = [env_dict[env_name]]
                # print(self.Envs)

    def __contains__(self, item):
        return item in self.Envs

    def __getitem__(self, item):
        return self.Envs[item]

    def __setitem__(self, key, value):
        self.Envs[key] = value

    def __iter__(self):
        for item in self.Envs:
            yield item

    def dump(self, file_path):
        # type: (str) -> None
        with codecs.open(file_path, "w", "utf-8") as fp:
            json.dump(self.__dict__, fp, encoding="utf-8", sort_keys=True, indent=2)

    @staticmethod
    def load(file_path):
        # type: (str) -> Environ
        with codecs.open(file_path, "r", "utf-8") as fp:
            ret = Environ(None)
            ret.__dict__ = json.load(fp, encoding="utf-8")
            return ret

    def __str__(self):
        return json.dumps(self.__dict__, encoding="utf-8", sort_keys=True, indent=2)

    def revert_difference(self, diff, ignore_unchanged=True):
        # type: (EnvironDifference, bool) -> Environ
        if ignore_unchanged:
            tmp = {}
            tmp.update(diff.Added)
            tmp.update(diff.Modified)
            tmp.update(diff.Removed)
            result = Environ(None)
            for env_name in tmp:
                if env_name in self:
                    result[env_name] = copy.deepcopy(self[env_name])
        else:
            result = copy.deepcopy(self)

        # Remove the added values:
        for env_name in diff.Added:
            if env_name in result:
                for env_value in diff.Added[env_name]:
                    list_try_remove(result[env_name], env_value)

        # Add the removed values
        for env_name in diff.Removed:
            if env_name not in result:
                result[env_name] = copy.deepcopy(diff.Removed[env_name])
            else:
                if guess_is_colon_separated(env_name):
                    # TODO: How to deal with this situation?
                    result[env_name] = diff.Removed[env_name] + result[env_name]
                else:
                    # TODO: How to deal with this situation?
                    pass

        # Revert the modified changes
        for env_name in diff.Modified:
            if env_name in result:
                for env_value in diff.Modified[env_name]["Add"]:
                    list_try_remove(result[env_name], env_value)
            else:
                result[env_name] = []

            assert env_name in result
            if guess_is_colon_separated(env_name) or len(result[env_name]) == 0:
                result[env_name] = diff.Modified[env_name]["Remove"] + result[env_name]
            else:
                # TODO: How to deal with this situation?
                pass

        return result

    def to_bashrc(self):
        # type: () -> str
        result = ""
        for env_name in self:
            if env_name.startswith("."):
                continue
            if len(self[env_name]) == 0:
                result += "unset %s\n" % env_name
            else:
                if not guess_is_colon_separated(env_name):
                    assert len(self[env_name]) == 1

                result_strs = []
                for env_value in self[env_name]:
                    result_strs.append(env_value
                                       .replace("\\", "\\\\")
                                       .replace("\"", "\\\"")
                                       .replace("$", "\\$")
                                       .replace("\n", "\\n"))
                result += "export %s=\"%s\"\n" % (env_name, ":".join(result_strs))

        return result


def main(args):
    # type: (list[str]) -> None
    if args[0] == "dump":
        Environ().dump(args[1])
    elif args[0] == "diff":
        old_env = Environ.load(args[1])
        new_env = Environ.load(args[2])
        EnvironDifference(old_env, new_env).dump(args[3])
    elif args[0] == "revert":
        env = Environ.load(args[1])
        diff = EnvironDifference.load(args[2])
        reverted = env.revert_difference(diff)
        with codecs.open(args[3], "w", "utf-8") as fp:
            fp.write(reverted.to_bashrc())


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))
    main(sys.argv[1:])
