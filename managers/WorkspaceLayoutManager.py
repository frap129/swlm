"""
Copyright 2022 Joe Maples <joe@maples.dev>

This file is part of swlm.

swlm is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

swlm is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
swlm. If not, see <https://www.gnu.org/licenses/>. 
"""

class WorkspaceLayoutManager:
    overridesMoveBinds = False

    def __init__(self, con, workspace, options):
        self.con = con
        self.workspaceId = workspace.ipc_data["id"]
        self.workspaceNum = workspace.num
        self.debug = options.debug


    def log(self, msg):
        if self.debug:
            print(("workspace %d: %s: " % (self.workspaceNum, self.__class__.__name__)) + msg)


    def windowCreated(self, event):
        pass


    def windowFocused(self, event):
        pass


    def windowClosed(self, event):
        pass


    def windowMoved(self, event):
        pass


    def binding(self, command):
        pass
