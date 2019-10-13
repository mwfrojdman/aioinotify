from enum import Enum
from pathlib import Path


class InotifyFlag(Enum):
    access = 0x1
    modify = 0x2
    attrib = 0x4
    close_write = 0x8
    close_nowrite = 0x10
    open = 0x20
    moved_from = 0x40
    moved_to = 0x80
    create = 0x100
    delete = 0x200
    delete_self = 0x400
    move_self = 0x800
    # the flags below can't be subscribed to
    unmount = 0x2000
    q_overflow = 0x4000
    ignored = 0x8000
    isdir = 0x40000000


ALL_FLAGS = {flag for flag in InotifyFlag if flag is not InotifyFlag.ignored}


class InotifyEvent:
    """
    A file system event from a monotored aioinotify.watch.Watch.
    """

    def __init__(self, pathname, event):
        self.pathname = pathname
        self.event = event


class HighLevelEvent:
    def __init__(self, path: Path, cookie: int, mask: int):
        self.path = path
        self.cookie = cookie
        self.mask = mask

    def __str__(self):
        flags = ', '.join(member.name for member in InotifyFlag if getattr(self, member.name))
        cookie = '' if self.cookie == 0 else self.cookie
        return f'{self.path}: {flags} ({self.mask}){cookie}'


class _MaskDescriptor:
    """A utility descriptor for InotifyEvent. It gets the event object's _mask attribute and
    returns a bool telling if a certain bit was set in the mask."""

    def __init__(self, bit):
        self.bit = bit

    def __get__(self, obj, objtype):
        return obj.mask & self.bit != 0


for member in InotifyFlag:
    setattr(HighLevelEvent, member.name, _MaskDescriptor(member.value))
del member
