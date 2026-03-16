import os
import subprocess
import platform

# Function to execute shell commands with cross-platform support
def run_shell_command(command):
    if platform.system() == 'Windows':
        command = 'cmd.exe /c ' + command
    elif platform.system() == 'Darwin':
        # MacOS specific shell calls
        pass
    else:
        # Linux/Unix shell
        pass
    return subprocess.run(command, shell=True, capture_output=True)
