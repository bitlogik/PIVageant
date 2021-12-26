#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pageant SSH agent window gateway for PIVageant
# Copyright (C) 2021  BitLogiK
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

import mmap
import platform
from secrets import randbits
from ctypes import (
    WinDLL,
    windll,
    wintypes,
    WinError,
    get_last_error,
    c_void_p,
    c_byte,
    c_uint32,
    c_uint64,
    c_int,
    c_int64,
    Structure,
    WINFUNCTYPE,
    POINTER,
    byref,
    memmove,
    cast,
)


def errcheck(result, func, args):
    if result is None or result == 0:
        raise WinError(get_last_error())
    return result


LRESULT = c_int64
HCURSOR = c_void_p
WNDPROC = WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)
ULONG_PTR = c_uint64 if platform.architecture()[0] == "64bit" else c_uint32


def MAKEINTRESOURCEW(xi32):
    return wintypes.LPCWSTR(xi32)


class COPYDATASTRUCT(Structure):
    _fields_ = [
        ("dwData", ULONG_PTR),
        ("cbData", wintypes.DWORD),
        ("lpData", c_void_p),
    ]


class WNDCLASSW(Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class PAINTSTRUCT(Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", wintypes.BYTE * 32),
    ]


kernel32 = WinDLL("kernel32", use_last_error=True)
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.errcheck = errcheck

user32 = WinDLL("user32", use_last_error=True)
user32.CreateWindowExW.argtypes = (
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    c_int,
    c_int,
    c_int,
    c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
)
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.errcheck = errcheck
user32.LoadIconW.argtypes = wintypes.HINSTANCE, wintypes.LPCWSTR
user32.LoadIconW.restype = wintypes.HICON
user32.LoadIconW.errcheck = errcheck
user32.LoadCursorW.argtypes = wintypes.HINSTANCE, wintypes.LPCWSTR
user32.LoadCursorW.restype = HCURSOR
user32.LoadCursorW.errcheck = errcheck
user32.RegisterClassW.argtypes = (POINTER(WNDCLASSW),)
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.errcheck = errcheck
user32.ShowWindow.argtypes = wintypes.HWND, c_int
user32.ShowWindow.restype = wintypes.BOOL
user32.UpdateWindow.argtypes = (wintypes.HWND,)
user32.UpdateWindow.restype = wintypes.BOOL
user32.UpdateWindow.errcheck = errcheck
user32.GetMessageW.argtypes = (
    POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
)
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = (POINTER(wintypes.MSG),)
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = (POINTER(wintypes.MSG),)
user32.DispatchMessageW.restype = LRESULT
user32.BeginPaint.argtypes = wintypes.HWND, POINTER(PAINTSTRUCT)
user32.BeginPaint.restype = wintypes.HDC
user32.BeginPaint.errcheck = errcheck
user32.GetClientRect.argtypes = wintypes.HWND, POINTER(wintypes.RECT)
user32.GetClientRect.restype = wintypes.BOOL
user32.GetClientRect.errcheck = errcheck
user32.DrawTextW.argtypes = (
    wintypes.HDC,
    wintypes.LPCWSTR,
    c_int,
    POINTER(wintypes.RECT),
    wintypes.UINT,
)
user32.DrawTextW.restype = c_int
user32.EndPaint.argtypes = wintypes.HWND, POINTER(PAINTSTRUCT)
user32.EndPaint.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = (c_int,)
user32.PostQuitMessage.restype = None
user32.DefWindowProcW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
user32.DefWindowProcW.restype = LRESULT

CW_USEDEFAULT = -2147483648
IDI_APPLICATION = MAKEINTRESOURCEW(32512)
WS_CHILD = 0x40000000
WS_OVERLAPPEDWINDOW = 13565952

CS_HREDRAW = 2
CS_VREDRAW = 1

IDC_ARROW = MAKEINTRESOURCEW(32512)
WHITE_BRUSH = 0

SW_SHOWNORMAL = 1
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_SHOWMINIMIZED = 2
SW_RESTORE = 9

WM_PAINT = 15
WM_DESTROY = 2
WM_COPYDATA = 74
DT_SINGLELINE = 32
DT_CENTER = 1
DT_VCENTER = 4

AGENT_DATATYPE = 0x804E50BA
CLOSE_MAGIC = randbits(31)
class_id = 0


def MainWin(callback):

    class_name = "Pageant"

    def CustomWndProc(hwnd, message, wParam, lParam):
        global class_id
        if message == WM_COPYDATA:
            # Entry point from the SSH client
            handle_wmcopy(lParam, hwnd, callback)
            return 0
        elif message == WM_DESTROY:
            if wParam == CLOSE_MAGIC:
                ret = user32.DestroyWindow(hwnd)
                if ret == 0:
                    raise WinError(get_last_error())
                ret = user32.UnregisterClassW(class_name, class_id)
                if ret == 0:
                    raise WinError(get_last_error())
                user32.PostQuitMessage(0)
                return wParam
        return user32.DefWindowProcW(hwnd, message, wParam, lParam)

    wndclass = WNDCLASSW()
    wndclass.style = CS_HREDRAW | CS_VREDRAW
    wndclass.lpfnWndProc = WNDPROC(CustomWndProc)
    wndclass.cbClsExtra = wndclass.cbWndExtra = 0
    wndclass.hInstance = kernel32.GetModuleHandleW(None)
    wndclass.hIcon = user32.LoadIconW(None, IDI_APPLICATION)
    wndclass.hCursor = user32.LoadCursorW(None, IDC_ARROW)
    wndclass.lpszMenuName = None
    wndclass.lpszClassName = class_name

    # Register Window Class
    class_id = user32.RegisterClassW(byref(wndclass))

    # Create Window
    user32.CreateWindowExW(
        0,
        wndclass.lpszClassName,
        "Pageant",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        250,
        120,
        None,
        None,
        wndclass.hInstance,
        None,
    )
    # Pump Messages
    msg = wintypes.MSG()
    while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(byref(msg))
        user32.DispatchMessageW(byref(msg))

    return msg.wParam


def handle_wmcopy(wmcp_adr, hwmn, handle_command):
    # process WM_COPYDATA message
    # from a pointer address to a COPYDATASTRUCT
    msg_copy_ptr = cast(wmcp_adr, POINTER(COPYDATASTRUCT))
    msg_copy = msg_copy_ptr.contents
    if msg_copy.dwData == AGENT_DATATYPE:
        # Client agent WM_COPYDATA received
        # Read data in the message, contains mmap name
        buf = bytearray(msg_copy.cbData)
        cbuf = (c_byte * msg_copy.cbData).from_buffer(buf)
        # Copy data into cbuf
        memmove(cbuf, msg_copy.lpData, msg_copy.cbData)
        mmap_name = buf[: msg_copy.cbData - 1].decode("utf8")
        # Connect to the given mmap
        conn_mmap = mmap.mmap(-1, 8192, tagname=mmap_name, access=mmap.ACCESS_WRITE)
        # Now read the mmap
        conn_mmap.seek(0)
        datalen = conn_mmap.read(4)
        retlen = int.from_bytes(datalen, "big")
        if retlen > 8192:
            raise Exception("Too many data received")
        cmd_rcvd = conn_mmap.read(retlen)
        resp = handle_command(cmd_rcvd)
        # Reply to the SSH client
        conn_mmap.seek(0)
        conn_mmap.write(resp)
        user32.ReplyMessage(len(resp))


def get_window_id():
    return windll.user32.FindWindowA(b"Pageant", b"Pageant")


def close_window(winid):
    windll.user32.SendMessageA(winid, WM_DESTROY, CLOSE_MAGIC, 0)
