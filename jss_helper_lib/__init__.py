#!/usr/local/autopkg/python
# Copyright (C) 2014, 2015 Shea G Craig <shea.craig@da.org>
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


"""jss_helper_lib

JSS actions and helper functions for jss_helper.
"""

from __future__ import absolute_import
import os
import sys

if os.path.isdir('/Library/AutoPkg/JSSImporter'):
    sys.path.insert(0, '/Library/AutoPkg/JSSImporter')
    import jss
else:
    raise Exception('python-jss is not installed!')

from . import actions
from .jss_connection import JSSConnection
from . import tools


__version__ = "2.2.0b2"
