import wx.adv


class PIVagTray(wx.adv.TaskBarIcon):
    def __init__(self, frame, icon_path):
        self.frame = frame
        super(PIVagTray, self).__init__()
        self.SetIcon(wx.Icon(icon_path), "PIVagent")
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.OnTaskBarClick)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_UP, self.OnTaskBarClick)

    def OnTaskBarActivate(self, evt):
        pass

    def OnTaskBarClick(self, evt):
        self.frame.Show()
        self.frame.Restore()
        self.frame.Raise()
