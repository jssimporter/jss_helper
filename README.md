# jss-helper

##Introduction:
jss-helper is a powerful commandline interface for managing and auditing your Casper JSS.

## Installation

Copy jss_helper wherever you may want it (possibly someplace in your path).

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

_NOTE_: ```jss_helper``` doesn't use SSL verification by default. If you need or want this, include the ```--ssl``` option to ```jss_helper```.

This may or may not work depending on a number of factors, including your python version, and related SSL packages. See [python-jss](https://www.github.com/sheagcraig/python-jss) documentation for details on making SSL verification work, including with SNI.

## Basic Usage
To see a list of verbs, try: ```jss_helper.py -h```
```
usage: jss_helper [-h] [-v] [--ssl]  ...

Query the JSS.

optional arguments:
  -h, --help     show this help message and exit
  -v             Verbose output.
  --ssl          Use SSL verification

Actions:
  
    category     List all categories, or search for an individual category.
    computer     List all computers, or search for an individual computer.
    group        List all computer groups, or search for an individual group.
    installs     Lists all policies which install a package.
    md           List all mobile devices, or search for an indvidual mobile
                 device.
    md_configp   List all mobile device configuration profiles, or search for
                 an individual mobile device configuration profile.
    md_group     List all mobile device groups, or search for an individual
                 mobile device group.
    md_scope_diff
                 Show the differences between two mobile device groups' scoped
                 mobile device configuration profiles.
    md_scoped    List all mobile device configuration profiles scoped to a
                 mobile device group.
    package      List of all packages, or search for an individual package.
    policy       List all policies, or search for an individual policy.
    scope_diff   Show the difference between two groups' scoped policies.
    scoped       List all policies scoped to a computer group.
    batch_scope  Scope a list of policies to a group.
    promote      Promote a package from development to production by updating
                 an existing production policy with a newer package.
```

Many of these verbs require further arguments. You can view them by doing a -h on them; e.g. ```jss_helper group -h```.

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
- group (Computer groups)
- md (mobile devices)
- md_configp (mobile device configuration profiles)
- md_group (mobile device group)
- package
- policy

  These all work in much the same way-specify the verb for a list, or add an ID or name to look at details for one object.

## The Magic; Advanced Features
There are a number of advanced verbs which I wrote to help me with managing and auditing our JSS's objects and configurations.

- ```installs``` lists all policies which install a provided package (name or ID).
- ```scoped``` and ```md_scoped``` give you the ability to see all of the policies or configuration profiles scoped to a group. _Note_: This does not include anything scoped to "All Computers"
	- Example: ```jss_helper scoped "Testing Group"```
- ```scope_diff``` and ```md_scope_diff``` compare the policies scoped to two different groups, using ```diff``` to display the differences.
- ```batch_scope``` allows you to scope a number of policies to a group.
	- Example: ```jss_helper batch_scope "Testing Group" 52 100 242 40 6273```
- ```promote``` allows you to update a package installation policy with a newer version.
	- With no arguments will prompt you to select a policy and package. The interactive menu will initially show you policies which have newer packages available, and packages which match the existing package name. Selecting "F" from the menu gives you the full list of policies or packages. See the [Package Info](#package-info) section below for more details on proper naming conventions.
	- Given a policy (name or ID) and a package (ID or name), will swap the old package for the new in that policy.
    - The optional argument ```-u/--update_name``` allows you to also update the name, by replacing the package name and the package version if found in the policy name. A policy named "Install Goat Simulator-1.2.0" would get changed to "Install Goat Simulator-1.3.1". See the [Package Info](#package-info) section for further details on naming.

## Package Info

## Issues, Upcoming Features
- ```policy_by_group``` can't search for "all computers". (Will add soon!)
- Installer package!
