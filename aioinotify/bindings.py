"""
This module contains ctypes bindings to the inotify functions from libc
"""
from ctypes import CDLL, c_int, get_errno, Structure, c_uint32, sizeof, c_char_p
import os
from pathlib import Path


class InotifyEventStructure(Structure):
    """
    struct inotify_event {
        int      wd;       /* Watch descriptor */
        uint32_t mask;     /* Mask describing event */
        uint32_t cookie;   /* Unique cookie associating related
                              events (for rename(2)) */
        uint32_t len;      /* Size of name field */
        char     name[];   /* Optional null-terminated name */
    };
    """
    _fields_ = [('wd', c_int), ('mask', c_uint32), ('cookie', c_uint32), ('len', c_uint32)]


INOTIFY_EVENT_SIZE = sizeof(InotifyEventStructure)



libc = CDLL('libc.so.6', use_errno=True)

libc.inotify_init1.argtypes = [c_int]
libc.restype = c_int


def init(nonblock=False):
    """Wraps inotify.init1.
    :param bool nonblock: Optional argument. Setting it to true leads to opening the inotify pipe
    in non-blocking mode.
    :return: The opened inotify pipe wrapped in a python file object.
    """
    flags = 0
    if nonblock:
        flags |= os.O_NONBLOCK
    fd = libc.inotify_init1(flags)
    if fd == -1:
        raise OSError(get_errno(), 'Failed to initialize inotify')
    return os.fdopen(fd, 'rb')


libc.inotify_add_watch.argtypes = [c_int, c_char_p, c_uint32]
libc.inotify_add_watch.restype = c_int


def add_watch(fd, path: Path, mask: int) -> int:
    """Wraps inotify_add_watch.
    :param str Path: The path to watch for file system events
    :param int mask:
    :return: The watch descriptor
    :rtype: int
    """
    if not isinstance(path, Path):
        raise TypeError('path is not a Path')
    if mask == 0:
        raise ValueError('add_watch must be called with at least on filter enabled')
    encoded_path = os.fsencode(path)
    watch_descriptor = libc.inotify_add_watch(fd, encoded_path, mask)
    if watch_descriptor == -1:
        raise OSError(get_errno(), 'Failed to add inotify watch')
    return watch_descriptor


libc.inotify_rm_watch.argtypes = [c_int, c_int]
libc.inotify_rm_watch.restype = c_int


def rm_watch(fd, wd):
    res = libc.inotify_rm_watch(fd, wd)
    if res != 0:
        raise OSError(get_errno(), 'Failed to remove inotify watch')
