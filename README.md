# jss_helper

## Introduction
jss_helper is a powerful commandline interface for managing and auditing your Casper JSS.

At first glance, it's a quick and easy way to query for objects like Policies, Packages, Smart Groups, etc. You can view lists of *all* Packages, or you can look at the actual XML representing a single package.

Where things get interesting, however, are the advanced features. jss_helper lets you do things that are not possible any other way.

- You can look at all of the policies scoped to a single group, or you can compare two groups' lists of scoped policies.
- With `promote`, you can easily, with an interactive menu, replace packages in policies with newer packages. jss_helper is smart about prompting you with out-of-date policies and showing you only relevent packages, although you can always see a full list too. And if you know your ID's, you can run the entire command from the commandline and skip the menu. `promote` will even update the policy's name with the new package version if applicable.
- Scope an entire list of policies to a group in one command. Useful if you're restructuring or adding a new group.
- See a list of all policies which do package installs.

## Installation
Either grab the package from the releases section, or follow below for manual installation.

Copy jss_helper and jss_helper_lib somewhere in your path. (Recommended:  `/usr/local/bin`)

jss_helper requires python-jss, a python module for interacting with the JSS API.

If you don't have pip:
```
sudo easy_install python-jss
```
Install the python-jss module.

```
sudo pip install python-jss
```

## Setup
You need to create a preferences file to specify the address of your JSS, and credentials.

To do so, issue the following commands:
```
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_user <username>
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_pass <password>
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_url <url>
```

_NOTE_: `jss_helper` doesn't use SSL verification by default. If you need or want this, include the `--ssl` option to `jss_helper`.

This may or may not work depending on a number of factors, including your python version, and related SSL packages. See [python-jss](https://www.github.com/sheagcraig/python-jss) documentation for details on making SSL verification work, including with SNI.

## Basic Usage
To see a list of verbs, try: `jss_helper.py -h`
```
usage: jss_helper [-h] [-v] [--ssl]  ...

Query the JSS.

optional arguments:
  -h, --help      show this help message and exit
  -v              Verbose output.
  --ssl           Use SSL verification

Actions:
  
    category      List all categories, or search for an individual category.
    computer      List all computers, or search for an individual computer.
    configp       List all configuration profiles, or search for an individual
                  configuration profile.
    excluded      List all policies and configuration profiles from which a
                  computer group is excluded.
    group         List all computer groups, or search for an individual group.
    imaging_config
                  List all Casper Imaging computer configurations, or search
                  for an individual computer configuration.
    installs      Lists all policies and imaging configurations which install
                  a package.
    md            List all mobile devices, or search for an indvidual mobile
                  device.
    md_configp    List all mobile device configuration profiles, or search for
                  an individual mobile device configuration profile.
    md_excluded   List all configuration profiles from which a mobile device
                  group is excluded.
    md_group      List all mobile device groups, or search for an individual
                  mobile device group.
    md_scope_diff
                  Show the differences between two mobile device groups'
                  scoped mobile device configuration profiles.
    md_scoped     List all mobile device configuration profiles scoped to a
                  mobile device group.
    package       List of all packages, or search for an individual package.
    policy        List all policies, or search for an individual policy.
    scope_diff    Show the difference between two groups' scoped policies and
                  configuration profiles.
    scoped        List all policies and configuration profiles scoped to a
                  computer group.
    batch_scope   Scope a list of policies to a group.
    promote       Promote a package from development to production by updating
                  an existing production policy with a newer package.
```

Many of these verbs require further arguments. You can view them by doing a -h on them; e.g. `jss_helper group -h`.

## Querying For Objects
Many of jss_helper's verbs do list or detail lookups on a JSS object type. For example,
```
jss_helper group
```
returns a list of all of the groups on the server.

To look at the details for a group, provide the ID or name of that group like so:
```
jss_helper group 42
```
or
```
jss_helper group "AwesomePeople"
```
Currently supported objects/subcommands are:
- category
- computer
- configp (OSX Configuration Profiles)
- group (Computer groups)
- imaging_config (Computer Imaging Configurations)
- md (mobile devices)
- md_configp (mobile device configuration profiles)
- md_group (mobile device group)
- package
- policy

  These all work in much the same way-specify the verb for a list, or add an ID or name to look at details for one object.

## The Magic; Advanced Features
There are a number of advanced verbs which I wrote to help me with managing and auditing our JSS's objects and configurations.

- `installs` lists all policies and computer imaging configurations which install a provided package (name or ID).
- `scoped` and `md_scoped` give you the ability to see all of the policies or configuration profiles scoped to a group. _Note_: This does not include anything scoped to "All Computers"
	- Example: `jss_helper scoped "Testing Group"`
- `scope_diff` and `md_scope_diff` compare the policies and profiles scoped to two different groups, using `diff` to display the differences.
- `batch_scope` allows you to scope a number of policies to a group.
	- Example: `jss_helper batch_scope "Testing Group" 52 100 242 40 6273`
	- Example: `jss_helper batch_scope "US ??? Lab" "Install Printer Drivers: *" 52 100`
		- Would scope all printer driver policies, and policies 52 and 100 to all groups found in the wildcard search "US ??? Lab".
- `promote` allows you to update a package installation policy with a newer version.
	- With no arguments will prompt you to select a policy and package. The interactive menu will initially show you policies which have newer packages available, and packages which match the existing package name. Selecting "F" from the menu gives you the full list of policies or packages. See the [Package Info](#package-info) section below for more details on proper naming conventions.
	- Given a policy (name or ID) and a package (ID or name), will swap the old package for the new in that policy.
    - The optional argument `-u/--update_name` allows you to also update the name, by replacing the package name and the package version if found in the policy name. A policy named "Install Goat Simulator-1.2.0" would get changed to "Install Goat Simulator-1.3.1". See the [Package Info](#package-info) section for further details on naming.
- Add and remove computers from a group with `group`, using the `--add` and `--remove` options, which can be combined with any number of ID's, names, or wildcard searches to add and remove computers.
	- Example: `jss_helper group "Testing" --add "US800-??" --remove 500 HastursMacbook`
	- There's also a `--dry-run` option for safety!
- `excluded` and `md_excluded` show policies and profiles from which a computer or mobile device have been excluded.

## Package Info
jss_helper uses a regular expression wherever packages are involved for splitting their name into a product name and a version. This regex isn't infallible, but it works pretty well, as long as you follow some simple naming best-practices:
- Packages should have names that match their filename (i.e. for a file named "x.pkg", don't have a package name on the JSS of "x", have "x.pkg").
- The package's product name comes first. This name can include all alphanumeric characters, underscores, and hyphens.
- The final space, underscore, or hyphen indicates the split between product name and version number.
- The version number should be a number of dot, underscore, or hyphen separated numbers and letter. These are frequently converted to objects of type `distutils.version.LooseVersion`, which is pretty lenient.
- The extension, while not used, must be one of ".pkg", ".dmg", or ".pkg.zip".

### Examples of Valid Package Names:
- `Goat Simulator-1.3.1.pkg`
- `Goat_Simulator 1.3.1.pkg`
- `Goat2 Simulator-1.3.1a323423TESTING.pkg.zip`

For reference, the regex is:
```
package_regex = (r"^(?P<basename>[\w\s\-]+)[\s\-_]"
				 r"(?P<version>[\d]+[\w.\-]*)"
				 r"(?P<extension>\.(pkg(\.zip)?|dmg))$")
```

## Issues, Upcoming Features
- `policy_by_group` can't search for "all computers". (Will add soon!)
- Installer package!
