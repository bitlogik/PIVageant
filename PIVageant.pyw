#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PIVageant
# a Pageant SSH agent with PIV dongle Yubico 5
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


from functools import partial
import ctypes
import os
import sys
import wx
import wx.lib.newevent
import mainwin
import pageant_win
import pageantclient
from _version import __version__
from getwin import check_pageant_running
from systemtray import PIVagTray
from piv_card import PIVCardException, PIVCardTimeoutException

KEY_NAME = "yub384"


def is_tty():
    if not hasattr(sys, "stdin"):
        return False
    if not hasattr(sys.stdin, "isatty"):
        return False
    return sys.stdin.isatty()


DEBUG_OUTPUT = is_tty()


class ModalWait(mainwin.ModalDialog):
    def end_sign(self, event):
        if event:
            event.Skip()
        self.Destroy()


class PIVageantwin(mainwin.PIVageant):
    def copy_content(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.pubkey_text.GetValue()))
            wx.TheClipboard.Close()
            wx.TheClipboard.Flush()

    def go_start(self, ssh_pubkey):
        self.print_pubkey(ssh_pubkey)
        process_cb = partial(
            pageantclient.process_command,
            DEBUG_OUTPUT,
            pageantclient.openssh_to_wire(ssh_pubkey),
            self.sign_status,
            self.end_status,
        )
        self.change_status("Key read, closing to tray")
        self.cpy_btn.Enable()
        wx.CallAfter(pageant_win.MainWin, pageant_win.gen_cb(process_cb))

    def change_status(self, text_status):
        self.status_text.SetLabelText(text_status)

    def sign_status(self, user):
        self.change_status("Signature requested")
        self.sign_alert = ModalWait(self)
        self.sign_alert.username_txt.SetLabel(user)
        self.sign_alert.Restore()
        self.sign_alert.Show(True)
        self.sign_alert.gauge_wait.Pulse()
        self.sign_alert.Refresh()
        self.sign_alert.Update()
        wx.MilliSleep(250)

    def end_status(self, data_text):
        self.change_status(data_text)
        # save main windows status for selective hide
        is_disp = self.IsShownOnScreen()
        if not is_disp:
            self.Lower()
            self.SetTransparent(0)
        self.Show(True)
        self.sign_alert.Destroy()
        if not is_disp:
            self.Hide()
            self.SetTransparent(255)
        wx.CallLater(3500, self.change_status, "Ready")

    def print_pubkey(self, pubkey_value):
        self.pubkey_text.SetValue(pubkey_value)

    def get_event(self, event):
        # Process PIVkey events
        if event.type == "Connected":
            self.go_start(event.data)
            wx.CallLater(3500, self.change_status, "Ready")
            wx.CallLater(850, self.sendtray, None)
            return
        if event.type == "Timeout":
            waiting_for_pivkey(self)
            return
        if event.type == "Error":
            self.change_status(event.data)
            return

    def sendtray(self, _):
        wx.CallLater(400, self.Hide)

    def closing(self, event):
        agent_win_id = pageant_win.get_window_id()
        if agent_win_id != 0:
            pageant_win.close_window(agent_win_id)
        if hasattr(event, "Skip"):
            event.Skip()
        self.trayicon.RemoveIcon()
        self.trayicon.Destroy()

    def get_pubkey(self):
        try:
            piv_ssh_public_key = pageantclient.read_pubkey(KEY_NAME, 0.1)
            self.change_status("PIV key detected")
            wx.PostEvent(self, PivKeyEvent(type="Connected", data=piv_ssh_public_key))
        except PIVCardTimeoutException:
            wx.PostEvent(self, PivKeyEvent(type="Timeout"))
        except PIVCardException as exc:
            err_msg = str(exc)
            if err_msg == "Error status : 0x6A82":
                wx.PostEvent(
                    self, PivKeyEvent(type="Error", data="No key found, run Gen-keys")
                )
            else:
                wx.PostEvent(
                    self, PivKeyEvent(type="Error", data="Unknown error: " + err_msg)
                )


def waiting_for_pivkey(curr_frame):
    wx.CallLater(250, curr_frame.get_pubkey)


def get_path(fpath):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, fpath)
    return fpath


PivKeyEvent, EVT_PIVKEY_EVENT = wx.lib.newevent.NewEvent()
# PIVKEY_EVENT Attribute type :
# "Timeout" (no key connected yey)
# "Connected"
# "Error"
# "Signed"
# Attribute data :
# for type Error : error message
# for type Connected : public_key


def mainapp():
    app = wx.App()
    ctypes.windll.shcore.SetProcessDpiAwareness(True)

    # Check if a Pageant is running
    if check_pageant_running():
        wx.MessageBox(
            "A Pageant process is already running.",
            "PIVageant info",
            wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP,
        )
        return

    app.main_frame = PIVageantwin(None)
    app.main_frame.SetTitle(f"PIVageant  -  {__version__}")
    icon_file = get_path("res\\pivageant.ico")
    app.main_frame.SetIcons(wx.IconBundle(icon_file))
    app.main_frame.Show()
    app.main_frame.Bind(wx.EVT_CLOSE, app.main_frame.closing)
    app.main_frame.Bind(wx.EVT_ICONIZE, app.main_frame.sendtray)
    app.main_frame.Bind(EVT_PIVKEY_EVENT, app.main_frame.get_event)
    app.main_frame.trayicon = PIVagTray(app.main_frame, icon_file)

    app.main_frame.Update()
    waiting_for_pivkey(app.main_frame)

    app.MainLoop()


if __name__ == "__main__":
    mainapp()
