#!/usr/bin/env python3
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
from i3ipc import Event, Connection
import inspect
from setproctitle import setproctitle

import utils
from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
from managers.MasterStackLayoutManager import MasterStackLayoutManager
from managers.AutotilingLayoutManager import AutotilingLayoutManager


class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


options = utils.getUserOptions()
managers = WorkspaceLayoutManagerDict()
workspaceWindows = WorkspaceLayoutManagerDict()


def windowCreated(con, event):
    # Check if we should pass this call to a manager
    workspace = utils.findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("Workspace or output excluded")
        return

    # Check if we have a layoutmanager
    if workspace.num not in managers:
        log("No manager for workpsace %d, ignoring" % workspace.num)
        return

    # Store window
    window = utils.findFocused(con)
    if window is not None:
        workspaceWindows[workspace.num].append(window.id)

    # Pass event to the layout manager
    log("Calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowAdded(event)


def windowFocused(con, event):
    # Check if we should pass this call to a manager
    workspace = utils.findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("Workspace or output excluded")
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("No manager for workpsace %d, ignoring" % workspace.num)
        return

    # log("windowFocused: Calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowFocused(event)


def windowClosed(con, event):
    # Check if we should pass this call to a manager
    workspace = utils.findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("Workspace or output excluded")
        return

    # Check if we have a manager
    if workspace.num not in managers:
        log("No manager for workpsace %d, ignoring" % workspace.num)
        return

    # Remove window
    try:
        workspaceWindows[workspace.num].remove(event.container.id)
    except BaseException as e:
        log("Untracked window %d closed on %d" % (event.container.id, workspace.num))

    # Pass command to the appropriate manager
    log("Calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowRemoved(event)


def windowMoved(con, event):
    # Check if we should pass this call to a manager
    window = utils.findFocused(con)
    workspace = window.workspace()
    if isExcluded(workspace):
        log("Workspace or output excluded")
        return

    # Ensure the workspace is being managed first
    if workspace.num not in managers:
        log("No manager for workpsace %d, ignoring" % workspace.num)
        return

    # Check if the window has moved workspaces
    if window.id not in workspaceWindows[workspace.num]:
        log("Window untracked, or changed workspaces")
        # Find the windows old workspace
        for workspaceNum in managers:
            if window.id in workspaceWindows[workspaceNum]:
                # Call windowRemoved on old workspace
                log("Calling windowRemoved for workspace %d" % workspaceNum)
                workspaceWindows[workspaceNum].remove(window.id)
                managers[workspaceNum].windowRemoved(event)

                # Call windowAdded on new workspace
                log("Calling windowAdded for workspace %d" % workspace.num)
                workspaceWindows[workspace.num].append(window.id)
                managers[workspace.num].windowAdded(event)
                return

    # Window has moved within a workspace, call windowMoved
    log("Calling windowMoved for workspace %d" % workspace.num)
    managers[workspace.num].windowMoved(event)


def onBinding(con, event):
    # Exit early if binding isnt for slwm
    command = event.ipc_data["binding"]["command"].strip()
    if "nop swlm" not in command:
        return
        
    # Check if we should pass this call to a manager
    workspace = utils.findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("Workspace or output excluded")
        return

    # Handle movement commands
    if "nop swlm move" in command and managers[workspace.num].overridesMoveBinds:
        managers[workspace.num].onBinding(command)
        log("Passed bind to manager on workspace %d" % workspace.num)
        return
    elif "nop swlm move " in  command:
        moveCmd = command.replace("nop swlm ", '')
        con.command(moveCmd)
        log("Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
        return

    # Handle wlm creation commands
    if command == "nop swlm layout none":
        # Create no-op WLM to prevent onWorkspace from overwriting
        managers[workspace.num] = WorkspaceLayoutManager(con, workspace, options)
        log("Destroyed manager on workspace %d" % workspace.num)
        return
    elif command == "nop swlm layout MasterStack":
        managers[workspace.num] = MasterStackLayoutManager(con, workspace, options)
        log("Created %s on workspace %d" % (managers[workspace.num].shortName, workspace.num))
        return
    elif command == "nop swlm layout Autotiling":
        managers[workspace.num] = AutotilingLayoutManager(con, workspace, options)
        log("Created %s on workspace %d" % (managers[workspace.num].shortName, workspace.num))
        return

    # Pass unknown command to the appropriate wlm
    if workspace.num not in managers:
        log("No manager for workpsace %d, ignoring" % workspace.num)
        return
        
    log("Calling manager for workspace %d" % workspace.num)
    managers[workspace.num].onBinding(command)


def onWorkspace(con, event):
    workspace = utils.findFocusedWorkspace(con)
    setWorkspaceLayoutManager(con, workspace)


def setWorkspaceLayoutManager(con, workspace):
    if workspace.num not in managers:
        if options.default == AutotilingLayoutManager.shortName:
            managers[workspace.num] = AutotilingLayoutManager(con, workspace, options)
            logCaller("Initialized workspace %d with %s" % (workspace.num, managers[workspace.num].shortName))
        elif options.default == MasterStackLayoutManager.shortName:
            managers[workspace.num] = MasterStackLayoutManager(con, workspace, options)
            logCaller("Initialized workspace %d wth %s" % (workspace.num, managers[workspace.num].shortName))
    if workspace.num not in workspaceWindows:
        workspaceWindows[workspace.num] = []


def log(msg):
    if options.debug:
        print("%s: %s" % (inspect.stack()[1][3], msg))


def logCaller(msg):
    if options.debug:
        print("%s: %s" % (inspect.stack()[2][3], msg))


def isExcluded(workspace):
    if workspace is None:
        return True

    if options.excludes and workspace.num in options.excludes:
        return True

    if options.outputs and workspace.ipc_data["output"] not in options.outputs:
        return True

    return False


def main():
    setproctitle("swlm")

    # Get connection to sway
    con = Connection()
    con.on(Event.WINDOW_FOCUS, windowFocused)
    con.on(Event.WINDOW_NEW, windowCreated)
    con.on(Event.WINDOW_CLOSE, windowClosed)
    con.on(Event.WINDOW_MOVE, windowMoved)
    con.on(Event.BINDING, onBinding)
    log("swlm started")

    # Set default layout maangers
    if options.default and options.default != "none":
        con.on(Event.WORKSPACE, onWorkspace)
        for workspace in con.get_workspaces():
            setWorkspaceLayoutManager(con, workspace)
            workspaceWindows[workspace.num] = []

    try:
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
