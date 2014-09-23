import sublime, sublime_plugin, sys, os
import subprocess
import time
import threading

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

    def build_padded_headers(self, headers):
        max_header_size = 0
        for curr_header in headers:
            curr_header_size = len(curr_header)
            if curr_header_size > max_header_size:
                max_header_size = curr_header_size

        padded = []
        for curr_header in headers:
            needed = max_header_size - len(curr_header)
            spaces = ' ' * needed
            padded.append(spaces + curr_header)
        return padded

    def build_separator(self, widths):
        str = '+'
        for col_width in widths:
            str += ('-' * (col_width + 2)) + '+'
        return str

    def value_to_string(self, value):
        if value is None:
            return 'NULL'
        return str(value)

    def row_to_line(self, values, widths):
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

    def build_line_per_row(self, rows, headers):
        rows = self.convert_all_values_to_strings(rows)
        widths = self.determine_field_widths(rows, headers)
        separator = self.build_separator(widths) + "\n"
        retval = ''
        retval += separator
        retval += self.row_to_line(headers, widths)
        retval += separator
        for values in rows:
            retval += self.row_to_line(values, widths)
        retval += separator
        return retval

    def build_line_per_field(self, rows, headers):
        rows = self.convert_all_values_to_strings(rows)
        padded_headers = self.build_padded_headers(headers)
        field_count = len(padded_headers)
        separator = ('*' * 25)
        retval = ''
        row_number = 0
        for values in rows:
            row_number += 1
            retval += separator + ' row ' + str(row_number) + ' ' + separator + "\n"
            for column_index in range(0, field_count):
                retval += padded_headers[column_index] + ": " + values[column_index] + "\n"
        return retval


class QueryRunnerThread(threading.Thread):
    def __init__(self, dbconn, stmt, table_builder, on_complete):
        self.dbconn = dbconn
        self.stmt = stmt
        self.table_builder = table_builder
        self.on_complete = on_complete
        threading.Thread.__init__(self)

    def run(self):
        cursor = self.dbconn.cursor()
        output = ""
        error = None
        try:
            start_time = time.time()
            cursor.execute(self.stmt)
            elapsed_amt = round(time.time() - start_time, 2)
            elapsed_str = str(elapsed_amt) + ' sec'
            if cursor.description is None:
                if self.stmt.lower().find("use") == 0:
                    return 'database changed\n'
                insert_id = cursor.lastrowid
                if insert_id > 0:
                    return 'last insert id: ' + str(insert_id) + ' (' + elapsed_str + ')\n'
                return str(cursor.rowcount) + ' rows affected (' + elapsed_str + ')\n'
            data = cursor.fetchall()
            headers = []
            for header_detail in cursor.description:
                headers.append(header_detail[0])
            row_count = len(data)
            if row_count == 0:
                return "no rows (" + elapsed_str + ")\n"

            if self.stmt[-2] == ';':
                output = self.table_builder.build_line_per_field(data, headers)
            else:
                output = self.table_builder.build_line_per_row(data, headers)
            output += str(row_count) + " rows (" + elapsed_str + ")\n"
        except Exception, excpt:
            error = excpt
            output = str(excpt) + "\n"
        sublime.set_timeout(lambda: self.on_complete(error, output), 1)


class SaveView:
    RECONNECT_MYSQL_ERRORS = frozenset([2006, 2013])

    def __init__(self):
        self.view = None
        self.source_tab = None
        self.table_builder = AsciiTableBuilder()
        self.selected_database = None
        self.dbconn = None

    def build_output_view_name(self):
        return 'mysql (%s): %s' % (self.selected_database, self.source_tab)

    def output_text(self, include_timestamp, text):
        edit = self.view.begin_edit()
        if include_timestamp:
            timestr = time.strftime("%Y-%m-%d %H:%M:%S ==> ", time.localtime())
        else:
            timestr = ""
        self.view.insert(edit, self.view.size(), timestr + text + "\n")
        self.view.end_edit(edit)
        self.view.show(self.view.size())

    def pick_database(self):
        self.ui_connection_list = []
        for connection in sublime.load_settings('onn.sublime-settings').get('connections'):
            self.ui_connection_list.append([connection.get('name'), 'Host: ' + connection.get('host')])
        window = sublime.active_window()
        window.show_quick_panel(self.ui_connection_list, self.connect_to_database)

    def connect_to_database(self, picked):
        if picked < 0:
            self.selected_database = None
            return

        onn_settings = sublime.load_settings('onn.sublime-settings')
        connections_list = onn_settings.get('connections')

        params = {}
        database = self.ui_connection_list[picked][0]
        self.selected_database = database

        for connection in connections_list:
            if connection.get('name') == database:
                params = connection

        self.output_text(True, "connecting to %s on %s:%s as %s" % (params.get('db'), params.get('host'), params.get('port'), params.get('user')))
        self.dbconn = connect(params.get('host'), params.get('user'), params.get('pass'), params.get('db'), params.get('port'))
        self.dbconn.cursor().execute('SET autocommit=1')
        self.view.set_name(self.build_output_view_name())

    def start_query(self, stmt):
        self.output_text(True, stmt)
        thread = QueryRunnerThread(self.dbconn, stmt, self.table_builder, self.query_completed)
        thread.start()

    def query_completed(self, excpt, text):
        self.output_text(False, text)
        if excpt == None:
            return
        error_code = excpt.args[0]
        if error_code in self.RECONNECT_MYSQL_ERRORS:
            self.dbconn = None

    def save_view(self, view, source_tab):
        self.view = view
        self.source_tab = source_tab
        self.dbconn = None

    def get_view(self):
        return self.view

    def has_view(self):
        return (not (self.view is None)) and (not (self.view.window() is None))

    def has_dbconn(self):
        return (not (self.dbconn is None))


class RunMysqlCommand(sublime_plugin.TextCommand):
    SQLSTMT_STARTS = frozenset(['select', 'update', 'delete', 'insert', 'replace', 'use', 'load', 'describe', 'desc', 'explain', 'create', 'alter', 'truncate', 'show', 'commit', 'set'])

    def __init__(self, view):
        super(RunMysqlCommand, self).__init__(view)
        self.save_output_view = None

    def run(self, edit):
        if self.save_output_view == None:
            self.save_output_view = SaveView()

        if self.view.settings().get('run_mysql_source_file') != None:
            edit = self.view.begin_edit()
            self.view.insert(edit, self.view.size(), "unable to run queries from an output view (for now)" + "\n")
            self.view.end_edit(edit)
            self.view.show(self.view.size())
            return

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

        self.ensure_output_view()

        if len(stmt) == 0:
            self.save_output_view.output_text(True, stmt + "\nunable to find statement")
            return

        if self.save_output_view.has_dbconn():
            self.save_output_view.start_query(stmt)
        else:
            self.save_output_view.pick_database()

    def has_sqlstmt_start(self, line):
        if len(line) == 0:
            return False
        if line[0].isspace():
            return False
        search_line = line.lower()
        if search_line == 'commit;':
            return True
        first_word = search_line.partition(' ')[0]
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

    def ensure_output_view(self):
        if self.save_output_view.has_view():
            return
        new_view = None
        for window in sublime.windows():
            for check_view in window.views():
                if check_view.settings().get('run_mysql_source_file') == self.current_file:
                    new_view = check_view
        if new_view is None:
            new_view = self.build_output_view()
        self.save_output_view.save_view(new_view, self.tab_name)

    def build_output_view(self):
        window = sublime.active_window()
        view = window.new_file()
        view.settings().set('run_mysql_source_file', self.current_file)
        view.settings().set('word_wrap', True)
        view.settings().set("RunInScratch", True)
        view.set_scratch(True)
        return view
