#!/usr/local/autopkg/python
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


"""jssconnection.py

Class for managing a JSS connection.
"""

from __future__ import absolute_import

import os.path
import sys

if os.path.isdir('/Library/AutoPkg/JSSImporter'):
    sys.path.insert(0, '/Library/AutoPkg/JSSImporter')
    import jss
else:
    raise Exception('python-jss is not installed!')


class JSSConnection(object):
    """Class for providing a single JSS connection."""
    _jss_prefs = None
    _jss = None

    @classmethod
    def setup(cls, connection=None):
        """Set up the JSSConnection class variable.

        Each client that imports jss_connection.JSSConnection has its
        own class variables. This function will configure properties on
        the current namespace's JSSConnection prior to use.

        Args:
            connection: Dictionary with JSS connection info, keys:
                jss_prefs: String path to a preference file.
                url: Path with port to a JSS.
                user: API Username.
                password: API Password.
                repo_prefs: A list of dicts with repository names and
                    passwords. See JSSPrefs.
                ssl_verify: Boolean indicating whether to verify SSL
                    certificates.  Defaults to True.
                verbose: Boolean indicating the level of logging.
                    (Doesn't do much.)
        """
        # cls._jss_prefs = jss.JSSPrefs()
        # cls._jss = jss.JSS(jss_prefs=cls._jss_prefs)

        if not connection:
            connection = {"jss_prefs": jss.JSSPrefs()}
        cls._jss_prefs = connection
        if isinstance(connection, jss.JSSPrefs):
            cls._jss = jss.JSS(jss_prefs=cls._jss_prefs)
        else:
            cls._jss = jss.JSS(**cls._jss_prefs)

        # if args:
        #     args_dict = vars(args)
        #     if "nossl" in args_dict:
        #         ssl = not args.nossl
        #         cls._jss.session.verify = ssl
        #     if "verbose" in args_dict:
        #         cls._jss.verbose = args.verbose



    @classmethod
    def get(cls):
        """Return the shared JSS object."""
        if not cls._jss:
            cls.setup()
        return cls._jss
