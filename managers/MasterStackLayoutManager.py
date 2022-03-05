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
    shortName = "MasterStack"
    overridesMoveBinds = True

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
        self.arrangeExistingLayout()

    def windowAdded(self, event):
        newWindow = utils.findFocused(self.con)

        # Ignore excluded windows
        if self.isExcluded(newWindow):
            return
        
        # New window replaces master, master gets pushed to stack
        self.log("Added window id: %d" % newWindow.id)
        self.pushWindow(newWindow.id)


    def windowRemoved(self, event):
        self.log("Removed window id: %d" % event.container.id)
        self.removeWindow(event.container.id)


    def windowFocused(self, event):
        focusedWindow = utils.findFocused(self.con)
        # Ignore excluded windows
        if self.isExcluded(focusedWindow):
            return

        self.setStackLayout()


    def onBinding(self, command):
        if command == "nop swlm move up":
            self.moveUp()
        elif command == "nop swlm move down":
            self.moveDown()
        elif command == "nop swlm rotate ccw" or command == "nop swlm move left":
            self.rotateCCW()
        elif command == "nop swlm rotate cw"or command == "nop swlm move right":
            self.rotateCW()
        elif command == "nop swlm swap master":
            self.swapMaster()


    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        if window.workspace() is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        return False


    def setMasterWidth(self):
        if self.masterWidth is not None:
            self.con.command("[con_id=%s] resize set %s 0 ppt" % (self.masterId, self.masterWidth))
            self.logCaller("Set window %d width to %d" % (self.masterId, self.masterWidth))


    def moveWindow(self, moveId, targetId):
        self.con.command("[con_id=%d] mark --add move_target" % targetId)
        self.con.command("[con_id=%d] move container to mark move_target" % moveId)
        self.con.command("[con_id=%d] unmark move_target" % targetId)
        self.logCaller("Moved window %s to mark on window %s" % (moveId, targetId))


    def pushWindow(self, windowId):
        # Check if master is empty
        if self.masterId == 0:
            self.log("Made window %d master" % windowId)
            self.masterId = windowId
            return

        # Check if we need to initialize the stack
        if len(self.stackIds) == 0:
            # Make sure the new window is in a valid position
            self.moveWindow(windowId, self.masterId)

            # Swap with master
            self.stackIds.append(self.masterId)
            self.con.command("move left")
            self.masterId = windowId
            self.log("Initialized stack with %d, new master %d" % (self.stackIds[0], windowId))
            self.setMasterWidth()
            return

        # Put new window at top of stack
        targetId = self.stackIds[-1]
        self.moveWindow(windowId, targetId)
        self.con.command("[con_id=%s] focus" % windowId)
        self.con.command("move up")

        # Swap with master
        prevMasterId = self.masterId
        self.con.command("[con_id=%s] swap container with con_id %s" % (windowId, prevMasterId))
        self.stackIds.append(self.masterId)
        self.masterId = windowId
        self.setMasterWidth()


    def popWindow(self):
        # Check if last window is being popped
        if len(self.stackIds) == 0:
            self.masterId = 0
            self.log("Closed last window, nothing to do")
            return

        # Move top of stack to master position
        self.masterId = self.stackIds.pop()
        self.con.command("[con_id=%s] focus" % self.masterId)

        # If stack is not empty, we need to move the view to the master position
        if len(self.stackIds) != 0:
            self.con.command("move left")
            self.setMasterWidth()

        self.log("Moved top of stack to master")


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


    def arrangeExistingLayout(self):
        workspace = utils.findFocused(self.con).workspace()
        untracked = []
        for node in workspace.nodes:
            if len(node.nodes) == 0:
                # Check if window should remain untracked
                if (self.isExcluded(node)):
                    continue

                untracked.append(node.id)
                self.log("arrangeExistingLayout: Found untracked window %d" % node.id)
            elif len(node.nodes) > 0:
                for conNode in node.nodes:
                    # Check if window should remain untracked
                    if (self.isExcluded(node)):
                        continue

                    untracked.append(node.id)
                    self.log("arrangeExistingLayout: Found untracked window %d" % node.id)  

        for windowId in untracked:
            if windowId != self.masterId and windowId not in self.stackIds:
                self.setStackLayout()
                # Unfloat the window, then treat it like a new window
                self.con.command("[con_id=%s] focus" % windowId)
                self.pushWindow(windowId)
                self.log("arrangeExistingLayout: Pushed window %d" % windowId)

        self.setStackLayout()
        self.log("arrangeExistingLayout: masterId is %d" % self.masterId)


    def removeWindow(self, windowId):
        if self.masterId == windowId:
            # If window is master, pop the next one off the stack
            self.popWindow()
        else:
            # If window is not master, remove from stack and exist
            try:
                self.stackIds.remove(windowId)
            except BaseException as e:
                # This should only happen if an untracked window was closed
                self.log("WTF: window not master or in stack")


    def moveUp(self):
        focusedWindow = utils.findFocused(self.con)

        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Swap master and top of stack if only two windows, or focus is top of stack
        if len(self.stackIds) < 2 or focusedWindow.id == self.stackIds[-1]:
            targetId = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped window %d with master" % targetId)
            return

        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with window above
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[i+1]))
                self.stackIds[i] = self.stackIds[i+1]
                self.stackIds[i+1] = focusedWindow.id
                self.log("Swapped window %d with %d" % (focusedWindow.id, self.stackIds[i]))
                return


    def moveDown(self):
        # Check if stack only has one window
        if len(self.stackIds) < 2:
            return

        focusedWindow = utils.findFocused(self.con)
        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Check if we hit bottom of stack
        if focusedWindow.id == self.stackIds[0]:
            self.log("Bottom of stack, nowhere to go")
            return

        # Swap with top of stack if master is focused
        if focusedWindow.id == self.masterId:
            self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[-1]))
            self.masterId = self.stackIds.pop()
            self.stackIds.append(focusedWindow.id)
            self.log("Swapped master %d with top of stack %d" % (self.stackIds[-1], self.masterId))
            return

        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with window below
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[i-1]))
                self.stackIds[i] = self.stackIds[i-1]
                self.stackIds[i-1] = focusedWindow.id
                self.log("Swapped window %d with %d" % (focusedWindow.id, self.stackIds[i]))
                return


    def rotateCCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap top of stack with master, then move old master to bottom
        newMasterId = self.stackIds.pop()
        prevMasterId = self.masterId
        bottomId = self.stackIds[0]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMasterId, prevMasterId))
        self.log("swapped top of stack with master")
        self.moveWindow(prevMasterId, bottomId)
        self.log("Moved previous master to bottom of stack")

        # Update record
        self.masterId = newMasterId
        self.stackIds.appendleft(prevMasterId)


    def rotateCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap bottom of stack with master, then move old master to top
        newMasterId = self.stackIds.popleft()
        prevMasterId = self.masterId
        topId = self.stackIds[-1]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMasterId, prevMasterId))
        self.log("swapped bottom of stack with master")
        self.moveWindow(prevMasterId, topId)
        self.con.command("[con_id=%d] focus" % prevMasterId)
        self.con.command("move up")
        self.con.command("[con_id=%d] focus" % newMasterId)
        self.log("Moved previous master to top of stack")

        # Update record
        self.masterId = newMasterId
        self.stackIds.append(prevMasterId)


    def swapMaster(self):
        # Exit if less than two windows
        if len(self.stackIds) == 0:
            self.log("Stack emtpy, can't swap")
            return
            
        focusedWindow = utils.findFocused(self.con)

        if focusedWindow is None:
            self.log("No window focused, can't swap")
            return

        # If focus is master, swap with top of stack
        if focusedWindow.id == self.masterId:
            targetId = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped master with top of stack")
            return

        # Find focused window in record
        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.masterId))

                # Refocus the previous master
                self.con.command("[con_id=%d] focus" % self.masterId)
                self.stackIds[i] = self.masterId

                # Update record
                self.masterId = focusedWindow.id
                self.log("Swapped master with window %d" % focusedWindow.id)
                return
