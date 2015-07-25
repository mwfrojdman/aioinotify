from enum import Enum


class InotifyMask(Enum):
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


class InotifyEvent:
    def __init__(self, pathname, event):
        self.pathname = pathname
        self._mask = event.mask
        self.wd = event.wd
        self.cookie = event.cookie

    def __str__(self):
        bits = [member.name for member in InotifyMask if getattr(self, member.name)]
        #bits = [bit_name for bit_name in self.bit_names if getattr(self, bit_name)]
        return 'path={pathname}: {bits}'.format(
            pathname=self.pathname, bits=', '.join(bits))

    def as_dict(self):
        return {
            'path': self.pathname,
            'bits': [member.name for member in InotifyMask if getattr(self, member.name)]}


class _MaskDescriptor:
    """A utility descriptor for InotifyEvent. It gets the event object's _mask attribute and
    returns a bool telling if a certain bit was set in the mask."""

    def __init__(self, bit):
        self.bit = bit

    def __get__(self, obj, objtype):
        return obj._mask & self.bit != 0


for member in InotifyMask:
    setattr(InotifyEvent, member.name, _MaskDescriptor(member.value))
del member
