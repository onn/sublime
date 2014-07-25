import subprocess
import sublime
import sublime_plugin
import time

class SaveView:
    def __init__(self):
        self.view = None

    def save_view(self, view):
        self.view = view

    def get_view(self):
        return self.view

    def has_view(self):
        return self.view is not None

save_output_view = SaveView()


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
        timestr = time.strftime("%Y-%m-%d %H:%M:%S ==> ", time.localtime())
        view.insert(edit, view.size(), timestr + stmt + "\n" + output + "\n")
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

    def get_output_view(self):
        if save_output_view.has_view():
            return save_output_view.get_view()
        new_view = self.build_output_view();
        save_output_view.save_view(new_view)
        return new_view

    def build_output_view(self):
        window = sublime.active_window()
        view = window.new_file()
        view.settings().set('word_wrap', True)
        view.set_name('output from %s' % (self.tab_name))
        view.settings().set("RunInScratch", True)
        view.set_scratch(True)
        return view
