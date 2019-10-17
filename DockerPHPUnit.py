import os
import sys
import shlex
import subprocess
import sublime
import sublime_plugin

if sys.version_info < (3, 3):
    raise RuntimeError('DockerPHPUnit works with Sublime Text 3 only')

SPU_THEME = 'Packages/DockerPHPUnit/DockerPHPUnit.hidden-tmTheme'
SPU_SYNTAX = 'Packages/DockerPHPUnit/DockerPHPUnit.hidden-tmLanguage'

class ShowInPanel:
    def __init__(self, window):
        self.window = window

    def display_results(self):
        self.panel = self.window.get_output_panel("exec")
        self.window.run_command("show_panel", {"panel": "output.exec"})

        self.panel.settings().set("color_scheme", SPU_THEME)
        self.panel.set_syntax_file(SPU_SYNTAX)

class DockerPhpUnitCommand(sublime_plugin.WindowCommand):
    def __init__(self, *args, **kwargs):
        super(DockerPhpUnitCommand, self).__init__(*args, **kwargs)
        self.settings         = sublime.load_settings('DockerPHPUnit.sublime-settings')
        self.phpunit_path               = self.settings.get('phpunit_path')
        self.phpunit_xml_remote_path    = self.settings.get('phpunit_xml_remote_path')
        self.phpunit_xml_local_path     = self.settings.get('phpunit_xml_local_path')
        self.docker_container           = self.settings.get('docker_container')

        if (str(self.phpunit_path) == ""):
            sublime.status_message("You have to set the phpunit_path in the DockerPHPUnit configuration")


    def run(self, *args, **kwargs):
        try:
            # The first folder needs to be the Laravel Project
            self.PROJECT_PATH = self.window.folders()[0] + "/"

            if self.phpunit_xml_local_path:
                self.CONFIG_PATH = self.PROJECT_PATH + self.phpunit_xml_local_path
            else:
                self.CONFIG_PATH = self.PROJECT_PATH

            sublime.status_message(self.CONFIG_PATH)
            if os.path.isfile("%s" % os.path.join(self.CONFIG_PATH, 'phpunit.xml')) or os.path.isfile("%s" % os.path.join(self.CONFIG_PATH, 'phpunit.xml.dist')):
                self.params = kwargs.get('params', False)
                self.type = kwargs.get('type', False)
                self.group = ""
                self.filename = ""
                self.current_function = ""

                if self.type == "unit":
                    self.group = " --exclude-group functional_test"
                elif self.type == "functional":
                    self.filename = self.file_name()

                    if not os.path.isfile(self.filename):
                        sublime.status_message("file " + self.filename + " not found")
                        return False
                    else:
                        self.filename = self.filename[len(self.PROJECT_PATH):]

                    self.current_function = self.get_current_function(self.window.active_view())
                    sys.stderr.write("PROJECT_PATH: %s \n" % self.current_function)

                elif self.type == "current_file":
                    self.filename = self.file_name()

                    if not os.path.isfile(self.filename):
                        sublime.status_message("file " + self.filename + " not found")
                        return False
                    else:
                        self.filename = self.filename[len(self.PROJECT_PATH):]
                self.on_done()
            else:
                sublime.status_message("phpunit.xml or phpunit.xml.dist not found")
        except IndexError:
            sublime.status_message("Please open a project with PHPUnit")

    def file_name(self):
        return self.window.active_view().file_name()

    def on_done(self):
        try:
            self.run_shell_command(self.PROJECT_PATH)
        except IOError:
            sublime.status_message('IOError - command aborted')

    def run_shell_command(self, working_dir):
            self.window.run_command("exec", {
                "cmd": self.build_command(),
                "shell": True,
                "working_dir": working_dir
            })
            self.display_results()
            return True

    def build_command(self):
        command = "docker exec %s sh -c \"%s -c %s\"" % (self.docker_container, self.phpunit_path, self.phpunit_xml_remote_path)
        if self.filename:
            command = "docker exec %s sh -c \"%s -c %s %s\"" % (self.docker_container, self.phpunit_path, self.phpunit_xml_remote_path, self.filename)
        if self.current_function:
            command = "docker exec %s sh -c \"%s -c %s --filter %s %s\"" % (self.docker_container, self.phpunit_path, self.phpunit_xml_remote_path, self.current_function, self.filename)
        return command;

    def display_results(self):
        display = ShowInPanel(self.window)
        display.display_results()

    def window(self):
        return self.view.window()

    def get_current_function(self, view):
        sel = view.sel()[0]
        function_regions = view.find_by_selector('entity.name.function')
        cf = None
        for r in reversed(function_regions):
            if r.a < sel.a:
                cf = view.substr(r)
                break
        return cf