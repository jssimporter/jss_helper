# jss_helper Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased][unreleased]

### Added

- Added action `configp` for OSX Configuration Profiles.
- `scoped` now includes OSXConfigurationProfile objects. (#4). Thanks to @homebysix for the great idea!
- `scope_diff` now also include profiles.
- Added action `imaging_config`.
- `installs` now includes imaging configurations (`ComputerConfiguration`) (#3) Thanks again to @homebysix for the idea.
- Added action `excluded` for showing policies and profiles from which a group is excluded. (#5) (@homebysix again!)
- Added action `md_excluded` for showing profiles from which a mobile device group is excluded.
- Most actions that take a search argument will now accept Unix-shell style wildcard characters for matching. These search arguments *MUST* be single-quote escaped in Bash to avoid shell wildcard-expansion; e.g.: `jss_helper installs 'Firefox*'`.
	- Actions incorporating wildcard searches:
		- All object search functions (`computer`, `policy`, etc)
		- `installs`
		- `group` `--add/--remove` optional arguments.
- Added `--add`, `--remove`, and `--dry-run` options to `group`. You can now add and remove any number of computers, specified by name, wildcard-name-search, or ID. If you specify `--dry-run` it doesn't save; it just prints the group XML.

### Changed

- More gracefully handles a CTRL-C exit from the menus.
- `promote` now opens your default browser to the log page for policy if needed.
- Output headers now make more sense.
- Commands which search for scoped objects now include results scoped to "all computers" or "all mobile devices" in their results, labeled as such.
	- `scoped`
	- `md_scoped`
	- `scope_diff`
	- `md_scope_diff`

## [2.0.0] - 2015-05-28 - Deep Fried Codpiece
This release changes the names of verbs and simplifies the arguments for running them. Therefore, there has been a major version increment!

### Added

- Added a policy_with_package command.
- Now versioned...
- Added some tests for `get_package_info` to make sure it handles all "valid" LooseVersion types.

### Changed

- Improved output formatting.
- Renamed many of the commands and arguments to make more sense.
- Restructured and Refactored for elegance.
- Every command should now accept name or ID for arguments.
- Actions that previously took an "--id" argument no longer need the "--id".
	- e.g. `jss_helper policy "Install Nethack"`
- `promote` changes:
	- Now allows for interactively selecting arguments.
	- Initially only shows policies which have package updates available ("F" allows you to see all install-policies).
	- Tries to guess which packages you may want to install (by regex searching for similar package names). You can still see a full list with the interactive "F" command.
	-  Uses a "-" or a " " (blank space) as delimeters in the policy name for `--update-name` purposes.
	- Drops the `old-package` argument. It was used as a safeguard, but I no longer think that it's needed. If you're running with the ID's, you know what you're doing, and if you're running interactively, you've visually confirmed what you want.
	- Now reminds you to flush the policy logs for non-ongoing policies.
	- Package options now sorted by product, then by version correctly.
	- Package names and versions are more accurately determined (see README about Package Info).

## 1.0 - 2014-08-14 - Blaster Master

- Initial Release

[unreleased]: https://github.com/sheagcraig/jss_helper/compare/2.0.0...HEAD
[2.0.0]: https://github.com/sheagcraig/jss_helper/compare/v1.0...2.0.0
