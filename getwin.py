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
