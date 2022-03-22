# -*- coding: utf-8 -*-

# PIVageant : Seek Windows class and name
# Copyright (C) 2021-2022  BitLogiK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import ctypes
from ctypes.wintypes import PBYTE


def get_classname_from_title(title):
    # Return the name of the class of the first windows with the given title
    # First get the window with the title
    found_win = ctypes.windll.user32.FindWindowA(None, title)
    # Now reads its class name
    class_name_maxsz = 1024
    class_name = (ctypes.c_ubyte * class_name_maxsz)()
    class_name_ptr = ctypes.cast(ctypes.pointer(class_name), PBYTE)
    class_name_sz = ctypes.windll.user32.GetClassNameA(
        found_win, class_name_ptr, class_name_maxsz
    )
    return bytes([*class_name[:class_name_sz]])


PAGEANT_CLASSTITLE = b"Pageant"


def check_pageant_running():
    # Check if there's a windows with title and class name = Pageant
    return PAGEANT_CLASSTITLE == get_classname_from_title(PAGEANT_CLASSTITLE)
