"""System-wide hotkey via Carbon RegisterEventHotKey.

Narrow system API: only the registered shortcut is delivered, so no
Accessibility / Input Monitoring permission is required.  Still works
while another app is focused — essential for a non-activating panel.
"""

import ctypes
import traceback

# Virtual key / modifier bits used by callers (⌘E for the lens toggle).
kVK_ANSI_E = 0x0E
cmdKey = 1 << 8


def _four_char(s):
    """Pack a 4-char string into a Carbon FourCharCode / OSType (uint32).

    Carbon identifies event classes and hotkey owners with four-byte codes
    written as ASCII in headers (e.g. 'keyb', 'TLen').  ctypes needs the
    numeric form those APIs actually take.
    """
    return (ord(s[0]) << 24) | (ord(s[1]) << 16) | (ord(s[2]) << 8) | ord(s[3])


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


_EventHandlerProc = ctypes.CFUNCTYPE(
    ctypes.c_int32,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
)

_kEventClassKeyboard = _four_char("keyb")
_kEventHotKeyPressed = 5
_noErr = 0


class GlobalHotKey:
    """One system-wide hotkey; keeps C callbacks alive for the process life."""

    _SIG = _four_char("TLen")

    def __init__(self, key_code, modifiers, callback):
        self._callback = callback
        self._hot_key_ref = ctypes.c_void_p()
        self._handler_ref = ctypes.c_void_p()
        self._carbon = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/Carbon.framework/Carbon"
        )
        c = self._carbon
        c.GetEventDispatcherTarget.restype = ctypes.c_void_p
        c.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            _EventHotKeyID,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        c.RegisterEventHotKey.restype = ctypes.c_int32
        c.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
        c.UnregisterEventHotKey.restype = ctypes.c_int32
        c.InstallEventHandler.argtypes = [
            ctypes.c_void_p,
            _EventHandlerProc,
            ctypes.c_uint32,
            ctypes.POINTER(_EventTypeSpec),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        c.InstallEventHandler.restype = ctypes.c_int32
        c.RemoveEventHandler.argtypes = [ctypes.c_void_p]
        c.RemoveEventHandler.restype = ctypes.c_int32

        # Keep the UPP alive; Carbon holds only a raw function pointer.
        self._handler_upp = _EventHandlerProc(self._on_event)

        target = c.GetEventDispatcherTarget()
        hot_id = _EventHotKeyID(self._SIG, 1)
        err = c.RegisterEventHotKey(
            key_code, modifiers, hot_id, target, 0, ctypes.byref(self._hot_key_ref)
        )
        if err != _noErr or not self._hot_key_ref.value:
            raise OSError("RegisterEventHotKey failed: %s" % err)

        spec = (_EventTypeSpec * 1)(
            _EventTypeSpec(_kEventClassKeyboard, _kEventHotKeyPressed)
        )
        err = c.InstallEventHandler(
            target, self._handler_upp, 1, spec, None, ctypes.byref(self._handler_ref)
        )
        if err != _noErr:
            c.UnregisterEventHotKey(self._hot_key_ref)
            raise OSError("InstallEventHandler failed: %s" % err)

    def _on_event(self, _call_ref, _event, _user_data):
        try:
            self._callback()
        except Exception:
            traceback.print_exc()
        return _noErr

    def unregister(self):
        c = self._carbon
        if self._hot_key_ref.value:
            c.UnregisterEventHotKey(self._hot_key_ref)
            self._hot_key_ref.value = None
        if self._handler_ref.value:
            c.RemoveEventHandler(self._handler_ref)
            self._handler_ref.value = None
