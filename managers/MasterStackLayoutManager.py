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
from collections import deque

from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
import utils

class MasterStackLayoutManager(WorkspaceLayoutManager):
    def __init__(self, con, workspace, options):
        self.con = con
        self.workspaceId = workspace.ipc_data["id"]
        self.workspaceNum = workspace.num
        self.masterId = 0
        self.stackIds = deque([])
        self.debug = options.debug
        self.masterWidth = options.masterWidth
        self.stackLayout = options.stackLayout

        # Handle window if it's not currently being tracked
        self.arrangeExistingLayout(utils.findFocused(self.con))


    def arrangeExistingLayout(self, window):
        if (self.isExcluded(window)):
            return

        print(window.ipc_data)
        print("\n")
                
        workspace = window.workspace()
        untracked = []
        for node in workspace.nodes:
            if window.id != node.id and node.id != self.masterId and node.id not in self.stackIds:
                # Check if window should remain untracked
                if (self.isExcluded(node)):
                    continue

                print(node.ipc_data)
                print("\n")
                # Flaot it to remove it from the current layout
                self.con.command("[con_id=%s] focus" % node.id)
                self.con.command("floating toggle")
                untracked.append(node.id)
                self.log("arrangeExistingLayout: Found untracked window %d" % node.id)

        for windowId in untracked:
            if windowId != self.masterId and windowId not in self.stackIds:
                self.setStackLayout()
                # Unfloat the window, then treat it like a new window
                self.con.command("[con_id=%s] focus" % windowId)
                self.con.command("floating tooggle")
                self.pushWindow(windowId)
                self.log("arrangeExistingLayout: Pushed window %d" % windowId)

        self.setStackLayout()
        self.log("arrangeExistingLayout: masterId is %d" % self.masterId)


    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        if window.workspace() is None:
            return True

        if window.orientation is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        return False


    def setMasterWidth(self):
        if self.masterWidth is not None:
            self.con.command('[con_id=%s] resize set %s 0 ppt' % (self.masterId, self.masterWidth))
            self.log("Set window %d width to %d" % (self.masterId, self.masterWidth))


    def moveWindow(self, subject, target):
        self.con.command("[con_id=%d] mark --add move_target" % target)
        self.con.command("[con_id=%d] move container to mark move_target" % subject)
        self.con.command("[con_id=%d] unmark move_target" % target)
        self.log("Moved window %s to mark on window %s" % (subject, target))


    def pushWindow(self, subject):
        # Check if master is empty too
        if self.masterId == 0:
            self.log("pushWindow: Made window %d master" % subject)
            self.masterId = subject
            return

        # Only record window if stack is empty
        if len(self.stackIds) == 0:
            self.stackIds.append(self.masterId)
            self.con.command("[con_id=%s] swap container with con_id %s" % (subject, self.masterId))
            self.masterId = subject
            self.log("pushWindow: Initialized stack with window %d" % subject)
            self.setMasterWidth()
            return

        # Put new window at top of stack
        target = self.stackIds[-1]
        self.moveWindow(subject, target)
        self.con.command("[con_id=%s] focus" % subject)
        self.con.command("move up")

        # Swap with master
        oldMaster = self.masterId
        self.con.command("[con_id=%s] swap container with con_id %s" % (subject, oldMaster))
        self.stackIds.append(self.masterId)
        self.masterId = subject
        self.setMasterWidth()


    def popWindow(self):
        # Check if last window is being popped
        if len(self.stackIds) == 0:
            self.masterId = 0
            self.log("popWindow: Closed last window, nothing to do")
            return

        # Move top of stack to master position
        self.masterId = self.stackIds.pop()
        self.con.command("[con_id=%s] focus" % self.masterId)
        self.con.command("move left")
        self.setMasterWidth()
        self.log("popWindow: Moved top of stack to master")


    def moveUp(self):
        focusedWindow = utils.findFocused(self.con)

        if focusedWindow is None:
            self.log("moveUp: No window focused, can't move")
            return

        # Swap master and top of stack if only two windows, or focus is top of stack
        if len(self.stackIds) < 2 or focusedWindow.id == self.stackIds[-1]:
            target = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (target, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = target
            self.log("moveUp: Swapped window %d with master" % target)
            return

        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with window above
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[i+1]))
                self.stackIds[i] = self.stackIds[i+1]
                self.stackIds[i+1] = focusedWindow.id
                self.log("moveUp: Swapped window %d with %d" % (focusedWindow.id, self.stackIds[i]))
                return


    def moveDown(self):
        # Check if stack only has one window
        if len(self.stackIds) < 2:
            return

        focusedWindow = utils.findFocused(self.con)
        if focusedWindow is None:
            self.log("moveDown: No window focused, can't move")
            return

        # Check if we hit bottom of stack
        if focusedWindow == self.stackIds[0]:
            self.log("moveDown: Bottom of stack, nowhere to go")
            return

        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with window below
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[i-1]))
                self.stackIds[i] = self.stackIds[i-1]
                self.stackIds[i-1] = focusedWindow.id
                self.log("moveDown: Swapped window %d with %d" % (focusedWindow.id, self.stackIds[i]))
                return


    def rotateCCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("rotateCCW: Only 2 windows, can't rotate")
            return

        # Swap top of stack with master, then move old master to bottom
        newMaster = self.stackIds.pop()
        oldMaster = self.masterId
        bottom = self.stackIds[0]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMaster, oldMaster))
        self.log("rotateCCW: swapped top of stack with master")
        self.moveWindow(oldMaster, bottom)
        self.log("rotateCCW: Moved previous master to bottom of stack")

        # Update record
        self.masterId = newMaster
        self.stackIds.appendleft(oldMaster)


    def rotateCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("rotateCW: Only 2 windows, can't rotate")
            return

        # Swap bottom of stack with master, then move old master to top
        newMaster = self.stackIds.popleft()
        oldMaster = self.masterId
        top = self.stackIds[-1]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMaster, oldMaster))
        self.log("rotateCW: swapped bottom of stack with master")
        self.moveWindow(oldMaster, top)
        self.con.command("[con_id=%d] focus" % oldMaster)
        self.con.command("move up")
        self.con.command("[con_id=%d] focus" % newMaster)
        self.log("rotateCW: Moved previous master to top of stack")

        # Update record
        self.masterId = newMaster
        self.stackIds.append(oldMaster)


    def swapMaster(self):
        # Exit if less than two windows
        if len(self.stackIds) == 0:
            self.log("swapMaster: Stack emtpy, can't swap")
            return
            
        focusedWindow = utils.findFocused(self.con)

        if focusedWindow is None:
            self.log("swapMaster: No window focused, can't swap")
            return

        # If focus is master, swap with top of stack
        if focusedWindow.id == self.masterId:
            target = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (target, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = target
            self.log("swapMaster: Swapped master with top of stack")
            return

        # Find focused window in record
        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.masterId))
                self.stackIds[i] = self.masterId
                self.masterId = focusedWindow.id
                self.log("swapMaster: Swapped master with window %d" % focusedWindow.id)
                return


    def setStackLayout(self):
        # splith is not supported yet. idk how to differentiate between splith and nested splith.
        if len(self.stackIds) != 0:
            layout = self.stackLayout or "splitv"
            bottom = self.stackIds[0]
            self.con.command("[con_id=%d] split vertical" % bottom)
            self.con.command("[con_id=%d] layout %s" % (bottom, layout))
        else:
            self.con.command("[con_id=%d] split horizontal" % self.masterId)
            self.con.command("[con_id=%d] layout %s" % (self.masterId, "splith"))



    def windowCreated(self, event):
        newWindow = utils.findFocused(self.con)

        # Ignore excluded windows
        if self.isExcluded(newWindow):
            return
        
        # New window replcases master, master gets pushed to stack
        self.log("New window id: %d" % newWindow.id)
        self.pushWindow(newWindow.id)


    def windowFocused(self, event):
        focusedWindow = utils.findFocused(self.con)
        # Ignore excluded windows
        if self.isExcluded(focusedWindow):
            return

        self.setStackLayout()

        # Handle window if it's not currently being tracked
        if self.masterId != focusedWindow.id and focusedWindow.id not in self.stackIds:
            self.pushWindow(focusedWindow.id)
            self.log("windowMoved: Pushed untracked window %d" % focusedWindow.id)
            return


    def windowMoved(self, event):
        focusedWindow = utils.findFocused(self.con)
        # Ignore excluded windows
        if self.isExcluded(focusedWindow):
            return

        # Handle window if it's not currently being tracked
        if self.masterId != focusedWindow.id and focusedWindow.id not in self.stackIds:
            self.pushWindow(focusedWindow.id)
            self.log("windowMoved: Pushed untracked window %d" % focusedWindow.id)
            return


    def windowClosed(self, event):
        self.log("Closed window id: %d" % event.container.id)

        if self.masterId == event.container.id:
            # If window is master, pop the next one off the stack
            self.popWindow()
        else:
            # If window is not master, remove from stack and exist
            try:
                self.stackIds.remove(event.container.id)
            except BaseException as e:
                # This should only happen if an untracked window was closed
                self.log("windowClosed: WTF: window not master or in stack")


    def binding(self, command):
        if command == "nop swlm move up":
            self.moveUp()
        elif command == "nop swlm move down":
            self.moveDown()
        elif command == "nop swlm rotate ccw":
            self.rotateCCW()
        elif command == "nop swlm rotate cw":
            self.rotateCW()
        elif command == "nop swlm swap master":
            self.swapMaster()
