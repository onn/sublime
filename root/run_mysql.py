import subprocess
import sublime
import sublime_plugin


class RunMysqlCommand(sublime_plugin.TextCommand):
    SQLSTMT_STARTS = frozenset(['select', 'update', 'delete', 'insert', 'replace', 'use', 'load', 'describe', 'desc', 'explain', 'create', 'alter'])

    def send_sql(self, stmt):
        cmd = '/usr/local/mysql/bin/mysql --login-path=devroot -t -e"' + stmt + '" lsfs_main'
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
        return output

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
            stmt = self.find_statement(region)
        else:
            stmt = self.view.substr(region).strip()

        if len(stmt) == 0:
            output = "unable to find statement"
        else:
            output = self.send_sql(stmt)

        view = self.get_output_view()
        edit = view.begin_edit()
        view.insert(edit, view.size(), "\n" + output)
        view.end_edit(edit)
        view.show(view.size())

    def has_sqlstmt_start(self, line):
        if len(line) == 0:
            return False
        if line[0].isspace():
            return False
        first_word = line.partition(' ')[0].lower()
        return first_word in self.SQLSTMT_STARTS

    def find_statement(self, cursor):
        cursor_lreg = self.view.line(cursor.a)

        lreg = cursor_lreg
        while True:
            begin_stmt = lreg.begin()
            line = str(self.view.substr(lreg))
            if self.has_sqlstmt_start(line):
                break
            if begin_stmt == 0:
                return ''
            lreg = self.view.line(begin_stmt - 1)

        max_end = self.view.size()
        lreg = cursor_lreg
        while True:
            end_stmt = lreg.end()
            if end_stmt >= max_end:
                break
            line = self.view.substr(lreg)
            if len(line) == 0 or line[-1] == ';' or line.isspace():
                break
            curr_begin = lreg.begin()
            if (curr_begin > begin_stmt) and self.has_sqlstmt_start(line):
                end_stmt = curr_begin - 1
                break
            lreg = self.view.line(end_stmt + 1)

        return self.view.substr(sublime.Region(begin_stmt, end_stmt)).strip()

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
