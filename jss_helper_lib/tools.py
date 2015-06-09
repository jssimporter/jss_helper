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


"""tools.py

Support functions for jss_helper.
"""


from distutils.version import StrictVersion, LooseVersion
import fnmatch
from operator import itemgetter
import re
import subprocess
import sys

import jss


REQUIRED_PYTHON_JSS_VERSION = StrictVersion("0.3.4")
WILDCARDS = "*?[]"


# General Functions ###########################################################
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
        A list of JSSObjects, or a JSSObjectList
    """
    search_is_wildcard = False
    if search:
        for wildcard in WILDCARDS:
            if wildcard in search:
                search_is_wildcard = True

    results = []
    if search_is_wildcard:
        wildcard_results = wildcard_search(obj_method(), search)
        for obj in wildcard_results:
            try:
                results.append(obj_method(obj["name"]))
            except jss.JSSGetError:
                continue
    else:
        if search:
            try:
                results = [obj_method(search)]
            except jss.JSSGetError:
                pass
        else:
            try:
                results = obj_method()
            except jss.JSSGetError:
                pass

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
    if scopables and isinstance(scopables[0],
                                (jss.Policy, jss.OSXConfigurationProfile)):
        search = "scope/computer_groups/computer_group"
    elif scopables and isinstance(scopables[0],
                                  jss.MobileDeviceConfigurationProfile):
        search = "scope/mobile_device_groups/mobile_device_group"

    return find_objects_in_containers(groups, search, scopables)


def get_scoped_to_all(containers):
    """Find objects scoped to all computers/mobile devices.

    Args:
        containers: A jss.Policy, jss.OSXConfigurationProfile, or
            jss.MobileDeviceConfigurationProfile object, or a list of
            those objects.
    Returns:
        A list of JSSObjects.
    """
    if not isinstance(containers, list):
        containers = [containers]

    results = []
    for container in containers:
        if isinstance(container, (jss.Policy, jss.OSXConfigurationProfile)):
            if container.findtext("scope/all_computers") == "true":
                results.append(container)
        elif isinstance(container, (jss.MobileDeviceConfigurationProfile)):
            if container.findtext("scope/all_mobile_devices") == "true":
                results.append(container)
    return results


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

        if not results:
            print "Object: %s does not exist!" % args.search
        elif len(results) > 1:
            print build_results_string(None, results)
        else:
            for result in results:
                print result

    return search_func


def write_text_to_file(ofilename, text):
    """Write text to a file.

    Adds a concluding newline character.

    Args:
        ofilename: Name of file to create.
        text: Text to write.
    """
    with open(ofilename, mode="w") as ofile:
        ofile.write(text + "\n")


def diff(text1, text2):
    """Perform an sdiff comparison of two strings.

    Due to the limitations of diff, strings must first be written to
    temporary files.

    Args:
        text1: First body of text.
        text2: Second body of text.

    Returns:
        Output from sdiff.
    """
    output_tuple = zip(("/tmp/jss_helper_diff_%s.txt" % num for num in
                        xrange(2)), (text1, text2))
    for filename, text in output_tuple:
        write_text_to_file(filename, text)
    # Diff will return 1 if files differ, so we have to catch that
    # error.
    try:
        result = subprocess.check_output(
            ["sdiff", "-d", output_tuple[0][0], output_tuple[1][0]])
    except subprocess.CalledProcessError as err:
        result = err.output

    return result


# Group manipulation functions ###############################################
def build_group_members(obj_search_method, searches):
    """Given a list of searches, build a list of all results.

    Args:
        obj_search_method: jss.JSS search method for the desired device
            type (e.g. jss.JSS.Computer or jss.JSS.MobileDevice).
        searches: List of searches to perform (with search_for_object).

    Returns:
        List of JSSObjects that match the searches.
    """
    devices = [device for obj_search in searches for device in
               search_for_object(obj_search_method, obj_search)]
    return devices


def add_group_members(group, members):
    """Add list of members to computer or md group."""
    if isinstance(group, jss.ComputerGroup):
        add_method = group.add_computer
    elif isinstance(group, jss.MobileDeviceGroup):
        add_method = group.add_mobile_device
    for member in members:
        print "Adding %s to %s" % (member.name, group.name)
        add_method(member)


def remove_group_members(group, members):
    """Remove list of members to computer or md group."""
    if isinstance(group, jss.ComputerGroup):
        remove_method = group.remove_computer
    elif isinstance(group, jss.MobileDeviceGroup):
        remove_method = group.remove_mobile_device
    for member in members:
        print "Removing %s from %s" % (member.name, group.name)
        try:
            remove_method(member)
        except ValueError:
            print "%s is not a member; not removing." % member.name


# Promotion functions #########################################################
def get_updatable_policies(policies, packages):
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
    multiples = _build_package_version_dict(packages)

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


def log_warning(url, policy):
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
                open_policy_log_in_browser(url, policy)
                break


def open_policy_log_in_browser(jss_url, policy):
    """Open a policy's log page in the default browser."""
    url = jss_url + "/policies.html?id=%s&o=l" % policy.id
    if jss.tools.is_linux():
        subprocess.check_call(["xdg-open", url])
    elif jss.tools.is_osx():
        subprocess.check_call(["open", url])


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


def _build_package_version_dict(package_list):
    """Build a dictionary of package products with multiple versions.

    Returns:
        A dictionary of packages with multiple versions on the server:
            key: Package basename (string)
            value: List of package versions of type
                distutil.version.LooseVersion
    """
    packages = [package.name for package in package_list]
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

    # Figure out the number of options, then the length of that number.
    length = len(str(len(options))) + len("\t")
    fmt_string = u"{0[0]:>{length}}: {0[1]}"
    choices = "\n".join([fmt_string.format(option, length=length) for option in
                         enumerate(options)])
    print "\n" + choices


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


