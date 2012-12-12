import subprocess
import sublime
import sublime_plugin


class RunMysqlCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        current_file = self.view.file_name()
        self.current_file = current_file

        window = sublime.active_window()

        if current_file == None:
            current_file = "None" + self.view.substr(self.view.line(0))
            file_name = self.view.substr(sublime.Region(0, self.view.size()))
            tab_name = "untitled"
        else:
            file_name = current_file.split("/")[-1]
            tab_name = file_name

        self.tab_name = tab_name
        self.file_name = file_name
        self.window = window

        region = self.view.sel()[0]
        if region.empty():
            args = self.view.substr(self.view.line(region.a))
        else:
            args = self.view.substr(region)
        cmd = '/usr/local/mysql/bin/mysql -uroot -t -e"' + args + '"'

        output = ''
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result, error = process.communicate()
            if error != '':
                output = error
            else:
                output = str(result)
        except OSError, excpt:
            output = str(excpt)

        view = self.get_output_view()
        edit = view.begin_edit()
        view.insert(edit, view.size(), "\n" + output)
        view.end_edit(edit)
        view.show(view.size())

    # TODO: seems like we should be able to just store what the view is, rather than search for it every time
    # but when I tried doing that before by storing it in self.output_view, it did not work
    def get_output_view(self):
        for window in sublime.windows():
            for view in window.views():
                if view.settings().get('parent_file') == self.current_file:
                    return view
        return self.build_output_view()

    def build_output_view(self):
        window = sublime.active_window()
        view = window.new_file()
        view.settings().set('parent_file', self.current_file)
        view.settings().set('word_wrap', True)
        view.set_name('output from %s' % (self.tab_name))
        view.settings().set("RunInScratch", True)
        view.set_scratch(True)
        return view
