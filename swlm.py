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


def log(msg):
    if options.debug:
        print(msg)


def isExcluded(workspace):
    if workspace is None:
        return True

    if options.excludes and workspace.num in options.excludes:
        return True

    if options.outputs and workspace.ipc_data["output"] not in options.outputs:
        return True

    return False


def findFocusedWorkspace(con):
    workspace = None
    for workspace in con.get_workspaces():
        if workspace.focused:
            workspace = workspace
            break

    return workspace


def windowCreated(con, event):
    # Check if we should pass this call to a manager
    workspace = findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("windowCreated: workspace or output excluded")
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("windowCreated: No manager for workpsace %d, ignoring" % workspace.num)
        return

    log("windowCreated: calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowCreated(event)


def windowFocused(con, event):
    # Check if we should pass this call to a manager
    workspace = findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("windowFocused: workspace or output excluded")
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("windowFocused: No manager for workpsace %d, ignoring" % workspace.num)
        return

    log("windowFocused: Calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowFocused(event)


def windowClosed(con, event):
    # Check if we should pass this call to a manager
    workspace = findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("windowClosed: workspace or output excluded")
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("windowClosed: No manager for workpsace %d, ignoring" % workspace.num)
        return

    log("windowClosed: calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowClosed(event)


def windowMoved(con, event):
    # Check if we should pass this call to a manager
    workspace = findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("windowMoved: workspace or output excluded")
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("windowMoved: No manager for workpsace %d, ignoring" % workspace.num)
        return

    log("windowMoved: calling manager for workspace %d" % workspace.num)
    managers[workspace.num].windowMoved(event)


def recvBinding(con, event):
    # Exit early if binding isnt for slwm
    command = event.ipc_data["binding"]["command"].strip()
    if "nop" not in command:
        return
        
    # Check if we should pass this call to a manager
    workspace = findFocusedWorkspace(con)
    if isExcluded(workspace):
        log("recvBinding: workspace or output excluded")
        return

    # Check if command is to create a layout manager
    if "nop swlm move" in command and managers[workspace.num].overridesMoveBinds:
        managers[workspace.num].binding(command)
        log("recvBinding: Passed bind to manager on workspace %d" % workspace.num)
        return
    elif "nop swlm move " in  command:
        moveCmd = command.replace("nop swlm ", '')
        con.command(moveCmd)
        log("recvBinding: Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
        return
    elif command == "nop swlm layout none":
        # Create no-op WLM to prevent onWorkspace from overwriting
        managers[workspace.num] = WorkspaceLayoutManager(con, workspace, options)
        log("recvBinding: Destroyed manager on workspace %d" % workspace.num)
        return
    elif command == "nop swlm layout MasterStack":
        managers[workspace.num] = MasterStackLayoutManager(con, workspace, options)
        log("recvBinding: Created MasterStackLayoutManager on workspace %d" % workspace.num)
        return
    elif command == "nop swlm layout Autotiling":
        managers[workspace.num] = AutotilingLayoutManager(con, workspace, options)
        log("recvBinding: Created AutotlingLayoutManager on workspace %d" % workspace.num)
        return

    # Pass command to the appropriate manager
    if workspace.num not in managers:
        log("recvBinding: No manager for workpsace %d, ignoring" % workspace.num)
        return
        
    log("recvCommand: calling manager for workspace %d" % workspace.num)
    managers[workspace.num].binding(command)

def onWorkspace(con, event):
    workspace = findFocusedWorkspace(con)
    if workspace.num not in managers:
        if options.default == "Autotiling":
            managers[workspace.num] = AutotilingLayoutManager(con, workspace, options)
            log("Initialized workspace %d with AutotilingLayoutManager" % workspace.num)
        elif options.default == "MasterStack":
            managers[workspace.num] = MasterStackLayoutManager(con, workspace, options)
            log("Initialized workspace %d with MasterStackLayoutManager" % workspace.num)

def main():
    setproctitle("swlm")

    # Get connection to sway
    con = Connection()
    con.on(Event.WINDOW_FOCUS, windowFocused)
    con.on(Event.WINDOW_NEW, windowCreated)
    con.on(Event.WINDOW_CLOSE, windowClosed)
    con.on(Event.WINDOW_MOVE, windowMoved)
    con.on(Event.BINDING, recvBinding)
    log("swlm started")

    # Set default layout maangers
    if options.default and options.default != "none":
        con.on(Event.WORKSPACE, onWorkspace)
        for workspace in con.get_workspaces():
            if options.default == "Autotiling":
                managers[workspace.num] = AutotilingLayoutManager(con, workspace, options)
                log("Initialized workspace %d with AutotilingLayoutManager" % workspace.num)
            elif options.default == "MasterStack":
                managers[workspace.num] = MasterStackLayoutManager(con, workspace, options)
                log("Initialized workspace %d with MasterStackLayoutManager" % workspace.num)

    try:
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
