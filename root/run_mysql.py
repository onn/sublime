import sublime, sublime_plugin, sys, os
import subprocess
import time

# weird stuff needed to get MySQLdb working
directory = os.path.dirname(os.path.realpath(__file__)) + "\\"
sys.path.append(directory+"\\MySQLdb")
sys.path.append(directory+"\\MySQLdb\\constants")

from MySQLdb import *
from MySQLdb.constants import *

class AsciiTableBuilder:
    def determine_field_widths(self, rows, headers):
        widths = []
        for column_index in range(0, len(headers)):
            max_width = len(headers[column_index])
            for values in rows:
                value_len = len(values[column_index])
                if value_len > max_width:
                    max_width = value_len
            widths.append(max_width)
        return widths

    def build_separator(self, widths):
        str = '+'
        for col_width in widths:
            str += ('-' * (col_width + 2)) + '+'
        return str

    def value_to_string(self, value):
        if value is None:
            return 'NULL'
        return str(value)

    def build_row(self, values, widths):
        str = '|'
        for column_index in range(0, len(widths)):
            max_width = widths[column_index]
            value_str = values[column_index]
            value_str = values[column_index]
            value_len = len(value_str)
            pad_len = (max_width - value_len) + 1
            str += (' ' * pad_len) + value_str + ' |'
        return (str + "\n")

    def convert_all_values_to_strings(self, old_rows):
        new_rows = []
        for old_values in old_rows:
            new_values = []
            for one_old in old_values:
                new_values.append(self.value_to_string(one_old))
            new_rows.append(new_values)
        return new_rows

    def run(self, rows, headers):
        rows = self.convert_all_values_to_strings(rows)
        widths = self.determine_field_widths(rows, headers)
        separator = self.build_separator(widths) + "\n"
        retval = ''
        retval += separator
        retval += self.build_row(headers, widths)
        retval += separator
        for values in rows:
            retval += self.build_row(values, widths)
        retval += separator
        return retval


class SaveView(sublime_plugin.EventListener):
    def __init__(self):
        self.view = None
        self.table_builder = AsciiTableBuilder()

    def connect_to_database(self, database=None):
        db_settings = sublime.load_settings('onn.sublime-settings')
        connections_list = db_settings.get('connections')

        params = {}
        if database is None:
            database = db_settings.get('default_schema')

        for connection in connections_list:
            if connection.get('name') == database:
                params = connection

        self.db = connect(params.get('host'), params.get('user'), params.get('pass'), params.get('db'), params.get('port'))

    def query(self, query):
        cursor = self.db.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = []
        for header_detail in cursor.description:
            headers.append(header_detail[0])
        output = self.table_builder.run(data, headers)
        return output

    def save_view(self, view):
        self.view = view

    def get_view(self):
        return self.view

    def has_view(self):
        return not (self.view is None)

    def on_close(self, view):
        if (not (self.view is None)) and (view.name() == self.view.name()):
            self.view = None

class RunMysqlCommand(sublime_plugin.TextCommand):
    SQLSTMT_STARTS = frozenset(['select', 'update', 'delete', 'insert', 'replace', 'use', 'load', 'describe', 'desc', 'explain', 'create', 'alter'])

    def __init__(self, view):
        super(RunMysqlCommand, self).__init__(view)
        self.save_output_view = SaveView()

    def send_sql_by_pipe(self, stmt):
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

    def send_sql_by_connection(self, stmt):
        return self.save_output_view.query(stmt)

    def send_sql(self, stmt):
        return self.send_sql_by_connection(stmt)

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

        view = self.get_output_view()
        if len(stmt) == 0:
            output = "unable to find statement"
        else:
            output = self.send_sql(stmt)

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
        if self.save_output_view.has_view():
            return self.save_output_view.get_view()
        new_view = None
        for window in sublime.windows():
            for check_view in window.views():
                if check_view.settings().get('parent_file') == self.current_file:
                    new_view = check_view
        if new_view is None:
            new_view = self.build_output_view()
        self.save_output_view.save_view(new_view)
        self.save_output_view.connect_to_database()
        return new_view

    def build_output_view(self):
        window = sublime.active_window()
        view = window.new_file()
        view.settings().set('parent_file', self.current_file)
        view.settings().set('word_wrap', True)
        view.set_name('output from %s' % (self.tab_name))
        view.settings().set("RunInScratch", True)
        view.set_scratch(True)
        return view
