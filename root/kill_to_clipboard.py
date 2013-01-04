import sublime_plugin
import sublime


class KillLocation:
    def __init__(self):
        self.kill_points = []
        self.kill_id = 0
        self.locked = False

    def performed_kill(self, view, regions):
        view_id = view.id
        if view_id != self.kill_id:
            self.locked = True

        compare_points = []
        for r in regions:
            compare_points.append(r.begin())

        if compare_points != self.kill_points:
            self.locked = True

        self.kill_points = compare_points
        self.kill_id = view_id

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def is_locked(self):
        return self.locked

kill_location = KillLocation()


class KillToClipboardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("move_to", {"to": "hardeol", "extend": True})

        text_items = []
        regions = []
        for selreg in self.view.sel():
            if selreg.empty():
                selreg = sublime.Region(selreg.a, selreg.a + 1)
            text_items.append(self.view.substr(selreg))
            regions.append(selreg)
        text = "\n".join(text_items)

        kill_location.performed_kill(self.view, regions)
        if kill_location.is_locked():
            sublime.set_clipboard(text)
        else:
            sublime.set_clipboard(sublime.get_clipboard() + text)
        kill_location.unlock()
        self.view.run_command("right_delete")


class YankFromClipboardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        kill_location.lock()
        self.view.run_command("paste")


class KillToClipboardEvents(sublime_plugin.EventListener):
    def on_activated(self, view):
        kill_location.lock()
