# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class PIVageant
###########################################################################

class PIVageant ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( 581,318 ), style = wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer3 = wx.BoxSizer( wx.VERTICAL )

        self.main_panel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizer1 = wx.BoxSizer( wx.VERTICAL )

        self.pubkey_text = wx.TextCtrl( self.main_panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_CHARWRAP|wx.TE_MULTILINE|wx.TE_NO_VSCROLL|wx.TE_READONLY )
        bSizer1.Add( self.pubkey_text, 1, wx.ALL|wx.EXPAND, 20 )

        self.cpy_btn = wx.Button( self.main_panel, wx.ID_ANY, u"copy", wx.DefaultPosition, wx.Size( -1,45 ), 0 )
        self.cpy_btn.SetFont( wx.Font( 14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.cpy_btn.Enable( False )

        bSizer1.Add( self.cpy_btn, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 3 )


        bSizer1.Add( ( 0, 12), 0, 0, 5 )

        self.status_text = wx.StaticText( self.main_panel, wx.ID_ANY, u"Connect a Yubico 5", wx.DefaultPosition, wx.Size( 400,-1 ), wx.ALIGN_CENTER_HORIZONTAL|wx.ST_NO_AUTORESIZE )
        self.status_text.Wrap( -1 )

        self.status_text.SetFont( wx.Font( 16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        bSizer1.Add( self.status_text, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5 )


        bSizer1.Add( ( 0, 12), 0, 0, 5 )


        self.main_panel.SetSizer( bSizer1 )
        self.main_panel.Layout()
        bSizer1.Fit( self.main_panel )
        bSizer3.Add( self.main_panel, 1, wx.EXPAND |wx.ALL, 0 )


        self.SetSizer( bSizer3 )
        self.Layout()

        self.Centre( wx.BOTH )

        # Connect Events
        self.cpy_btn.Bind( wx.EVT_BUTTON, self.copy_content )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def copy_content( self, event ):
        event.Skip()


###########################################################################
## Class ModalDialog
###########################################################################

class ModalDialog ( wx.Dialog ):

    def __init__( self, parent ):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Signature requested", pos = wx.DefaultPosition, size = wx.Size( 482,172 ), style = wx.CAPTION|wx.STAY_ON_TOP )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer2 = wx.BoxSizer( wx.VERTICAL )

        self.static_text_modal = wx.StaticText( self, wx.ID_ANY, u"Touch the button to sign as user", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.static_text_modal.Wrap( -1 )

        bSizer2.Add( self.static_text_modal, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5 )

        self.username_txt = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.username_txt.Wrap( -1 )

        bSizer2.Add( self.username_txt, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5 )


        bSizer2.Add( ( 0, 12), 1, wx.EXPAND, 5 )

        self.gauge_wait = wx.Gauge( self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL )
        self.gauge_wait.SetValue( 0 )
        bSizer2.Add( self.gauge_wait, 0, wx.ALL|wx.EXPAND, 5 )


        bSizer2.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.cancel_btn = wx.Button( self, wx.ID_ANY, u"cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer2.Add( self.cancel_btn, 0, wx.ALL|wx.ALIGN_RIGHT, 5 )


        self.SetSizer( bSizer2 )
        self.Layout()

        self.Centre( wx.BOTH )

        # Connect Events
        self.cancel_btn.Bind( wx.EVT_BUTTON, self.cancel_sign )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def cancel_sign( self, event ):
        event.Skip()


