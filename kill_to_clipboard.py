import sublime_plugin
import sublime


class KillLocation:
    def __init__(self):
        self.kill_points = []
        self.kill_id = 0

    def unchanged(self, view, regions):
        append = True
        view_id = view.id
        if view_id != self.kill_id:
            append = False

        compare_points = []
        for r in regions:
            compare_points.append(r.begin())

        if compare_points != self.kill_points:
            append = False

        self.kill_points = compare_points
        self.kill_id = view_id
        return append

kill_location = KillLocation()


class KillToClipboardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("move_to", {"to": "hardeol", "extend": True})

        text_items = []
        regions = []
        for s in self.view.sel():
            if s.empty():
                s = sublime.Region(s.a, s.a + 1)
            text_items.append(self.view.substr(s))
            regions.append(s)

        text = "\n".join(text_items)
        if kill_location.unchanged(self.view, regions):
            sublime.set_clipboard(sublime.get_clipboard() + text)
        else:
            sublime.set_clipboard(text)
        self.view.run_command("right_delete")
