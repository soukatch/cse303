"""
    Module: cse303

    Purpose: This module holds common class definitions and common functions, so
             that we can easily create scripts for testing the functionality of
             the server and client in the CSE 303 assignments.
"""

import subprocess
import os
import time
import filecmp
import sys
import shutil

indentation = 75
"""width of the message content in a line"""

verbose = False
"""print verbose output (e.g., shell commands)?"""

class UserConfig:
    """An object that encapsulates a username and password, for convenience in the scripts"""

    def __init__(self, name, pwd):
        """Construct a UserConfig object from a name and password"""
        self.name = name
        self.pwd = pwd

class ServerConfig:
    """An object that encapsulates the server's configuration, and makes it easy to launch a server."""

    def __init__(self, exe, port, keyfile, dirfile, threads = "1", buckets = "16", qinterval = "60", upquot = "1048576", downquot = "1048576", reqquot = "128", top = "4", admin = "alice"):
        """Construct a ServerConfig object from an executable, port, keyfile, directory file, thread count, quota interval, u/d/r quotas, and TOP threshold"""
        self.exe = exe
        self.port = port
        self.keyfile = keyfile
        self.dirfile = dirfile
        self.threads = threads
        self.buckets = buckets
        self.qi = qinterval
        self.upq = upquot
        self.dnq = downquot
        self.rqq = reqquot
        self.top = top
        self.admin = admin

    def launchcmd(self):
        """Return, in list form, the parts of a command to start the server"""
        return [self.exe, "-p", self.port, "-k", self.keyfile, "-f", self.dirfile, "-t", self.threads, "-b", self.buckets, "-i", self.qi, "-u", self.upq, "-d", self.dnq, "-r", self.rqq, "-o", self.top, "-a", self.admin]

class ClientConfig:
    """An object that encapsulates the client's configuration, and makes it easy to invoke clients that execute a single command."""

    def __init__(self, exe, server, port, keyfile):
        """Construct a ClientConfig object from an executable, server name/address, port, and keyfile"""
        self.exe = exe
        self.server = server
        self.port = port
        self.keyfile = keyfile

    def cmd0(self, user, cmd):
        """Configure the common parts of a 0-argument command"""
        return [self.exe, "-k", self.keyfile, "-s", self.server, "-p", self.port, "-u", user.name, "-w", user.pwd, "-C", cmd]

    def cmd1(self, user, cmd, param1):
        """Configure the common parts of a 1-argument command"""
        return [self.exe, "-k", self.keyfile, "-s", self.server, "-p", self.port, "-u", user.name, "-w", user.pwd, "-C", cmd, "-1", param1]

    def cmd2(self, user, cmd, param1, param2 ):
        """Configure the common parts of a 2-argument command"""
        return [self.exe, "-k", self.keyfile, "-s", self.server, "-p", self.port, "-u", user.name, "-w", user.pwd, "-C", cmd, "-1", param1, "-2", param2]

    def reg(self, user):
        """Configure a command for registering a user"""
        return self.cmd0(user, "REGISTER")

    def bye(self, user):
        """Configure a command for stopping the server"""
        return self.cmd0(user, "EXIT____")

    def setC(self, user, filename):
        """Configure a command for setting a user's content"""
        return self.cmd1(user, "SETPFILE", filename)

    def getC(self, user, filename):
        """Configure a command for getting a user's content"""
        return self.cmd1(user, "GETPFILE", filename)

    def getA(self, user, filename):
        """Configure a command for getting all users"""
        return self.cmd1(user, "ALLUSERS", filename)

    def kvI(self, user, key, valfile):
        """Configure a command for inserting a key/value pair"""
        return self.cmd2(user, "KVINSERT", key, valfile)

    def kvU(self, user, key, valfile):
        """Configure a command for upserting a key/value pair"""
        return self.cmd2(user, "KVUPDATE", key, valfile)

    def kvG(self, user, key):
        """Configure a command for getting a value"""
        return self.cmd1(user, "KVGETONE", key)

    def kvD(self, user, key):
        """Configure a command for deleting a key"""
        return self.cmd1(user, "KVDELETE", key)

    def kvA(self, user, filename):
        """Configure a command for getting all keys"""
        return self.cmd1(user, "KVGETALL", filename)

    def kvT(self, user, filename):
        """Configure a command for getting top keys"""
        return self.cmd1(user, "TOP_KEYS", filename)

    def kvF(self, user, name, filename):
        """Configure a command for registering a .so"""
        return self.cmd2(user, "REG_MR__", name, filename)

    def kMR(self, user, name, filename):
        """Configure a command for invoking a map/reduce on the server"""
        return self.cmd2(user, "MAP__RED", name, filename)

    def persist(self, user):
        """Configure a command for persisting the server"""
        return self.cmd0(user, "PERSIST_")

def delfile(file):
    """delete a file, but only if it exists"""
    if os.path.exists(file):
        os.remove(file)

def copyfile(source, destination):
    """Copy a file"""
    shutil.copyfile(source, destination)

def copyexefile(source, destination):
    """Copy a file and make it executable"""
    shutil.copyfile(source, destination)
    st = os.stat(destination)
    os.chmod(destination, st.st_mode | 0o111)

def killall(procname):
    """Invoke the 'killall' command to kill instances of a process"""
    # To avoid error messages, we use Popen, then read from stdout and stderr so
    # that we block until the process completes
    s = subprocess.Popen(["killall", procname], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    s.stderr.readline()
    s.stdout.readline()

def green(txt):
    """wrap /txt/ in ASCII codes for making it green"""
    green = '\033[32m'
    reset = '\033[0m'
    return green+txt+reset

def red(txt):
    """wrap /txt/ in ASCII codes for making it red"""
    red = '\033[31m'
    reset = '\033[0m'
    return red+txt+reset

def waitfor(secs):
    """wait for /secs/ seconds"""
    time.sleep(secs)

def do_cmd(msg, expect, cmd, server):
    """Launch /cmd/ in a subprocess, and then check if its result equals the expected value"""
    if verbose:
        for x in cmd:
            print(x, end=" ")
        print("", end="\n")
    print((msg+" Expect: '" + expect+"'").ljust(indentation), end="")
    s = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    res_o = s.stdout.readline().rstrip().decode("utf-8")
    if res_o == expect:
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR")+"] '" + str(res_o) + "'")
    after(server.pid)
    return s

def await_server(msg, expect, server):
    """Wait for server to terminate"""
    after(server.pid)
    print((msg+" Expect: '" + expect+"'").ljust(indentation), end="")
    res = server.pid.stdout.readline().rstrip().decode("utf-8")
    if res == expect:
        print("[" + green("OK") + "]")
    else:
        print("[" + red("ERR")+"] '" + res + "'")

def clean_common_files(server, client):
    """ Delete any of the files that we would expect the client or server to have made during an interrupted run of the tests"""
    print("Cleaning up temp files".ljust(indentation), end="")
    files = [server.keyfile+".pri", server.keyfile + ".pub", server.dirfile, client.keyfile]
    for f in files:
        delfile(f)
    print("["+green("OK")+"]")

def check_file_result(f1, f2):
    """Check if f1 and f2 match, and then delete f2"""
    print(("  Comparing"+" "+f1+" and "+f2 + ".file.dat"+".").ljust(indentation), end="")
    if not os.path.exists(f2+".file.dat"):
        print("["+red("ERR")+"] Cannot find " + f2 + ".file.dat")
        return
    if filecmp.cmp(f1, f2+".file.dat"):
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR")+"] Files do not match")
    delfile(f2+".file.dat")

def check_file_list(file, list):
    """Check if the file has the same contents (newline-delimited, sorted) as the list, then delete the file"""
    # read the file, strip newlines, sort the file
    f = open(file)
    lines1 = f.readlines()
    f.close()
    lines2 = []
    for x in lines1:
        lines2.append(x.strip())
    lines2.sort()
    # sort the list, so we can use == to compare
    list.sort()
    print(("Checking"+" "+file+".").ljust(indentation), end="")
    if lines2 == list:
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR")+"] Files do not have correct contents")
        print("file:")
        for x in lines2:
            print(x)
        print("list:")
        for x in list:
            print(x)
    # delete when done
    delfile(file)

def check_file_list_nosort(file, list):
    """Check if the file has the same contents (newline-delimited) as the list, then delete the file"""
    # read the file, strip newlines
    f = open(file)
    lines1 = f.readlines()
    f.close()
    lines2 = []
    for x in lines1:
        lines2.append(x.strip())
    print(("Checking"+" "+file+".").ljust(indentation), end="")
    if lines2 == list:
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR")+"] Files do not have correct contents")
        print("file:")
        for x in lines2:
            print(x)
        print("list:")
        for x in list:
            print(x)
    # delete when done
    delfile(file)

def line():
    """Print a line of dashes, to help with separating output"""
    for i in range(1, indentation + 5):
        print("-", end="")
    print()

def check_args_verbose():
    """Check the command line arguments to see if there is a VERBOSE flag"""
    for arg in sys.argv:
        if arg == "VERBOSE":
            return True
    return False

def check_args_server():
    """Check the command line arguments to see if there is a SERVER flag"""
    for arg in sys.argv:
        if arg == "SERVER":
            return True
    return False

def check_args_client():
    """Check the command line arguments to see if there is a CLIENT flag"""
    for arg in sys.argv:
        if arg == "CLIENT":
            return True
    return False

def get_len(filename):
    """Get the length of a file"""
    return os.stat(filename).st_size

def verify_filesize(filename, expect):
    """Compare a file's size to an expected value"""
    s = get_len(filename)
    print(("Checking size of " + filename + " (expect " + str(expect) + ")").ljust(indentation), end="")
    if (s == expect):
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR: " + str(s))+"]")

def verify_peek(filename, offset, len, val):
    """Check if a value can be found at a specific location in a file"""
    msg = "Checking position " + str(offset) + " of " + filename + " for '" + val + "'"
    leftmsg(msg)
    f = open(filename, "rb")
    f.seek(offset, 0)
    found = f.read(len).decode("ascii")
    if (val == found):
        okmsg()
    else:
        print("["+red("ERR: " + found)+"]")
    f.close()

def build_file(filename, size):
    """Create a file named 'filename' that consists of 'size' bytes"""
    f = open(filename, "w")
    for i in range(0, size):
        f.write(".")
    f.close()

def build_file_as(filename, contents):
    """Create a file named 'filename' that consists of the given string"""
    f = open(filename, "w")
    f.write(contents)
    f.close()

def override_exe(server, client):
    """Change the server or client executable to the solution executable"""
    if check_args_server():
        server.exe = "solutions/server.exe"
    if check_args_client():
        client.exe = "solutions/client.exe"

def makeclean():
    """Clean out the build folder"""
    print("Running 'make clean'".ljust(indentation), end="")
    process = subprocess.run(["make", "clean"], capture_output=True)
    print("["+green("OK")+"]")

def build(makefiles):
    """Build using all provided makefiles"""
    print("Building executables:")
    for file in makefiles:
        print("  " + file, end="", flush=True)
        process = subprocess.run(["make", "-j", "-f", file], capture_output=True)
        print("".ljust(indentation-len(file)-2), end="", flush=True)
        if process.returncode == 0:
            print("["+green("OK")+"]")
        else:
            print("["+red("ERROR")+"]")

def check_exist(file, val):
    """Report if a file's existence matches expectation"""
    msg = "Ensuring " + file
    if val:
        msg += " exists"
    else:
        msg += " does not exist"
    print(msg.ljust(indentation), end="")
    if os.path.exists(file) == val:
        print("["+green("OK")+"]")
    else:
        print("["+red("ERR")+"]")

def after(proc):
    """Clean up the server's stdout by reading the two lines we expect after every connection"""
    line = proc.stdout.readline().rstrip().decode("utf-8")
    if line != "Waiting for a client to connect...":
        print("  Unexpected server output: "+line)
    line = proc.stdout.readline().rstrip().decode("utf-8")
    if (line != "Connected to 127.0.0.1") & (line != "Connected to 0.0.0.0"):
        print("  Unexpected server output: "+line)

def killprocs():
    """Kill any server.exe or client.exe executables"""
    print("Stopping any errant processes".ljust(indentation), end="")
    killall("server.exe")
    killall("client.exe")
    print("["+green("OK")+"]")

def leftmsg(msg):
    """Print a left-justified message"""
    print(msg.ljust(indentation), end="")

def okmsg():
    """Print [OK]"""
    print("["+green("OK")+"]")

def do_cmd_a(msg, expects, cmd):
    """Launch /cmd/ in a subprocess, and then check if its results equal the expected values"""
    if verbose:
        for x in cmd:
            print(x, end=" ")
        print("", end="\n")
    print(msg)
    s = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    for e in expects:
        res_o = s.stdout.readline().rstrip().decode("utf-8")
        print(("  Expect '" + e + "'").ljust(indentation), end="")
        if res_o == e:
            print("["+green("OK")+"]")
        else:
            print("["+red("ERR")+"] '" + str(res_o) + "'")
    return s

def next8(num):
    """Raise the value of num to the next multiple of 8"""
    ret = num
    if ret % 8 != 0:
        ret = ret + (8 - ret % 8)
    return ret
