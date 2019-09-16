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


"""actions.py

Functions called by jss_helper, implementing all top-level actions.
"""


import argparse
import os
import sys

sys.path.insert(0, '/Library/Application Support/JSSImporter')

import jss

from .jss_connection import JSSConnection
from . import tools

# pylint: disable=no-name-in-module
from Foundation import (NSData,
                        NSPropertyListSerialization,
                        NSPropertyListMutableContainersAndLeaves,
                        NSPropertyListXMLFormat_v1_0)
# pylint: enable=no-name-in-module


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = "~/Library/Preferences/com.github.autopkg.plist"
PYTHON_JSS_PREFERENCES = (
    "~/Library/Preferences/com.github.sheagcraig.python-jss.plist")


class Plist(dict):
    """Abbreviated plist representation (as a dict)."""

    def __init__(self, filename=None):
        """Init a Plist, optionally from parsing an existing file.

        Args:
            filename: String path to a plist file.
        """
        if filename:
            dict.__init__(self, self.read_file(filename))
        else:
            dict.__init__(self)
            self.new_plist()

    def read_file(self, path):
        """Replace internal XML dict with data from plist at path.

        Args:
            path: String path to a plist file.

        Raises:
            PlistParseError: Error in reading plist file.
        """
        # pylint: disable=unused-variable
        info, pformat, error = (
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                NSData.dataWithContentsOfFile_(os.path.expanduser(path)),
                NSPropertyListMutableContainersAndLeaves,
                None,
                None
            ))
        # pylint: enable=unused-variable
        if info is None:
            if error is None:
                error = "Invalid plist file."
            raise PlistParseError("Can't read %s: %s" % (path, error))

        return info

    def write_plist(self, path):
        """Write plist to path.

        Args:
            path: String path to desired plist file.

        Raises:
            PlistDataError: There was an error in the data.
            PlistWriteError: Plist could not be written.
        """
        plist_data, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
            self,
            NSPropertyListXMLFormat_v1_0,
            0,
            None)
        if plist_data is None:
            if error is None:
                error = "Failed to serialize data to plist."
            raise PlistDataError(error)
        else:
            if not plist_data.writeToFile_atomically_(
                    os.path.expanduser(path), True):
                raise PlistWriteError("Failed writing data to %s" % path)

    def new_plist(self):
        """Generate a barebones recipe plist."""
        # Not implemented at this time.
        pass


def connect():
    """make the connection to the JSS"""

    # get AutoPkg configuration settings for JSSImporter,
    # and barring that, get python-jss settings.
    if os.path.exists(os.path.expanduser(AUTOPKG_PREFERENCES)):
        autopkg_env = Plist(AUTOPKG_PREFERENCES)
        connection = map_jssimporter_prefs(autopkg_env)
        print "Preferences: %s\n" % AUTOPKG_PREFERENCES
    elif os.path.exists(os.path.expanduser(PYTHON_JSS_PREFERENCES)):
        jss_env = Plist(PYTHON_JSS_PREFERENCES)
        connection = map_jssimporter_prefs(jss_env)
        print "Preferences: %s\n" % PYTHON_JSS_PREFERENCES
    else:
        sys.exit("No python-jss or AutoPKG/JSSImporter configuration "
                     "file!")
    JSSConnection.setup(connection)


def map_jssimporter_prefs(prefs):
    """Convert python-jss preferences to JSSImporter preferences."""
    connection = {}
    connection["url"] = prefs["JSS_URL"]
    connection["user"] = prefs["API_USERNAME"]
    connection["password"] = prefs["API_PASSWORD"]
    connection["ssl_verify"] = prefs.get("JSS_VERIFY_SSL", True)
    connection["suppress_warnings"] = prefs.get("JSS_SUPPRESS_WARNINGS", True)
    connection["jss_migrated"] = prefs.get("JSS_MIGRATED", True)
    connection["repo_prefs"] = prefs.get("JSS_REPOS")
    print('JSS: {}'.format(connection["url"]))

    return connection


def build_argparser():
    """Build the argument parser for jss_helper.

    Returns: A configured argparse parser.
    """
    # Create our argument parser
    parser = argparse.ArgumentParser(description="Query the Jamf Pro Server.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output (does nothing at present).")
    parser.add_argument("--nossl", default=False, action="store_true",
                        help="Does nothing, because JSS_VERIFY_SSL is now used.")
    parser.add_argument("--ssl", default=True, action="store_true",
                        help="Does nothing, because ssl is now the default.")
    subparser = parser.add_subparsers(dest="subparser_name", title="Actions",
                                      metavar="")

    subparsers = {}

    jss_connection = JSSConnection.get()

    # computer
    subparsers["computer"] = {
        "help": "List all computers, or search for an individual computer.",
        "func": tools.create_search_func(jss_connection.Computer),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "computer.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["configp"] = {
        "help": "List all configuration profiles, or search for an individual "
                "configuration profile.",
        "func": tools.create_search_func(jss_connection.OSXConfigurationProfile),
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
        "func": computer_group_search_or_modify,
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
        "func": tools.create_search_func(jss_connection.ComputerConfiguration),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "computer configuration.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["package"] = {
        "help": "List of all packages, or search for an individual package.",
        "func": tools.create_search_func(jss_connection.Package),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "package.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["policy"] = {
        "help": "List all policies, or search for an individual policy.",
        "func": tools.create_search_func(jss_connection.Policy),
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
        "func": tools.create_search_func(jss_connection.Category),
        "args": {"search": {"help": "ID or name (wildcards allowed) of "
                                    "category.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md"] = {
        "help": "List all mobile devices, or search for an indvidual mobile "
                "device.",
        "func": tools.create_search_func(jss_connection.MobileDevice),
        "args": {"search": {"help": "ID or name (wildcards allowed) of mobile "
                                    "device.",
                            "default": None,
                            "nargs": "?"}}}
    subparsers["md_group"] = {
        "help": "List all mobile device groups, or search for an individual "
                "mobile device group.",
        "func": md_group_search_or_modify,
        "args": {"search": {"help": "ID or name (wildcards allowed) of mobile "
                                    "device group.",
                            "default": None,
                            "nargs": "?"},
                 "--add": {"help": "Mobile device ID's or names to add to "
                                   "group. Wildcards may be used.",
                           "nargs": "*"},
                 "--remove": {"help": "Mobile Device ID's or names to remove "
                                      "from group. Wildcards may be used.",
                              "nargs": "*"},
                 "--dry_run": {"help": "Construct the updated XML for the "
                                       "group, but don't save. Prints "
                                       "results.",
                               "action": "store_true"}}}
    subparsers["md_configp"] = {
        "help": "List all mobile device configuration profiles, or search for "
                "an individual mobile device configuration profile.",
        "func": tools.create_search_func(
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


def get_scoped(args):
    """Print all policies and config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of computer group.
    """
    print _get_scoped(args.group)


def _get_scoped(search_group):
    """Return all policies and config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of computer group.

    Returns:
        Formatted string report.
    """
    jss_connection = JSSConnection.get()
    group = jss_connection.ComputerGroup(search_group)

    # Search for policies.
    policies = jss_connection.Policy().retrieve_all()
    policy_results = tools.find_groups_in_scope([group], policies)
    policy_heading = "Policies scoped to %s" % group.name
    output = tools.build_results_string(policy_heading, policy_results) + "\n"

    policy_results = tools.get_scoped_to_all(policies)
    policy_heading = "Policies scoped to all computers"
    output += tools.build_results_string(policy_heading, policy_results) + "\n"

    # Search for configuration profiles.
    configps = jss_connection.OSXConfigurationProfile().retrieve_all()
    configp_results = tools.find_groups_in_scope([group], configps)
    configp_heading = "Configuration profiles scoped to %s" % group.name
    output += (tools.build_results_string(configp_heading, configp_results) +
               "\n")
    configp_results = tools.get_scoped_to_all(configps)
    configp_heading = "Configuration profiles scoped to all computers"
    output += tools.build_results_string(configp_heading, configp_results)

    return output


def get_md_scoped(args):
    """Print all mobile device config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of group.
    """
    print _get_md_scoped(args.group)


def _get_md_scoped(search_group):
    """Return all mobile device config profiles scoped to a group.

    Args:
        args: argparser args with properties:
            group: Name or ID of group.

    Returns:
        Formatted string report.
    """
    jss_connection = JSSConnection.get()
    group = jss_connection.MobileDeviceGroup(search_group)

    configps = jss_connection.MobileDeviceConfigurationProfile().retrieve_all()
    results = tools.find_groups_in_scope([group], configps)
    output = tools.build_results_string("Profiles scoped to %s" % group.name,
                                        results) + "\n"
    results = tools.get_scoped_to_all(configps)
    output += tools.build_results_string(
        "Profiles scoped to all mobile devices", results)

    return output


def get_group_scope_diff(args):
    """Print a diff of all policies scoped to two different groups.

    Args:
        args: argparser args with properties:
            group1: Name or ID of first computer group.
            group2: Name or ID of second computer group.
    """
    results1 = _get_scoped(args.group1)
    results2 = _get_scoped(args.group2)
    print tools.diff(results1, results2)


def get_md_scope_diff(args):
    """Print a diff of all configuration profiles scoped to two groups.

    Args:
        args: argparser args with properties:
            group1: Name or ID of first group.
            group2: Name or ID of second group.
    """
    results1 = _get_md_scoped(args.group1)
    results2 = _get_md_scoped(args.group2)
    print tools.diff(results1, results2)


def batch_scope(args):
    """Scope a list of policies to a computer group.

    Args:
        args: argparser args with properties:
            group: Name, wildcard search, or ID of computer group.
            policy: List of ID's or names of policies to scope.
                Wildcard searches accepted.
    """
    jss_connection = JSSConnection.get()
    groups = tools.search_for_object(jss_connection.ComputerGroup, args.group)
    print "Scoping to groups: %s" % ", ".join([group.name for group in groups])
    print 79 * "-"
    for policy_query in args.policy:
        policies = tools.search_for_object(jss_connection.Policy, policy_query)
        for policy in policies:
            for group in groups:
                policy.add_object_to_scope(group)
            policy.save()
            print "%s: Success." % policy.name


def computer_group_search_or_modify(args):
    """Perform a group search or add/remove computers from group.

    Args:
        args: argparser args with properties:
            search: Name or ID of computer group.
            add: List of ID, name, or name wildcard searches to add.
            remove: List of ID, name, or name wildcard searches to
                remove.
            dry_run: Bool whether to save or just print group XML.
    """
    jss_connection = JSSConnection.get()
    group_search_method = jss_connection.ComputerGroup
    member_search_method = jss_connection.Computer
    _group_search_or_modify(group_search_method, member_search_method, args)


def md_group_search_or_modify(args):
    """Perform a group search or add/remove mobile devices from group.

    Args:
        args: argparser args with properties:
            search: Name or ID of computer group.
            add: List of ID, name, or name wildcard searches to add.
            remove: List of ID, name, or name wildcard searches to
                remove.
            dry_run: Bool whether to save or just print group XML.
    """
    jss_connection = JSSConnection.get()
    group_search_method = jss_connection.MobileDeviceGroup
    member_search_method = jss_connection.MobileDevice
    _group_search_or_modify(group_search_method, member_search_method, args)


def _group_search_or_modify(group_search_method, member_search_method, args):
    """Perform a group search or add/remove devices from group.

    Args:
        group_search_method: Func to search the Jamf Pro Server for groups.
            (i.e. jss.JSS.ComputerGroup or jss.JSS.MobileDeviceGroup)
        member_search_method: Func to search the Jamf Pro Server for devices.
            (i.e. jss.JSS.Computer or jss.JSS.MobileDevice)
        args: argparser args with properties:
            search: Name or ID of computer group.
            add: List of ID, name, or name wildcard searches to add.
            remove: List of ID, name, or name wildcard searches to
                remove.
            dry_run: Bool whether to save or just print group XML.
    """
    if not args.search and (args.add or args.remove):
        print "Please provide a group to add or remove from."
        sys.exit(1)
    elif args.search and (args.add or args.remove):
        try:
            group = group_search_method(args.search)
        except jss.exceptions.GetError:
            print "Group not found."
            sys.exit(1)

        if args.add:
            add_members = tools.build_group_members(
                member_search_method, args.add)
            tools.add_group_members(group, add_members)

        if args.remove:
            remove_members = tools.build_group_members(
                member_search_method, args.remove)
            tools.remove_group_members(group, remove_members)

        if args.dry_run:
            print group
        else:
            group.save()

    else:
        search_func = tools.create_search_func(
            group_search_method)
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
        results = tools.find_objects_in_containers(group, search,
                                                   item["containers"])
        output = tools.build_results_string(item["heading"] + header, results)
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
    packages = tools.search_for_object(jss_connection.Package, args.package)

    results = set(tools.find_objects_in_containers(packages, search, policies))
    output = tools.build_results_string("Policies which install '%s'" %
                                        args.package, results) + "\n"

    search = "packages/package"
    imaging_configs = jss_connection.ComputerConfiguration()
    ic_results = set(tools.find_objects_in_containers(packages, search,
                                                      imaging_configs))
    output += tools.build_results_string("Imaging configs which install '%s'" %
                                         args.package, ic_results)
    print output


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
    all_packages = jss_connection.Package()

    # Handle policy arguments.
    if args.policy:
        policy = jss_connection.Policy(args.policy)
    else:
        policy_name = tools.policy_menu(jss_connection.Policy(),
                                        all_packages)
        policy = jss_connection.Policy(policy_name)

    cur_pkg = policy.findtext("package_configuration/packages/package/name")

    # Handle package arguments.
    if args.new_package:
        new_pkg_name = args.new_package
    else:
        new_pkg_name = tools.get_pkg_menu(all_packages, cur_pkg)

    # Make changes to policy.
    policy.remove_object_from_list(cur_pkg, "package_configuration/packages")
    policy.add_package(jss_connection.Package(new_pkg_name))

    # Handle policy name updating.
    if args.update_name:
        try:
            tools.update_name(policy, cur_pkg, new_pkg_name)
        except ValueError:
            print "Unable to update policy name!"

    # Save policy and remind user to flush logs if needed.
    policy.save()
    url = JSSConnection.get().base_url
    tools.log_warning(url, policy)
