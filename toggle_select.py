import sublime
import sublime_plugin

onnSelectingBlock = False


class OnnStartSelectCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        global onnSelectingBlock
        onnSelectingBlock = True
        cursor = [s for s in self.view.sel()]
        self.view.add_regions("onn_start", cursor, "", "", sublime.HIDDEN | sublime.PERSISTENT)
        sublime.status_message("toggle select ON")


class OnnCancelSelectCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        global onnSelectingBlock
        if (not onnSelectingBlock):
            return
        onnSelectingBlock = False
        onn_start = self.view.get_regions("onn_start")
        if onn_start:
            self.view.erase_regions("onn_start")
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(onn_start[0].end(), onn_start[0].end()))
        sublime.status_message("toggle select canceled")


class OnnCutCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        global onnSelectingBlock
        onnSelectingBlock = False
        self.view.run_command("cut")


class OnnCopyCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        global onnSelectingBlock
        self.view.run_command("copy")
        onnSelectingBlock = False
        cursor = [s for s in self.view.sel()]
        cursor_begin = cursor[0].begin()
        cursor_end = cursor[0].end()
        onn_start = self.view.get_regions("onn_start")
        onn_begin = onn_start[0].begin()
        self.view.erase_regions("onn_start")
        self.view.sel().clear()
        if cursor_begin < onn_begin:
            self.view.sel().add(sublime.Region(cursor_begin, cursor_begin))
        else:
            self.view.sel().add(sublime.Region(cursor_end, cursor_end))


class OnnToggleSelectDetector(sublime_plugin.EventListener):
    def __init__(self, *args, **kwargs):
        sublime_plugin.EventListener.__init__(self, *args, **kwargs)

    def on_query_context(self, view, key, operator, operand, match_all):
        global onnSelectingBlock
        if (key == "onn_toggle_select") and (operator == sublime.OP_EQUAL):
            return (onnSelectingBlock == operand)
        else:
            return None
