#!/usr/bin/env python
# Copyright (C) 2014-2015 Shea G Craig <shea.craig@da.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""jss_helper

Perform queries of objects on a JAMF Software Server.

Requires: python-jss.
usage: jss_helper [-h] [-v] [--ssl]  ...

Query the JSS.

optional arguments:
  -h, --help      show this help message and exit
  -v              Verbose output.
  --ssl           Use SSL verification

Actions:

    category      List all categories, or search for an individual
                  category.
    computer      List all computers, or search for an individual
                  computer.
    configp       List all configuration profiles, or search for an
                  individual configuration profile.
    excluded      List all policies and configuration profiles from
                  which a computer group is excluded.
    group         List all computer groups, or search for an individual
                  group.
    imaging_config
                  List all Casper Imaging computer configurations, or
                  search for an individual computer configuration.
    installs      Lists all policies and imaging configurations which
                  install a package.
    md            List all mobile devices, or search for an indvidual
                  mobile device.
    md_configp    List all mobile device configuration profiles, or
                  search for an individual mobile device configuration
                  profile.
    md_excluded   List all configuration profiles from which a mobile
                  device group is excluded.
    md_group      List all mobile device groups, or search for an
                  individual mobile device group.
    md_scope_diff
                  Show the differences between two mobile device groups'
                  scoped mobile device configuration profiles.
    md_scoped     List all mobile device configuration profiles scoped
                  to a mobile device group.
    package       List of all packages, or search for an individual
                  package.
    policy        List all policies, or search for an individual policy.
    scope_diff    Show the difference between two groups' scoped
                  policies and configuration profiles.
    scoped        List all policies and configuration profiles scoped to
                  a computer group.
    batch_scope   Scope a list of policies to a group.
    promote       Promote a package from development to production by
                  updating an existing production policy with a newer
                  package.
"""


import argparse
from distutils.version import StrictVersion, LooseVersion
import fnmatch
from operator import itemgetter
import re
import subprocess
import sys

import jss


__version__ = "2.0.1"
__all__ = ["version_check", "build_results_string",
           "find_objects_in_containers", "_input_menu_text", "prompt_user",
           "in_range", "sort_package_list", "display_options_list",
           "build_argument_parser", "create_search_func", "search_for_object",
           "get_package_info", "update_name", "get_newest_pkg", "log_warning",
           "open_policy_log_in_browser", "_build_package_version_dict",
           "_get_updatable_policies", "_add_flags_to_list",
           "get_scoped_to_all", "wildcard_search", "find_groups_in_scope",
           "get_scoped", "get_md_scoped", "get_group_scope_diff",
           "get_md_scope_diff", "batch_scope", "group_search_or_modify",
           "get_excluded", "get_md_excluded", "_get_exclusions_by_type",
           "get_package_policies", "promote", "main"]

REQUIRED_PYTHON_JSS_VERSION = StrictVersion("0.3.4")
WILDCARDS = "*?[]"


# Class Definitions ###########################################################
class JSSConnection(object):
    """Class for providing a single JSS connection."""
    _jss_prefs = None
    _jss = None

    @classmethod
    def setup(cls):
        """Set up the jss connection class variable."""
        cls._jss_prefs = jss.JSSPrefs()
        cls._jss = jss.JSS(jss_prefs=cls._jss_prefs)

    @classmethod
    def get(cls):
        """Return the shared JSS object."""
        if not cls._jss:
            cls.setup()
        return cls._jss


# Utility Functions ###########################################################
def version_check():
    """Ensure we have the right version of python-jss."""
    try:
        python_jss_version = StrictVersion(jss.__version__)
    except AttributeError:
        python_jss_version = StrictVersion("0.0.0")

    if python_jss_version < REQUIRED_PYTHON_JSS_VERSION:
        print "Requires python-jss version: %s. Installed: %s" % (
            (REQUIRED_PYTHON_JSS_VERSION, python_jss_version))
        sys.exit(1)


def build_results_string(heading, results):
    """Format results for output reporting.

    Args:
        heading: String heading for results, or None for no heading.
        results: An iterable of JSSObjects, a JSSObjectList, or a
            single JSSObject..

    Returns:
        Formatted report string.
    """
    output_string = ""
    if heading:
        output_string = heading
        if not output_string.endswith("\n"):
            output_string += "\n"
    # Print column aligned lists of ID and Name.
    if results:
        if (all([isinstance(result, jss.JSSObject) for result in results]) or
                (isinstance(results, jss.JSSObjectList) and len(results) > 0)):
            width = max([int(len(str(result.id))) for result in results])
            output_strings = []
            for i in results:
                output_strings.append(u"ID: {:>{width}}\tNAME: {}".format(
                    i.id, i.name, width=width))
            output_string += "\n".join(output_strings)
        # Just print the object.
        elif isinstance(results, jss.JSSObject):
            output_string += str(results)
    else:
        output_string += "No results found."
    return output_string + "\n"


def find_objects_in_containers(search_objects, search_path, containers):
    """Get all container objects which contain references to objects.

    JSS Objects often reference other objects: e.g. Policies have
    scoping groups and packages. This function will search within a
    container-type JSS Object for a reference to another object.

    Args:
        search_objects: A JSSObject, list/tuple of JSSObjects or a
            jss.JSSObjectList to search for in 'containers'.
        search_path: A str xpath pointing to the subelement of
            'containers' to search within.
        containers: List of JSSObjects in which to locate
            'search_objects'.

    Returns: A list of JSSObjects which match.
    """
    results = []
    if isinstance(containers, jss.JSSObjectList):
        full_objects = containers.retrieve_all()
    else:
        full_objects = containers

    if isinstance(search_objects, jss.JSSObject):
        search_objects = [search_objects]
    search_ids = [obj.id for obj in search_objects]
    search_names = [obj.name for obj in search_objects]
    for obj in full_objects:
        for element in obj.findall(search_path):
            if (element.findtext("id") in search_ids or
                    element.findtext("name") in search_names):
                results.append(obj)
    return results


def _input_menu_text(expandable, flags):
    """Based on available options, build a series of prompts."""
    # Build the input menu text:
    input_menu_strings = ["\nEnter a number to select from list."]
    if expandable:
        input_menu_strings.append("Enter 'F' to expand the options list.")
    if flags and "DEFAULT" in flags:
        input_menu_strings.append("Hit <Enter> to accept default choice.")
    input_menu_strings.append("Please choose an object: ")
    return "\n".join(input_menu_strings)


def prompt_user(options, expandable=False, flags=None):
    """Ask user a question based on configured values.

    Args:
        options: Iterable of options to choose from.
        expandable: Optional iterable of options to choose from, larger
            than "options". If provided, will add an "F" option to the
            interactive menu which allows user to expand the possible
            selections.

            Defaults to an empty list, and will disable
            the "F" menu option.
        flags: Dynamically mark some options with extra
            text. For example, make an option "Default".

            Key: String name of text to append to option in list.
            Value: Function for matching an option. The function
                must return a bool.

            e.g.: {"CURRENT": lambda f: current_package in f}
                where "current_package" is a variable with the desired
                value.

            flags accepts a special key name: "DEFAULT", which will
            flag an option as a default, which is selectable by the
            user by simply pressing enter.

    Returns:
        The item chosen from the options iterable. Note, this does not
        include the flag text if present.
    """
    # In case the abbreviated option list is actually empty, go ahead
    # and use the expanded list.
    if not options:
        options = expandable
        expandable = False
    flagged_options = _add_flags_to_list(flags, options)
    display_options_list(flagged_options)

    # Ask user to select an option until they make a valid choice.
    result = None
    while not result:
        choice = raw_input(_input_menu_text(expandable, flags))
        if choice.isdigit() and in_range(int(choice), len(options)):
            result = options[int(choice)]
        elif choice.upper() == "F" and expandable:
            # User wants the full list.
            flagged_full_options = _add_flags_to_list(flags, expandable)
            display_options_list(flagged_full_options)
            options = expandable
            # Turn off expandable so the next loop won't continue to
            # allow the "F" option.
            expandable = False
        elif choice == "" and flags and "DEFAULT" in flags:
            results = [option for option in options if
                       flags["DEFAULT"](option)]
            # If there is a result, use it! Otherwise, just repeat the
            # menu.
            if results:
                result = results.pop()
        else:
            print "Invalid choice!"

    return result


def in_range(val, size):
    """Determine whether a value x is within the range 0 > x <= size."""
    return val < size and val >= 0


def sort_package_list(packages):
    """Sort a list of packages by version number.

    Args:
        packages: A list of string names that are formatted for
            get_package_info() usage.

    Returns:
        A list of string package names in order of
        distutils.version.LooseVersion
    """
    package_info = []
    for package in packages:
        pkg_name, pkg_string_version = get_package_info(package)
        # If the regex fails on either basename or version, skip.
        if pkg_name and pkg_string_version:
            # Upper the name for sorting, and convert version to a
            # LooseVersion.
            package_info.append((package, pkg_name.upper(),
                                 LooseVersion(pkg_string_version)))

    # Sort by name, then version.
    package_info.sort(key=itemgetter(1, 2))
    # Return just the original name.
    return [package[0] for package in package_info]


def display_options_list(options):
    """Prints options in columns as a numbered list.

    Optionally, flag some options with extra text.

    Args:
        options: Iterable of strings to enumerate, and print in
            columns.
    """
    # Justify the columns so the option numbers don't push the options
    # out of a nice left-justified column.
    # TODO: Very similar to build_results_string.

    # Figure out the number of options, then the length of that number.
    length = len(str(len(options))) + len("\t")
    fmt_string = u"{0[0]:>{length}}: {0[1]}"
    choices = "\n".join([fmt_string.format(option, length=length) for option in
                         enumerate(options)])
    print "\n" + choices


def build_argument_parser():
    """Build the argument parser for jss_helper.

    Returns: A configured argparse parser.
    """
    # Create our argument parser
    parser = argparse.ArgumentParser(description="Query the JSS.")
    parser.add_argument("-v", action="store_true", help="Verbose output.")
    parser.add_argument("--ssl", default=False, action="store_true",
                        help="Use SSL verification")
    subparser = parser.add_subparsers(dest="subparser_name", title="Actions",
                                      metavar="")

    subparsers = {}

    jss_connection = JSSConnection.get()

    # computer
    subparsers["computer"] = {
        "help": "List all computers, or search for an individual computer.",
        "func": create_search_func(jss_connection.Computer),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "computer.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["configp"] = {
        "help": "List all configuration profiles, or search for an individual "
                "configuration profile.",
        "func": create_search_func(jss_connection.OSXConfigurationProfile),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "profile.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["excluded"] = {
        "help": "List all policies and configuration profiles from which a "
                "computer group is excluded.",
        "func": get_excluded,
        "args": {"group": {"help": "ID or name of group."}}}
    subparsers["group"] = {
        "help": "List all computer groups, or search for an individual group.",
        "func": group_search_or_modify,
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "computer group.",
                            "default": None,
                            "nargs": "?"},
                 "--add": {"help": "Computer ID's or names to add to group. "
                                   "Wildcards may be used.",
                           "nargs": "*"},
                 "--remove": {"help": "Computer ID's or names to remove from "
                                      "group. Wildcards may be used.",
                              "nargs": "*"},
                 "--dry_run": {"help": "Construct the updated XML for the "
                                       "group, but don't save. Prints "
                                       "results.",
                               "action": "store_true"}}}
    subparsers["imaging_config"] = {
        "help": "List all Casper Imaging computer configurations, or search "
                "for an individual computer configuration.",
        "func": create_search_func(jss_connection.ComputerConfiguration),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "computer configuration.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["package"] = {
        "help": "List of all packages, or search for an individual package.",
        "func": create_search_func(jss_connection.Package),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "package.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["policy"] = {
        "help": "List all policies, or search for an individual policy.",
        "func": create_search_func(jss_connection.Policy),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "policy.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["scoped"] = {
        "help": "List all policies and configuration profiles scoped to a "
                "computer group.",
        "func": get_scoped,
        "args": {"group": {"help": "ID or name of a computer group."}}}
    subparsers["installs"] = {
        "help": "Lists all policies and imaging configurations which install "
                "a package.",
        "func": get_package_policies,
        "args": {"package": {"help": "ID, name, or wildcard name of "
                                     "package(s)."}}}
    subparsers["scope_diff"] = {
        "help": "Show the difference between two groups' scoped policies and "
                "configuration profiles.",
        "func": get_group_scope_diff,
        "args": {"group1": {"help": "ID or name of first group."},
                 "group2": {"help": "ID or name of second group."}}}
    subparsers["category"] = {
        "help": "List all categories, or search for an individual category.",
        "func": create_search_func(jss_connection.Category),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "category.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md"] = {
        "help": "List all mobile devices, or search for an indvidual mobile "
                "device.",
        "func": create_search_func(jss_connection.MobileDevice),
        "args": {"search": {"help": "ID or name (wildcards allowed) of mobile "
                                    "device.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md_group"] = {
        "help": "List all mobile device groups, or search for an individual "
                "mobile device group.",
        "func": create_search_func(jss_connection.MobileDeviceGroup),
        "args": {"search": {"help": "ID or name (wildcards allowed) of mobile "
                                    "device group.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md_configp"] = {
        "help": "List all mobile device configuration profiles, or search for "
                "an individual mobile device configuration profile.",
        "func": create_search_func(
            jss_connection.MobileDeviceConfigurationProfile),
        "args": {"search": {"help": "ID or name (wildcards allowed) of mobile "
                                    "device configuration profile.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md_scoped"] = {
        "help": "List all mobile device configuration profiles scoped to a "
                "mobile device group.",
        "func": get_md_scoped,
        "args": {"group": {"help": "ID or name of a mobile device group."}}}
    subparsers["md_scope_diff"] = {
        "help": "Show the differences between two mobile device groups' "
                "scoped mobile device configuration profiles.",
        "func": get_md_scope_diff,
        "args": {"group1": {"help": "ID or name of first group."},
                 "group2": {"help": "ID or name of second group."}}}
    subparsers["md_excluded"] = {
        "help": "List all configuration profiles from which a mobile device "
                "group is excluded.",
        "func": get_md_excluded,
        "args": {"group": {"help": "ID or name of group."}}}

    sorted_subparsers = sorted(subparsers)
    for command in sorted_subparsers:
        sub = subparser.add_parser(command, help=subparsers[command]["help"],
                                   description=subparsers[command]["help"])
        for arg in subparsers[command]["args"]:
            sub.add_argument(arg, **subparsers[command]["args"][arg])
        sub.set_defaults(func=subparsers[command]["func"])

    # More complicated parsers.

    # Batch Scope
    arg_help = "Scope a list of policies to a group."
    batch_scope_subparser = subparser.add_parser(
        "batch_scope", help=arg_help, description=arg_help)
    batch_scope_subparser.add_argument(
        "group", help="Name, ID, or wildcard search of group to scope "
                      "policies.")
    arg_help = ("A space delimited list of policy IDs or names. Wildcards "
                "allowed.")
    batch_scope_subparser.add_argument("policy", help=arg_help, nargs="*")
    batch_scope_subparser.set_defaults(func=batch_scope)

    # Promote
    arg_help = ("Promote a package from development to production by updating "
                "an existing production policy with a newer package.")
    promote_subparser = subparser.add_parser(
        "promote", help=arg_help, description=arg_help)
    promote_subparser.add_argument("policy", help="Policy name or ID.",
                                   nargs="?", default=None)
    promote_subparser.add_argument("new_package", help="Package name or ID.",
                                   nargs="?", default=None)
    arg_help = ("Update the package version number in the policy's name. "
                "The Policy name must include the exact product name and the "
                "version. The package extension is optional, and will not be "
                "modified. Text replacement also ignores '-', '_', and ' ' "
                "(space) between the name and version. e.g.: 'jss_helper "
                "promote \"Install Nethack-3.4.3\" Nethack-3.4.4' will result "
                "in the policy name: 'Install Nethack-3.4.4'. See the README "
                "for further examples and more details.")
    promote_subparser.add_argument("-u", "--update_name", help=arg_help,
                                   action="store_true")
    promote_subparser.set_defaults(func=promote)

    return parser


def create_search_func(obj_method):
    """Generates a function to perform basic list and xml queries.

    Args:
        obj_method: A function that searches for a JSSObject.
            Probably one of the jss.JSS helper methods.
            (e.g. jss.JSS.Package)

    Returns:
        A function that takes one argument of Argparser args, with a
        'search' property to be passed to the obj_method if needed.
    """
    def search_func(args):
        """Searches JSS for all objects OR a specific object.

        Prints results as a list or an individual object differently
        for purposes of output.

        Args:
            args: argparser args with properties:
                search: Name or ID of object to search for.
        """
        results = search_for_object(obj_method, args.search)

        if results is None:
            print "Object: %s does not exist!" % args.search
        # TODO: Should this be isinstance(results, JSSObjectList) and
        # drop the wrapping of obj_method(search) in a list in
        # search_for_objects?
        elif len(results) > 1:
            print build_results_string(None, results)
        else:
            for result in results:
                print result

    return search_func


def search_for_object(obj_method, search):
    """Return objects matching a search pattern.

    Manages making the appropriate searches based on the type of
    search query.

    Args:
        obj_method: Func to call to perform the search. Assumes that
            the second argument, search, will be passable as the sole
            argument to that func. The intention is to pass a search
            method from the jss.JSS object, e.g.
            "jss_connection.Package"
        search: A name, ID, or wildcard search (see func
            wildcard_search). Used as the argument to "obj_method".

    Returns:
        A list of JSSObjects, a JSSObjectList, or None.
    """
    search_is_wildcard = False
    if search:
        for wildcard in WILDCARDS:
            if wildcard in search:
                search_is_wildcard = True

    if search_is_wildcard:
        wildcard_results = wildcard_search(obj_method(), search)
        results = []
        for obj in wildcard_results:
            try:
                results.append(obj_method(obj["name"]))
            except jss.JSSGetError:
                continue

        if not results:
            results = None
    else:
        if search:
            try:
                results = [obj_method(search)]
            except jss.JSSGetError:
                results = None
        else:
            try:
                results = obj_method()
            except jss.JSSGetError:
                results = None

    return results


def get_package_info(package_name):
    """Return the package basename and version as a tuple."""
    # Product name should be a combination of letters, numbers,
    # hyphens, or underscores.
    # A " ", "-", or "_" should separate the name from the version.
    # whitespace, hyphens, or underscores
    # The version then is any number of digits, followed by any number
    # of letters, numbers, separated by "-", "_", "."s.
    # Finally, an extension of ".pkg", ".pkg.zip", or ".dmg" must
    # follow.
    package_regex = (r"^(?P<basename>[\w\s\-]+)[\s\-_]"
                     r"(?P<version>[\d]+[\w.\-]*)"
                     r"(?P<extension>\.(pkg(\.zip)?|dmg))$")
    match = re.search(package_regex, package_name)
    if match:
        result = match.group("basename", "version")
    else:
        result = (None, None)
    return result


def update_name(policy, cur_pkg_name, new_pkg_name):
    """Try to update policy name with package info.

    Try to replace the product name and version in the policy's name
    with the new values.

    Changes passed policy object if possible; otherwise raises an
    exception.

    Args:
        policy: A Policy object to update.
        cur_pkg_name: String name of the current package.
        new_pkg_name: String name of the updated package.

    Raises:
        Exception: One or more of the arguments were not formatted
            correctly for text replacement to occur.
    """
    policy_name_element = policy.find("general/name")
    cur_pkg_basename, cur_pkg_version = get_package_info(cur_pkg_name)
    new_pkg_basename, new_pkg_version = get_package_info(new_pkg_name)

    changes = [cur_pkg_basename, cur_pkg_version, new_pkg_basename,
               new_pkg_version]
    if all(changes):
        name = policy_name_element.text
        new_name = name.replace(cur_pkg_basename, new_pkg_basename)
        new_name = new_name.replace(cur_pkg_version, new_pkg_version)
        print "Old name: %s" % name
        print "New name: %s" % new_name
        policy_name_element.text = new_name
    else:
        raise ValueError("Unable to update policy name!")


def get_newest_pkg(options):
    """Get the newest package from a list of a packages.

    Args:
        options: List of package names.

    Returns: Either the newest package name or None. Package names
        must be in some format that get_package_info() can extract a
        version number.
    """
    versions = {get_package_info(package)[1]: package for package
                in options if get_package_info(package)[1]}
    if versions:
        newest = max([LooseVersion(version) for version in versions])
        result = versions[str(newest)]
    else:
        result = None

    return result


def log_warning(policy):
    """Print warning about flushing the logs if triggers in policy."""
    if policy.findtext("general/frequency") != "Ongoing":
        triggers = ["trigger_checkin", "trigger_enrollment_complete",
                    "trigger_login", "trigger_logout",
                    "trigger_network_state_changed", "trigger_startup",
                    "trigger_other"]
        for trigger in triggers:
            value = policy.findtext("general/" + trigger)
            # Value can be string "false" or "" for "trigger_other".
            if value not in [None, "False"]:
                print "Remember to flush the policy logs!"
                open_policy_log_in_browser(policy)
                break


def open_policy_log_in_browser(policy):
    """Open a policy's log page in the default browser."""
    url = JSSConnection.get().base_url + "/policies.html?id=%s&o=l" % policy.id
    if jss.tools.is_linux():
        subprocess.check_call(["xdg-open", url])
    elif jss.tools.is_osx():
        subprocess.check_call(["open", url])


def _build_package_version_dict():
    """Build a dictionary of package products with multiple versions.

    Returns:
        A dictionary of packages with multiple versions on the server:
            key: Package basename (string)
            value: List of package versions of type
                distutil.version.LooseVersion
    """
    packages = [package.name for package in JSSConnection.get().Package()]
    package_version_dict = {}
    for package in packages:
        package_name, package_version = get_package_info(package)
        # Convert string version to something we can cmp.
        if package_name:
            if package_name not in package_version_dict:
                package_version_dict[package_name] = [
                    LooseVersion(package_version)]
            else:
                package_version_dict[package_name].append(
                    LooseVersion(package_version))

    # Narrow down packages list to only products which have multiple
    # packages on the JSS.
    multiples = {package: package_version_dict[package] for package in
                 package_version_dict if
                 len(package_version_dict[package]) > 1}
    return multiples


def _get_updatable_policies(policies):
    """Get a list of policies where newer pkg versions are available.

    Packages must have names which can be successfully split into
    product name and version with get_package_info().

    Args:
        policies: A list of Policy objects.

    Returns:
        A list of strings; the names of policies which install a
        package that is older than another package available on the
        JSS.
    """
    multiples = _build_package_version_dict()

    # For each policy, lookup any packages it installs in the multiples
    # dictionary and see if there is a newer version available.
    updates_available = []
    search = "package_configuration/packages/package/name"
    for policy in policies:
        packages_installed = [package.text for package in
                              policy.findall(search)]
        for package in packages_installed:
            pkg_name, pkg_version = get_package_info(package)
            if pkg_name in multiples:
                if LooseVersion(pkg_version) < max(multiples[pkg_name]):
                    updates_available.append(policy)
                    break

    # Make a new list of just names (rather than the full XML)
    updates_available_names = [policy.findtext("general/name") for policy in
                               updates_available]

    return updates_available_names


def _add_flags_to_list(flags, options):
    """Add a set of flags to options which match.

    See the documentation for ask_user() for full details.

        Args:
            flags: Dynamically mark some options with extra
                text. For example, make an option "Default".

                Key: String name of text to append to option in list.
                Value: Function for matching an option. The function
                    must return a bool.

                e.g.: {"CURRENT": lambda f: current_package in f}
                    where "current_package" is a variable with the desired
                    value.

            options: A list of strings to append text to.

        Returns:
            A list of flagged options. It does not mutate "options".
    """
    # Copy list to make sure we don't mutate any values.
    flagged_options = list(options)
    if flags:
        # Make a list of matches, then append text to each match.
        for flag in flags:
            matches = [option for option in flagged_options if
                       flags[flag](option)]
            for match in matches:
                flagged_options[flagged_options.index(match)] += " (%s)" % flag
    return flagged_options


def get_scoped_to_all(containers):
    """Find objects scoped to all computers/mobile devices.

    Args:
        containers: A list of jss.Policy,
            jss.OSXConfigurationProfile, or
            jss.MobileDeviceConfigurationProfile objects.
    Returns:
        A list of JSSObjects.
    """
    results = []
    for container in containers:
        # pylint: disable=unidiomatic-typecheck
        # TODO: This can be slightly compacted.
        if type(container) in [jss.Policy, jss.OSXConfigurationProfile]:
            if container.findtext("scope/all_computers") == "true":
                results.append(container)
        elif type(container) in [jss.MobileDeviceConfigurationProfile]:
            if container.findtext("scope/all_mobile_devices") == "true":
                results.append(container)
        # pylint: enable=unidiomatic-typecheck
    return results


def wildcard_search(objects, pattern, case_sensitive=True):
    """Search for names that match a Unix-shell style pattern.

    Args:
        objects: Iterable of JSSObjects with a .name property.
        pattern: String pattern to search for, with the following
            characters used as wildcards:
                "*": Matches everything.
                "?": Matches any single character.
                "[seq]": Matches any character in seq.
                "[!seq]": Matches any character not in seq.
                To escqpe a wildcard character, wrap it in brackets;
                e.g.: "[?]" matches a "?".
        case_sensitive: Boolean value whether to make comparison with
            case sensitivity. Defaults to "True".

    Returns:
        List of all JSSObjects which match the wildcard.
    """
    # The fnmatch module uses OS-specific case sensitivity settings.
    # We are not matching filenames, so we don't care what the
    # filesystem wants.

    # It would probably be easier to just copy the fnmatch source here
    # and edit fnmatch.fnmatch to do what we need!
    if not case_sensitive:
        test_names = [(obj, obj.name.upper()) for obj in objects]
    else:
        test_names = [(obj, obj.name) for obj in objects]

    results = [obj for obj, name in test_names if
               fnmatch.fnmatchcase(name, pattern)]

    return results


def find_groups_in_scope(groups, scopables):
    """Find groups which are scoped in scopables.

    Args:
        groups: A list of jss ComputerGroup or MobileDeviceGroup objects.
        scopables: A list of JSSObjects or a jss.JSSObjectList of some
            types which have a "scope" subelement (Policy,
            OSXConfigurationProfile, MobileDeviceConfigurationProfile).

    Returns: A list of JSSObjects which match.
    """
    if isinstance(scopables, jss.JSSObjectList):
        scopables = scopables.retrieve_all()
    if scopables and (type(scopables[0]) in
                      [jss.Policy, jss.OSXConfigurationProfile]):
        search = "scope/computer_groups/computer_group"
    elif scopables and isinstance(scopables[0],
                                  jss.MobileDeviceConfigurationProfile):
        search = "scope/mobile_device_groups/mobile_device_group"

    return find_objects_in_containers(groups, search, scopables)


# Actions #####################################################################
def get_scoped(args):
    """Print all policies and config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of computer group.
    """
    jss_connection = JSSConnection.get()
    group = jss_connection.ComputerGroup(args.group)

    # Search for policies.
    policies = jss_connection.Policy()
    policy_results = find_groups_in_scope([group], policies)
    policy_heading = "Policies scoped to %s" % group.name
    output = build_results_string(policy_heading, policy_results) + "\n"

    policy_results = get_scoped_to_all(policies)
    policy_heading = "Policies scoped to all computers"
    output += build_results_string(policy_heading, policy_results) + "\n"

    # Search for configuration profiles.
    configps = jss_connection.OSXConfigurationProfile()
    configp_results = find_groups_in_scope([group], configps)
    configp_heading = "Configuration profiles scoped to %s" % group.name
    output += build_results_string(configp_heading, configp_results) + "\n"
    configp_results = get_scoped_to_all(configps)
    configp_heading = "Configuration profiles scoped to all computers"
    output += build_results_string(configp_heading, configp_results)

    print output


def get_md_scoped(args):
    """Print all mobile device config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of group.
    """
    jss_connection = JSSConnection.get()
    group = jss_connection.MobileDeviceGroup(args.group)

    configps = jss_connection.MobileDeviceConfigurationProfile()
    results = find_groups_in_scope([group], configps)
    output = build_results_string("Profiles scoped to %s" % group.name,
                                  results) + "\n"
    results = get_scoped_to_all(configps)
    output += build_results_string("Profiles scoped to all mobile devices",
                                   results)

    print output


def get_group_scope_diff(args):
    """Print a diff of all policies scoped to two different groups.

    Args:
        args: argparser args with properties:
            group1: Name or ID of first computer group.
            group2: Name or ID of second computer group.
    """
    # TODO: This can just run scoped twice and then do the file diff.
    jss_connection = JSSConnection.get()
    policies = jss_connection.Policy()
    policies.sort()
    group1 = jss_connection.ComputerGroup(args.group1)
    group2 = jss_connection.ComputerGroup(args.group2)
    results1 = find_groups_in_scope([group1], policies)
    results2 = find_groups_in_scope([group2], policies)
    scoped_to_all = get_scoped_to_all(policies)

    configps = jss_connection.OSXConfigurationProfile()
    configps.sort()
    configp_results1 = find_groups_in_scope([group1], configps)
    configp_results2 = find_groups_in_scope([group2], configps)
    configp_scoped_to_all = get_scoped_to_all(configps)

    # I tried to do this with the tempfile module, but the files always
    # ended up being size 0 and dissappearing, despite delete=False.
    with open("/tmp/file1", mode="w") as file1:
        output = build_results_string("Policies scoped to %s" % group1.name,
                                      results1) + "\n"
        policy_heading = "Policies scoped to all computers"
        output += build_results_string(policy_heading, scoped_to_all) + "\n"
        output += build_results_string("Configuration profiles scoped to %s"
                                       % group1.name, configp_results1) + "\n"
        configp_heading = "Configuration profiles scoped to all computers"
        output += build_results_string(configp_heading, configp_scoped_to_all)
        # Add a newline to keep diff from complaining.
        file1.write(output + "\n")
        file1_name = file1.name
    with open("/tmp/file2", mode="w") as file2:
        output = build_results_string("Policies scoped to %s" % group2.name,
                                      results2) + "\n"
        policy_heading = "Policies scoped to all computers"
        output += build_results_string(policy_heading, scoped_to_all) + "\n"
        output += build_results_string("Configuration profiles scoped to %s"
                                       % group2.name, configp_results2)
        configp_heading = "Configuration profiles scoped to all computers"
        output += build_results_string(configp_heading, configp_scoped_to_all)
        # Add a newline to keep diff from complaining.
        file2.write(output + "\n")
        file2_name = file2.name

    # Diff will return 1 if files differ, so we have to catch that
    # error.
    try:
        result = subprocess.check_output(
            ["diff", "-dy", file1_name, file2_name])
    except subprocess.CalledProcessError as err:
        result = err.output

    print result


def get_md_scope_diff(args):
    """Print a diff of all configuration profiles scoped to two groups.

    Args:
        args: argparser args with properties:
            group1: Name or ID of first group.
            group2: Name or ID of second group.
    """
    jss_connection = JSSConnection.get()
    profiles = jss_connection.MobileDeviceConfigurationProfile()
    group1 = jss_connection.MobileDeviceGroup(args.group1)
    group2 = jss_connection.MobileDeviceGroup(args.group2)
    results1 = find_groups_in_scope([group1], profiles)
    results2 = find_groups_in_scope([group2], profiles)
    scoped_to_all = get_scoped_to_all(profiles)

    # I tried to do this with the tempfile module, but the files always
    # ended up being size 0 and dissappearing, despite delete=False.
    with open("/tmp/file1_name", mode="w") as file1:
        output = build_results_string("Profiles scoped to %s" % group1.name,
                                      results1) + "\n"
        output += build_results_string("Profiles scoped to all mobile devices",
                                       scoped_to_all)
        # Add a newline to keep diff from complaining.
        file1.write(output + "\n")
        file1_name = file1.name
    with open("/tmp/file2_name", mode="w") as file2:
        output = build_results_string("Profiles scoped to %s" % group2.name,
                                      results2) + "\n"
        output += build_results_string("Profiles scoped to all mobile devices",
                                       scoped_to_all)
        # Add a newline to keep diff from complaining.
        file2.write(output + "\n")
        file2_name = file2.name

    # Diff will return 1 if files differ, so we have to catch that
    # error.
    try:
        result = subprocess.check_output(
            ["diff", "-dy", file1_name, file2_name])
    except subprocess.CalledProcessError as err:
        result = err.output

    print result


def batch_scope(args):
    """Scope a list of policies to a computer group.

    Args:
        args: argparser args with properties:
            group: Name, wildcard search, or ID of computer group.
            policy: List of ID's or names of policies to scope.
                Wildcard searches accepted.
    """
    jss_connection = JSSConnection.get()
    groups = search_for_object(jss_connection.ComputerGroup, args.group)
    print "Scoping to groups: %s" % ", ".join([group.name for group in groups])
    print 79 * "-"
    for policy_query in args.policy:
        policies = search_for_object(jss_connection.Policy, policy_query)
        for policy in policies:
            for group in groups:
                policy.add_object_to_scope(group)
            policy.save()
            print "%s: Success." % policy.name


def group_search_or_modify(args):
    """Perform a group search or add/remove computers from group.

    Args:
        args: argparser args with properties:
            search: Name or ID of computer group.
            add: List of ID, name, or name wildcard searches to add.
            remove: List of ID, name, or name wildcard searches to
                remove.
            dry_run: Bool whether to save or just print group XML.
    """
    # TODO: There's a lot of duplication and need of refactoring here.
    jss_connection = JSSConnection.get()
    if not args.search and (args.add or args.remove):
        print "Please provide a group to add or remove from."
        sys.exit(1)
    elif args.search and (args.add or args.remove):
        computers = jss_connection.Computer()
        try:
            group = jss_connection.ComputerGroup(args.search)
        except jss.exceptions.JSSGetError:
            print "Group not found."
            sys.exit(1)
        if args.add:
            add_computers = []
            for computer_search in args.add:
                search_is_wildcard = False
                for wildcard in WILDCARDS:
                    if wildcard in computer_search:
                        search_is_wildcard = True
                        break

                full_computers = []
                if search_is_wildcard:
                    search_results = [computer["name"] for computer in
                                      wildcard_search(computers,
                                                      computer_search)]
                    full_computers.extend(search_results)
                else:
                    full_computers.append(computer_search)

                for computer in full_computers:
                    try:
                        add_computers.append(
                            jss_connection.Computer(computer))
                    except jss.exceptions.JSSGetError:
                        continue

            for computer in add_computers:
                print "Adding %s to %s" % (computer.name, group.name)
                group.add_computer(computer)

        if args.remove:
            remove_computers = []
            for computer_search in args.remove:
                search_is_wildcard = False
                for wildcard in WILDCARDS:
                    if wildcard in computer_search:
                        search_is_wildcard = True
                        break

                full_computers = []
                if search_is_wildcard:
                    search_results = [computer["name"] for computer in
                                      wildcard_search(computers,
                                                      computer_search)]
                    full_computers.extend(search_results)
                else:
                    full_computers.append(computer_search)

                for computer in full_computers:
                    try:
                        remove_computers.append(
                            jss_connection.Computer(computer))
                    except jss.exceptions.JSSGetError:
                        continue

            for computer in remove_computers:
                print "Removing %s from %s" % (computer.name, group.name)
                try:
                    group.remove_computer(computer)
                except ValueError:
                    print "%s is not a member; not removing." % computer.name

        if args.dry_run:
            print group
        else:
            group.save()

    else:
        search_func = create_search_func(jss_connection.ComputerGroup)
        search_func(args)


def get_excluded(args):
    """Print all policies and config profiles with group excluded.

    Args:
        args: argparser args with properties:
            group: Name or ID of computer group.
    """
    group = JSSConnection.get().ComputerGroup(args.group)
    _get_exclusions_by_type(group)


def get_md_excluded(args):
    """Print all mobile device config profiles with group excluded.

    Args:
        args: argparser args with properties:
            group: Name or ID of mobile device group.
    """
    group = JSSConnection.get().MobileDeviceGroup(args.group)
    _get_exclusions_by_type(group)


def _get_exclusions_by_type(group):
    """Private function for retrieving excluded groups.

    Will handle both mobile device and computer group exclusions.

    Args:
        group: A jss.ComputerGroup or jss.MobileDeviceGroup object.
    """
    jss_connection = JSSConnection.get()
    scopables = []
    header = " with %s excluded from scope." % group.name
    base_search = "scope/exclusions/%s_groups/%s_group"

    if isinstance(group, jss.ComputerGroup):
        search = base_search % ("computer", "computer")
        scopables.append({"containers": jss_connection.Policy(),
                          "heading": "Policies"})
        scopables.append(
            {"containers": jss_connection.OSXConfigurationProfile(),
             "heading": "Configuration Profiles"})
    elif isinstance(group, jss.MobileDeviceGroup):
        search = base_search % ("mobile_device", "mobile_device")
        scopables.append(
            {"containers": jss_connection.MobileDeviceConfigurationProfile(),
             "heading": "Mobile Device Configuration Profiles"})

    for item in scopables:
        results = find_objects_in_containers(group, search,
                                             item["containers"])
        output = build_results_string(item["heading"] + header, results)
        print output


def get_package_policies(args):
    """Print all policies which install a package.

    Args:
        args: argparser args with properties:
            package: ID, name, or wildcard-search-name of package.
    """
    search = "package_configuration/packages/package"
    jss_connection = JSSConnection.get()
    policies = jss_connection.Policy()
    packages = search_for_object(jss_connection.Package, args.package)

    results = set(find_objects_in_containers(packages, search, policies))
    output = build_results_string("Policies which install '%s'" % args.package,
                                  results) + "\n"

    search = "packages/package"
    imaging_configs = jss_connection.ComputerConfiguration()
    ic_results = set(find_objects_in_containers(packages, search,
                                                imaging_configs))
    output += build_results_string("Imaging configs which install '%s'" %
                                   args.package, ic_results)
    print output


# pylint: disable=too-many-locals
def promote(args):
    """Replace a package in a policy with another package.

    Designed with the intention of facilitating promotion from
    development to production of a package.

    If any arg is missing, an interactive menu will be displayed.

    Args:
        args: argparser args with properties:
            new_package: ID or name of package to install.
            policy: Name or ID of policy.
            update_name: Bool, Will atttempt to update the policy name
                with the new package name (minus the extension). e.g.
                "Install NetHack-3.4.3" will result in "Install
                NetHack-3.4.4".

                The policy name must include the exact package name,
                and version number for this to do anything.
    """
    jss_connection = JSSConnection.get()
    if args.policy:
        policy = jss_connection.Policy(args.policy)
    else:
        # Interactive policy menu
        print ("No policy specified in args: Building a list of policies "
               "which have newer packages available...")
        # Get full policy XML for all policies.
        policy_list = jss_connection.Policy()
        print "Retrieving %i policies. Please wait..." % len(policy_list)
        all_policies = policy_list.retrieve_all()

        # Get lists of policies with available updates, and all
        # policies which install packages.
        with_updates = _get_updatable_policies(all_policies)
        install_policies = [
            policy.name for policy in all_policies if
            int(policy.findtext("package_configuration/packages/size")) > 0]

        policy_name = prompt_user(with_updates, expandable=install_policies)
        policy = jss_connection.Policy(policy_name)

    cur_pkg = policy.findtext("package_configuration/packages/package/name")
    cur_pkg_basename, _ = get_package_info(cur_pkg)

    if args.new_package:
        new_pkg_name = args.new_package
    else:
        # Interactive package menu.

        # Build a list of ALL packages.
        full_options = [package.name for package in jss_connection.Package()]
        # Build a list of packages with same product name as policy.
        matching_options = [option for option in full_options if
                            cur_pkg_basename and cur_pkg_basename.upper() in
                            option.upper()]

        # Sort the package lists by name, then version.
        sorted_full_options = sort_package_list(full_options)
        sorted_matching_options = sort_package_list(matching_options)

        # Build flags for menu.
        flags = {"CURRENT": lambda f: cur_pkg in f}
        default = get_newest_pkg(matching_options)
        if default:
            flags["DEFAULT"] = lambda f: default in f

        new_pkg_name = prompt_user(
            sorted_matching_options, expandable=sorted_full_options,
            flags=flags)

    policy.remove_object_from_list(cur_pkg, "package_configuration/packages")
    policy.add_package(jss_connection.Package(new_pkg_name))

    if args.update_name:
        try:
            update_name(policy, cur_pkg, new_pkg_name)
        except ValueError:
            print "Unable to update policy name!"

    policy.save()
    log_warning(policy)
# pylint: enable=too-many-locals


def main():
    """Run as a cli command."""
    version_check()
    jss_connection = JSSConnection.get()

    parser = build_argument_parser()
    args = parser.parse_args()
    if args.v:
        jss_connection.verbose = True
    # Until I add a toggle method...
    jss_connection.session.verify = args.ssl

    try:
        args.func(args)
    except KeyboardInterrupt:
        # User wishes to bail.
        sys.exit(1)


if __name__ == "__main__":
    main()
