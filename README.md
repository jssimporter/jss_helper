jss-helper Introduction:
=================

jss-helper gives you a commandline interface to some features of the Jamf JSS API.

Installation:
=================

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

Setup:
=================

You need to create a preferences file to specify the address of your JSS, and credentials.

To do so, issue the following commands:
```
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_user <username>
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_pass <password>
defaults write ~/Library/Preferences/com.github.sheagcraig.python-jss.plist jss_url <url>
```

_NOTE_: ```jss_helper``` doesn't use SSL verification by default. If you need or want this, include the ```--ssl``` option to ```jss_helper```.

This may or may not work depending on a number of factors, including your python version, and related SSL packages. See [python-jss](https://www.github.com/sheagcraig/python-jss) documentation for details on making SSL verification work, including with SNI.

Basic Usage:
=================

To see a list of verbs, try: ```jss_helper.py -h```
```
usage: jss_helper [-h] [-v]
                  {category,group_policy_diff,group,package,policy_by_group,md,computer,md_configp_diff,md_configp,policy,md_group,md_configp_by_group,batch_scope,promote}
                  ...

Query the JSS.

positional arguments:
  {category,group_policy_diff,group,package,policy_by_group,md,computer,md_configp_diff,md_configp,policy,md_group,md_configp_by_group,batch_scope,promote}
    category            Get a list of all categories' names and IDs.
    group_policy_diff   Lists all policies scoped to two provided groups,
                        highlighting the differences.
    group               Get a list of all computer groups, or an individual
                        group.
    package             Get a list of all packages' names and IDs, or the
                        package XML.
    policy_by_group     Lists all policies scoped to provided group.
    md                  Get a list of mobile devices, or find one by ID.
    computer            Get a list of all computers, or an individual
                        computer.
    md_configp_diff     Lists the differences between all mobile configuration
                        profiles scoped to the provided groups.
    md_configp          Get a list of mobile device configuration profiles, or
                        find one by ID,
    policy              Get a list of all policies' names and IDs, or the
                        policy XML.
    md_group            Get a list of mobile device groups, or find one by ID.
    md_configp_by_group
                        Lists all mobile configuration profiles scoped to
                        provided group.
    batch_scope         Scope a list of policies to a group.
    promote             Promote a package from development to production by
                        updating an existing production policy with a newer
                        package.

optional arguments:
  -h, --help            show this help message and exit
  -v                    Verbose output.
```

Many of these verbs, the "positional arguments", have sub-options. You can view them by doing a -h on them; e.g. ```jss_helper group -h```.

Querying For Objects:
=================

Many of jss_helper's verbs do list or detail lookups on a JSS object type. For example,
```
jss_helper group
```
returns a list of all of the groups on the server.

To look at the details for a group, provide the ID of that group like so:
```
jss_helper group --id 42
```
Currently supported objects (which will expand as I develop further):
  - category
  - group
  - package
  - md (mobile devices)
  - md_configp (mobile device configuration profiles)
  - computer
  - policy
  - md_group (mobile device group)

  These all work in much the same way-specify the verb for a list, add an ```--id``` to look at details for one object.


The Magic; Advanced Features:
=================

There are a number of advanced verbs which I wrote to help me with auditing our JSS's objects and configurations.

  - ```policy_by_group``` and ```md_configp_by_group``` give you the ability to see all of the policies or configuration profiles scoped to a supplied group. _Note_: This does not include anything scoped to "All Computers"
    - Example: ```jss_helper policy_by_group "Testing Group"```
  - ```group_policy_diff``` and ```md_configp_diff``` compares the policies scoped to two different groups, using ```diff``` to display the differences.
  - ```batch_scope``` allows you to scope a number of policies (identified by ID) to a group (identified by name).
    - Example: ```jss_helper batch_scope "Testing Group" 52 100 242 40 6273```
  - ```promote```, given two package ID's and a policy ID, will swap the old package for the new in that policy.
    - The optional argument ```--update-version-in-name``` allows you to also update the name. At the moment, this is very specific to my organization, where policies that install software end with a hyphen, and then the version number, and the packages do the same. So, if used, a policy named "Install Goat Simulator-1.2.0" would get changed to "Install Goat Simulator-1.3.1".

Issues, Upcoming Features
=================
  - Need to add ability to use name OR ID for all verbs. Currently inconsistent
  - promotion policy renaming is limited to my organization.
  - ```policy_by_group``` can't search for "all computers". (Will add soon!)
