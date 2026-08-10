"""Fullscreen rubber-band region picker for placing the reading lens."""

import sys

import objc
from Foundation import NSObject, NSMakeRect, NSMakePoint
from AppKit import (
    NSApp,
    NSPanel,
    NSView,
    NSColor,
    NSBezierPath,
    NSScreen,
    NSCursor,
    NSEvent,
    NSBackingStoreBuffered,
    NSWindowStyleMaskBorderless,
    NSScreenSaverWindowLevel,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSViewWidthSizable,
    NSViewHeightSizable,
    NSGraphicsContext,
    NSCompositingOperationClear,
    NSCompositingOperationSourceOver,
    NSRectFill,
    NSLeftMouseDraggedMask,
    NSLeftMouseUpMask,
    NSKeyDownMask,
    NSEventTypeLeftMouseDragged,
    NSEventTypeLeftMouseUp,
    NSEventTypeKeyDown,
)

#: Ignore click-without-drag / accidental tiny selections.
_MIN_PX = 4.0
_ESC = 53


class SelectPanel(NSPanel):
    """Borderless overlay that can take key focus for Escape."""

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


class SelectView(NSView):
    """Dimmed screen; rubber-band is owned by RegionSelectOverlay in screen space."""

    def initWithFrame_(self, frame):
        self = objc.super(SelectView, self).initWithFrame_(frame)
        self.owner = None
        return self

    def acceptsFirstMouse_(self, _ev):
        return True

    def acceptsFirstResponder(self):
        return True

    def resetCursorRects(self):
        self.addCursorRect_cursor_(self.bounds(), NSCursor.crosshairCursor())

    @objc.python_method
    def _local_selection(self):
        if self.owner is None:
            return None
        screen_sel = self.owner.selection_screen_rect()
        if screen_sel is None:
            return None
        win = self.window()
        if win is None:
            return None
        return win.convertRectFromScreen_(screen_sel)

    def drawRect_(self, _rect):
        NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.32).set()
        NSRectFill(self.bounds())
        sel = self._local_selection()
        if sel is None or sel.size.width < 0.5 or sel.size.height < 0.5:
            return
        # Only clear the part that intersects this display.
        b = self.bounds()
        x0 = max(sel.origin.x, b.origin.x)
        y0 = max(sel.origin.y, b.origin.y)
        x1 = min(sel.origin.x + sel.size.width, b.origin.x + b.size.width)
        y1 = min(sel.origin.y + sel.size.height, b.origin.y + b.size.height)
        if x1 <= x0 or y1 <= y0:
            return
        clipped = NSMakeRect(x0, y0, x1 - x0, y1 - y0)
        ctx = NSGraphicsContext.currentContext()
        ctx.setCompositingOperation_(NSCompositingOperationClear)
        NSRectFill(clipped)
        ctx.setCompositingOperation_(NSCompositingOperationSourceOver)
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.95).set()
        stroke = NSBezierPath.bezierPathWithRect_(clipped)
        stroke.setLineWidth_(1.5)
        stroke.stroke()

    def mouseDown_(self, ev):
        if self.owner is not None:
            self.owner.selection_began(NSEvent.mouseLocation())

    def keyDown_(self, ev):
        if ev.keyCode() == _ESC:
            if self.owner is not None:
                self.owner.escape()
            return
        objc.super(SelectView, self).keyDown_(ev)


class RegionSelectOverlay(NSObject):
    """One overlay window per display; selection tracked in screen coordinates."""

    def init(self):
        self = objc.super(RegionSelectOverlay, self).init()
        self._wins = []
        self._views = []
        self._on_complete = None
        self._on_cancel = None
        self._on_escape = None
        self._active = False
        self._anchor = None
        self._current = None
        self._local_monitor = None
        self._monitor_handler = None
        return self

    @objc.python_method
    def is_active(self):
        return bool(self._active)

    @objc.python_method
    def selection_screen_rect(self):
        if self._anchor is None or self._current is None:
            return None
        x0 = min(self._anchor.x, self._current.x)
        y0 = min(self._anchor.y, self._current.y)
        x1 = max(self._anchor.x, self._current.x)
        y1 = max(self._anchor.y, self._current.y)
        return NSMakeRect(x0, y0, x1 - x0, y1 - y0)

    @objc.python_method
    def _redisplay_all(self):
        for view in self._views:
            view.setNeedsDisplay_(True)

    @objc.python_method
    def selection_began(self, screen_pt):
        self._anchor = NSMakePoint(screen_pt.x, screen_pt.y)
        self._current = NSMakePoint(screen_pt.x, screen_pt.y)
        self._redisplay_all()

    @objc.python_method
    def selection_moved(self, screen_pt):
        if self._anchor is None:
            return
        self._current = NSMakePoint(screen_pt.x, screen_pt.y)
        self._redisplay_all()

    @objc.python_method
    def selection_ended(self, screen_pt):
        if self._anchor is None:
            self.cancel()
            return
        self._current = NSMakePoint(screen_pt.x, screen_pt.y)
        sel = self.selection_screen_rect()
        self._anchor = None
        self._current = None
        self._redisplay_all()
        if (
            sel is None
            or sel.size.width < _MIN_PX
            or sel.size.height < _MIN_PX
        ):
            self.cancel()
            return
        self.complete(sel)

    @objc.python_method
    def begin(self, on_complete, on_cancel, on_escape=None):
        if self._active:
            self.cancel()
        self._on_complete = on_complete
        self._on_cancel = on_cancel
        self._on_escape = on_escape
        self._anchor = None
        self._current = None
        self._wins = []
        self._views = []

        screens = list(NSScreen.screens() or [])
        if not screens:
            screens = [NSScreen.mainScreen()] if NSScreen.mainScreen() else []
        if not screens:
            sys.stderr.write("region-select: no screens available\n")
            sys.stderr.flush()
            if on_cancel is not None:
                on_cancel()
            return

        key_win = None
        for screen in screens:
            frame = screen.frame()
            win = SelectPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False
            )
            win.setOpaque_(False)
            win.setBackgroundColor_(NSColor.clearColor())
            win.setHasShadow_(False)
            win.setLevel_(NSScreenSaverWindowLevel)
            win.setIgnoresMouseEvents_(False)
            win.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            # Pin to this display; AppKit will not keep a single window spanning
            # multiple screens, so we create one panel per NSScreen instead.
            win.setFrame_display_(frame, True)

            view = SelectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, frame.size.width, frame.size.height)
            )
            view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            view.owner = self
            win.setContentView_(view)

            self._wins.append(win)
            self._views.append(view)
            if screen == NSScreen.mainScreen() or key_win is None:
                key_win = win

        self._active = True
        sys.stderr.write(
            "region-select: drawing mode activated (%d screen%s)\n"
            % (len(self._wins), "" if len(self._wins) == 1 else "s")
        )
        sys.stderr.flush()

        NSApp.activateIgnoringOtherApps_(True)
        for win in self._wins:
            win.orderFrontRegardless()
        if key_win is not None:
            key_win.makeKeyAndOrderFront_(None)
            key_win.makeFirstResponder_(key_win.contentView())
        NSCursor.crosshairCursor().set()
        for view in self._views:
            view.resetCursorRects()

        # Local monitor so drag/up keep working when the cursor crosses displays
        # (mouseDragged: alone stays on the window that got mouseDown:).
        mask = NSLeftMouseDraggedMask | NSLeftMouseUpMask | NSKeyDownMask

        def _monitor(event):
            if not self._active:
                return event
            et = event.type()
            if et == NSEventTypeLeftMouseDragged:
                self.selection_moved(NSEvent.mouseLocation())
                return None
            if et == NSEventTypeLeftMouseUp:
                self.selection_ended(NSEvent.mouseLocation())
                return None
            if et == NSEventTypeKeyDown and event.keyCode() == _ESC:
                self.escape()
                return None
            return event

        # Keep the callable alive; Carbon/AppKit only hold a weak-ish ref via bridge.
        self._monitor_handler = _monitor
        self._local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            mask, self._monitor_handler
        )

    @objc.python_method
    def complete(self, screen_rect):
        o, s = screen_rect.origin, screen_rect.size
        sys.stderr.write(
            "region-select: finished  pos=(%.1f, %.1f)  size=%.1f×%.1f\n"
            % (o.x, o.y, s.width, s.height)
        )
        sys.stderr.flush()
        cb = self._on_complete
        self._teardown()
        if cb is not None:
            cb(screen_rect)

    @objc.python_method
    def cancel(self):
        cb = self._on_cancel
        self._teardown()
        if cb is not None:
            cb()

    @objc.python_method
    def escape(self):
        """Esc: dismiss overlay and restore the previous lens (via on_escape)."""
        sys.stderr.write("region-select: escape — restore previous lens\n")
        sys.stderr.flush()
        cb = self._on_escape if self._on_escape is not None else self._on_cancel
        self._teardown()
        if cb is not None:
            cb()

    @objc.python_method
    def _teardown(self):
        self._active = False
        self._anchor = None
        self._current = None
        self._on_complete = None
        self._on_cancel = None
        self._on_escape = None
        if self._local_monitor is not None:
            NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None
        self._monitor_handler = None
        for win in self._wins:
            win.orderOut_(None)
        self._wins = []
        self._views = []
        NSCursor.arrowCursor().set()
