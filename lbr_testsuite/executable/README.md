# Module executable

Module contains components for executing commands and operations related to command execution.

Main highlights of this module are:
 - Execute **blocking** or **asynchronous** commands.
 - Execute commands on **local** or **remote** machine.
 - Query command return code, output, status (is running? etc.).
 - Set output, env, failure handling.
 - Simple API for working with **systemd** services\*.
 - Special class for coredump handling\*.
 - Special class for [strace](https://strace.io/)\* (linux syscall tracer).
 - Special class for **file synchronization** (works on local and remote machine, removes
   need for branching (eg. `if local ... else ...`)).

\* Local only.

### Executable details

User has access to [3 main classes](./executable.py) to choose which class is best suited for given task:

 - `Tool` is used for simple command execution. It always waits for command to finish and checks return code.
 - `Daemon` is intended for commands that run on background, eg. some daemons\*. It doesn't wait for command
    to finish. User must manage/query command status on his own. It's expected that command keeps running
    until it is explicitly terminated.

    \*Despite the name, it currently doesn't support processes that fork where original process
    terminates (like typical Unix daemon). Process should run in foreground so that it can receive
    signals and inputs from terminal.
 - `AsyncTool` is "one-shot" execution similar `Tool`, but it's asynchronous like `Daemon`. One of it's features
    is that it allows user to continuously read stdout/stderr while process is running.

There are also additional classes built on top of main classes. They have specific uses cases:

 - [Service](./service.py) is used for systemd services. User can stop/(re)start/reload service and query
   its status. Usable only in local execution.
 - [Rsync](./rsync.py) is used for file synchronization. Works on local and remote machines. User can
   pull (download), push (upload) files or directories from/to special directory on target machine.
   Additional operations include file creation and file/directory deletion. On local machine
   this is transformed to copying files or directories between directories.

Execution on local machine is implemented by standard [subprocess](https://docs.python.org/3.8/library/subprocess.html)
module. Execution on remote machine is implemented with [fabric](https://www.fabfile.org/) library.
Both local and remote execution has its quirks. Despite our effort to make local/remote
work transparent to user, not all methods or parameters behave identically. Known differences
are described as following:

 - Remote variant can't start with empty environment. Updates to env are [additive](https://docs.paramiko.org/en/3.3/api/channel.html#paramiko.channel.Channel.update_environment).
 - Remote variant doesn't support separate stdout and stderr. They are **mixed in stdout** by default (outputs are
   mixed also in local execution for consistency, but user can separate them if needed).
 - Remote variant doesn't support coredump/strace.
 - Remote variant does not report correct return code when process is killed by signal (default RC -1 is returned, no
   matter what signal terminated the process). Currently there is no straightforward way to retrieve the signal.
 - Remote variant generally converts to `sh -c cmd`. In specific cases this differs from `cmd`.
   User logged into remote host might have special permission to `cmd`, but might not have same
   permission to `sh` (also true under sudo).

#### Failure verbosity

Executable checks return code of process by default. User can choose how failure will be handled.
There are four levels to choose from:
 - *normal*: fails in a normal way. An error message is printed and an exception is raised when an executable fails.
 - *no-error*: does not producean  error message (it's printed in debug level). Rest is as same as on 'normal' level.
 - *no-exception*: does not raise an exception on executable failure. Rest is as same as on 'no-error' level.
 - *silent*: a failure does not provide any output nor raises an exception.

### Remote work

When using remote execution, user must provide data for **SSH authentication** on remote machine.
Ideal case would be to have [SSH agent enabled](https://unix.stackexchange.com/a/72558).
In such case user doesn't have to provide anything, unless he wants to login with different username.

Other supported methods are via password or private key. Password is set in form of a string.
Key must not be encrypted. In other words, key must be without password.
Module currently doesn't support advanced security features like reading password from file
or accepting encrypted key (as you need to provide password for encrypted key, you're back to
dealing with password). As mentioned, recommended solution is to use SSH agent.

Current user's username is used by default to login into remote machine. This is true even when
Python is run under root/sudo. Reason is that SSH login as root is not recommended and disabled
by default on some systems.

When creating new instance of executable (or Rsync) class, user can provide **executor**. It is the
main component responsible for executing commands. Currently, there are implementations for
[local](./local_executor.py) and [remote](./remote_executor.py) executors. Local executor is used
by default. In order to use remote execution, user must create remote executor object and pass it
to executable during initialization. Remote executor accepts data for SSH authentication described above.
One remote executor can be used by multiple executables in sequence. Given that it stores process
context, it **cannot be used in parallel**. If user needs parallel remote execution, multiple executors must
be used.

### Examples of usage

##### Tool

```python
from lbr_testsuite.executable import Tool

# Simple printf command.
cmd = Tool(["printf", "Hello"])
stdout, _ = cmd.run()
assert stdout == "Hello"
assert cmd.returncode() == 0

# Allow non-zero return codes.
Tool("exit 1", failure_verbosity="no-exception").run()

# Launch command in environment with only a single variable.
cmd = Tool(["printenv", "-0"])
cmd.set_env(dict(TEST_TOOL_ENV_VAR="X"))
cmd.run()
# Stdout: 'TEST_TOOL_ENV_VAR=X\x00'

# Usage of sudo.
cmd = Tool(["whoami"], sudo=True)
cmd.run()
# Stdout: 'root\n'

# Output stdout to file "a.txt".
cmd = Tool("echo 'a'")
cmd.set_outputs(stdout="a.txt")
cmd.run()
# Stdout: empty as it was written to the file

# Output stderr to file "b.txt".
cmd = Tool(">&2 echo 'b'")
cmd.set_outputs(stdout="not_used.txt", stderr="b.txt")
cmd.run()
# Stdout/err: empty as it was written to the file


# Appending arguments.
cmd = Tool(["echo"])
cmd.append_arguments("Hello")
cmd.append_arguments("World")
cmd.run()
# Stdout: 'Hello World\n'
```

For more examples see [Tool pytests](../../pytest_tests/tests/executable/test_tool.py).

##### Daemon

```python
from lbr_testsuite.executable import Daemon

cmd = Daemon("httpd -k start -DFOREGROUND -e 'debug'")
cmd.start()
assert cmd.is_running()

time.sleep(10)
stdout, _ = cmd.stop()

assert not cmd.is_running()
```

For more examples see [Daemon pytests](../../pytest_tests/tests/executable/test_tool.py).

##### AsyncTool

```python
from lbr_testsuite.executable import AsyncTool

cmd = AsyncTool("""sh -c 'for i in {1..15}; do echo -e "A"; sleep 1; done'""")
cmd.run()

# Continously read output
for idx, newline in enumerate(cmd.stdout):
    print(newline)
    if idx >= 10:
        break

# Returns rest of output after process finishes
cmd.wait_or_kill()
```

For more examples see [AsyncTool pytests](../../pytest_tests/tests/executable/test_async_tool.py).

##### Service (systemd)

```python
from lbr_testsuite.executable import Service

srv = Service("httpd")
srv.start()
assert srv.is_active()

srv.stop()
srv.returncode()

srv.restart()
assert srv.is_active()
srv.stop()
assert not srv.is_active()
```

For more examples see [Service pytests](../../pytest_tests/tests/executable/service.py).

##### Rsync

```python
from lbr_testsuite.executable import Rsync, Tool

local_rsync = Rsync()


pushed_file = local_rsync.push_path("my_dir/file.txt")
Tool(f'cat {pushed_file}').run()

pulled_file = local_rsync.pull_path("different_file.txt")
Tool(f'cat {pulled_file}').run()
```

For more examples see [Rsync pytests](../../pytest_tests/tests/executable/test_rsync.py).


##### Remote alternatives

```python
from lbr_testsuite.executable import RemoteExecutor, Tool

# Assume SSH agent
re1 = RemoteExecutor("example.com")

# Use password
re2 = RemoteExecutor("example.com", password="hacked")

# Use key
re2 = RemoteExecutor("example.com", username="user", key_filename="./path_to_not_encrypted_key")


# Use executor in executables to execute command on remote machine
cmd = Tool(f'printf "Hello"', executor=re1)
cmd.run()
```

##### Remote Rsync

```python
from lbr_testsuite.executable import RemoteExecutor, Tool

re = RemoteExecutor("example.com")

remote_rsync = Rsync(executor=re)

pushed_file = remote_rsync.push_path("my_dir/file.txt")
Tool(f'cat {pushed_file}', executor=re1).run()

pulled_file = remote_rsync.pull_path("different_file.txt")
Tool(f'cat {pulled_file}').run()  # No explicit executor = use local executor
```
