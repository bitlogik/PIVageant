#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PIVageant
# a Windows Pageant SSH agent with PIV dongle
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
from ctypes import windll
import os
import sys
import wx
import wx.lib.newevent
import lib.gui.mainwin
import lib.gui.pageant_win
from lib.gui.getwin import check_pageant_running
from lib.gui.systemtray import PIVagTray
from lib.piv.piv_card import (
    PIVCardException,
    PIVCardTimeoutException,
    ConnectionException,
)
from lib.piv.genkeys import generate_key
from lib.ssh.ssh_encodings import openssh_to_wire
from lib.pageantclient import process_command, read_pubkey
from _version import __version__

KEY_NAME = "ECPSSHKey"


def is_tty():
    if not hasattr(sys, "stdin"):
        return False
    if not hasattr(sys.stdin, "isatty"):
        return False
    return sys.stdin.isatty()


DEBUG_OUTPUT = False


class ModalWait(lib.gui.mainwin.ModalDialog):
    def end_sign(self, event):
        if event:
            event.Skip()
        self.Destroy()


class PIVageantwin(lib.gui.mainwin.PIVageant):
    def copy_content(self, evt):
        if wx.TheClipboard.Open():
            pubkey_txt = self.pubkey_text.GetValue().replace("\n", "")
            if pubkey_txt.startswith("ecdsa-"):
                pubkey_str = wx.TextDataObject(pubkey_txt)
                wx.TheClipboard.SetData(pubkey_str)
                wx.TheClipboard.Close()
                wx.TheClipboard.Flush()
                self.change_status("Public key in clipboard")
                wx.CallLater(800, self.change_status, "Ready")

    def gen_key(self, evt):
        evt.Skip()
        confirm_modal = wx.MessageDialog(
            self,
            "A new key generation can erase any current key in the dongle.\nConfirm key creation ?",
            caption="Confirm key generation",
            style=wx.YES | wx.NO | wx.CENTRE,
            pos=wx.DefaultPosition,
        )
        confirm_modal.SetYesNoLabels("Proceed", "cancel")
        if confirm_modal.ShowModal() == wx.ID_YES:
            self.change_status("Key generation ...")
            self.print_pubkey("")
            generate_key(DEBUG_OUTPUT)
            self.waiting_for_pivkey()

    def go_start(self, ssh_pubkey):
        self.print_pubkey(ssh_pubkey)
        process_cb = partial(
            process_command,
            DEBUG_OUTPUT,
            openssh_to_wire(ssh_pubkey),
            self.sign_status,
            self.end_status,
        )
        self.change_status("Key read, closing to tray")
        self.cpy_btn.Enable()
        close_agentwindow()
        wx.CallLater(500, lib.gui.pageant_win.MainWin, process_cb)

    def change_status(self, text_status):
        self.status_text.SetLabelText(text_status)

    def sign_status(self, user, card_info):
        self.change_status("Signature requested")
        self.sign_alert = ModalWait(self)
        if not card_info["isYubico"]:
            self.sign_alert.static_text_modal.SetLabel("Signing with the PIV dongle")
        self.sign_alert.username_txt.SetLabel(f"as user : {user}")
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
            self.waiting_for_pivkey()
            return
        if event.type == "Error":
            self.change_status(event.data)
            return

    def sendtray(self, _):
        wx.CallLater(400, self.Hide)

    def closing(self, event):
        close_agentwindow()
        if hasattr(event, "Skip"):
            event.Skip()
        self.trayicon.RemoveIcon()
        self.trayicon.Destroy()

    def waiting_for_pivkey(self):
        wx.CallLater(500, self.get_pubkey)

    def get_pubkey(self):
        try:
            piv_ssh_public_key = read_pubkey(KEY_NAME, 0.1, DEBUG_OUTPUT)
            self.change_status("PIV key detected")
            self.gen_btn.Enable()
            wx.PostEvent(self, PivKeyEvent(type="Connected", data=piv_ssh_public_key))
        except PIVCardTimeoutException:
            wx.PostEvent(self, PivKeyEvent(type="Timeout"))
        except PIVCardException as exc:
            err_msg = str(exc)
            if err_msg == "Error status : 0x6A82":
                self.gen_btn.Enable()
                wx.PostEvent(
                    self, PivKeyEvent(type="Error", data="No key found, generate a key")
                )
            else:
                wx.PostEvent(self, PivKeyEvent(type="Error", data="Error: " + err_msg))
        except ConnectionException as exc:
            wx.PostEvent(self, PivKeyEvent(type="Error", data=str(exc)))


def close_agentwindow():
    agent_win_id = lib.gui.pageant_win.get_window_id()
    if agent_win_id != 0:
        lib.gui.pageant_win.close_window(agent_win_id)


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
    windll.shcore.SetProcessDpiAwareness(2)

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
    app.main_frame.waiting_for_pivkey()

    app.MainLoop()


if __name__ == "__main__":
    if "-v" in sys.argv[1:]:
        DEBUG_OUTPUT = is_tty()
    mainapp()
