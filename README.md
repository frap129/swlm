# [WIP] swlm - Sway Workspace Layout Manager

swlm is a daemon that handles layout management on a per-workspace basis. Each `WorkspaceLayoutManager` (WLM) is
responsible for managing all of the tiling windows on a given workspace. The `mananagers/` directoy contains files
that each hold an implementation of a WLM, with `WorkspaceLayoutManager.py` containing the parent class from which
all WLMs are derived.

```
Usage: swlm.py [options]

Options:
  -h, --help            show this help message and exit
  --default=LAYOUT_MANAGER
                        The LayoutManager to apply to all workspaces at
                        startup. default: Autotiling
  -e 1,2,.. , --exclude-workspaces=1,2,..
                        List of workspaces numbers that should be ignored.
  -o HDMI-0,DP-0,.. , --outputs=HDMI-0,DP-0,..
                        List of outputs that should be used instead of all.
  -d, --debug           Enable debug messages
  -w WIDTH, --master-width=WIDTH
                        MasterStack only: the percent screen width the master
                        window should fill.
  -l LAYOUT, --stack-layout=LAYOUT
                        MasterStack only: The layout of the stack. ("tabbed",
                        "stacked", "splitv") default: splitv
```

### TODO
- [ ] Improve configuration
  - [ ] Configuration file with more per-workspace options 
  - [ ] Load custom WorkspaceLayoutManagers from config path
  - [ ] Reload config without restarting swlm
- [ ] Replace "windowClosed?" in WLMs with "windowRemoved", call it when a window closes OR moves to a different workspace
- [ ] Differentiate WLMs that support managing existing windows
  - [ ] Add warning (swaynag?) when enabling WLMs that don't support existing windows on a workspace with windows
- [ ] More Layouts!
- [ ] MasterStack:
  - [ ] Fix stack window sizes changes when moving up/down
  - [ ] If user changes the size of master, maintain that size
  - [ ] Automatically arrange pre-existing windows into correct layout
- [ ] idk im probably forgetting a lot
- [X] ~Differentiate WLMs that support window movement~
  - [X] ~Add wrappers for window movement. Defaults would be used for WLMs that support movement, but WLMs that don't can override with better defaults (ex for MasterStack: replace up/down with move up/down in stack, left/right with rotation)~

## Installation

Because swlm is still early in development, I haven't come up with a way to package it yet. For now, clone this
repositiory and symlink `swlm.py` to `~/.local/bin/swlm` or any directoy in your PATH.

## Layout Managers

The layout manager controlling a workspace can be dynamically changed using the command `nop layout <LAYOUT>`. In
order to handle window movement in layouts that don't use standard sway up/down/left/right, a WLM can override
these commands with better defaults, and swlm will fall back the regular command for WLMs that don't. To use the
WLM provided movement commands, replace your `move <direction>` bindsyms with
```
# Override move binds
bindsym $mod+Shift+Left nop swlm move left
bindsym $mod+Shift+Down nop swlm move down
bindsym $mod+Shift+Up nop swlm move up
bindsym $mod+Shift+Right nop swlm move right
```

### none

The `none` layout manager does not manage any windows. It exists as a reference implementation, and to allow users
to disable layout management on a given workspace.

Binding:
```
bindym <your bind here> nop swlm layout none # disable layout management on a workspace
```

### Autotiling

Based on nwg-piotr's [autotiling](https://github.com/nwg-piotr/autotiling/blob/master/autotiling/main.py),
the `Autotiling` layout manager alternates between splith and splitv based on a windows height/width ratio.
`Autotiling` excludes floating tabbed, and stacked windows.

Binding:
```
bindym <your bind here> nop swlm layout Autotiling # set focused workspace's layout manager to Autotiling
```

### MasterStack

`MasterStack` is inspired by dwm/dwl/river, but is my own take on it. It implements a master window with a stack
on the right side. When a new window is created, it replaces master and master is placed on top of the stack.
If the master window is deleted, the top of the stack replaces master. `MasterStack` implements a keybind for
swapping. When swapping, the focused window is swapped with master. If the focused window is master, it gets
swapped with the top of the stack. `MasterStack` also implements rotation. When rotating counter-clockwise,
master is moved to the bottom of the stack, and the top of the stack becomes the new master. Conversely,
rotating clockwise moves master to the top of the stack, and the bottom of the stack becomes the new master.

`MasterStack` provides overrides for `move <directon>` binds. 

Known bugs:
- Breaks when a window is moved to a different workspace
- Only works correctly if workspace has no windows when its created.

Bindings:
```
bindym <your bind here> nop swlm layout MasterStack # set focused workspace's layout manager to MasterStack
bindym <your bind here> nop swlm swap master # swap focused window with master
bindym <your bind here> nop swlm rotate cw # rotate layout cw 1 window
bindym <your bind here> nop swlm rotate ccw # rotate layout ccw 1 window
```
