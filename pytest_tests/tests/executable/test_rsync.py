"""
Author(s): Jan Sobol <sobol@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of executable module features. Tests of Rsync module.
"""

import os
from pathlib import Path

import pytest
import pytest_cases

from lbr_testsuite.executable import Rsync, Tool
from lbr_testsuite.executable.rsync import RsyncException


TESTING_STRING_1 = "testing string first..."
TESTING_STRING_2 = "testing string second..."


@pytest.fixture
def host_workdir(executor):
    """Fixture to provide testing workdir on rsync target (host)."""

    workdir_path = "/tmp/testsuite_testing/rsync_workdir"
    Tool(f"mkdir -p {workdir_path}", executor=executor).run()
    yield workdir_path
    Tool(f"rm -rf {workdir_path}", executor=executor).run()


def create_file_on_host(executor, content, filename):
    """Create file on rsync target (host) via shell command.

    Parameters
    ----------
    executor : Executor
        Executor with context of rsync target host.
    content : str
        Content to write to file.
    filename : str or Path
        Created file name.
    """

    Tool(
        f"echo {content} > {filename}",
        executor=executor,
    ).run()


@pytest_cases.fixture
@pytest_cases.parametrize(pt=["absolute", "relative"])
def path_type(pt):
    """Parameterize tests in which relative and absolute paths are tested
    separately.
    """

    return pt


def test_rsync_push(executor, tmp_path):
    """Test of file pushing (uploading) and get_data_directory method.

    Test pushes simple text files and then verifies their content.
    Per-host and per-user session temporary data directories are tested
    by creating two instances of Rsync. Both instances must use the same
    temporary directory as they are used by same user and target host.
    """

    with open(Path(tmp_path) / "testing_file1.txt", "w", encoding="ascii") as file:
        file.write(TESTING_STRING_1)
    with open(Path(tmp_path) / "testing_file2.txt", "w", encoding="ascii") as file:
        file.write(TESTING_STRING_2)

    rsync1 = Rsync(executor)
    first_dir = rsync1.get_data_directory()
    pushed = rsync1.push_path(Path(tmp_path) / "testing_file1.txt")
    assert pushed == str(Path(first_dir) / "testing_file1.txt")
    content, _ = Tool(["cat", pushed], executor=executor).run()
    assert content.strip() == TESTING_STRING_1

    rsync2 = Rsync(executor)
    second_dir = rsync2.get_data_directory()
    assert first_dir == second_dir, "Same directory should be used for same user and host."
    pushed = rsync2.push_path(Path(tmp_path) / "testing_file2.txt")
    assert pushed == str(Path(second_dir) / "testing_file2.txt")
    content, _ = Tool(["cat", pushed], executor=executor).run()
    assert content.strip() == TESTING_STRING_2


def test_rsync_push_custom_data_dir(executor, host_workdir, tmp_path):
    """Test of file pushing (uploading) and get_data_directory method
    with custom data directory.
    """

    with open(Path(tmp_path) / "testing_file1.txt", "w", encoding="ascii") as file:
        file.write(TESTING_STRING_1)

    rsync = Rsync(executor, data_dir=host_workdir)
    assert host_workdir == rsync.get_data_directory()
    pushed = rsync.push_path(Path(tmp_path) / "testing_file1.txt")
    assert pushed == str(Path(host_workdir) / "testing_file1.txt")
    content, _ = Tool(["cat", pushed], executor=executor).run()
    assert content.strip() == TESTING_STRING_1


def test_rsync_pull(executor, tmp_path, path_type):
    """Test of file pulling (downloading).

    Text file is created by a command on host, then it is pulled and
    its content is verified. Absolute and relative paths are tested
    separately.
    """

    rsync = Rsync(executor)

    test_file = f"testing_shell_file1_{path_type}.txt"
    if path_type == "absolute":
        pull_path = Path(rsync.get_data_directory()) / test_file
    else:
        pull_path = test_file

    create_file_on_host(
        executor,
        TESTING_STRING_1 + path_type,
        Path(rsync.get_data_directory()) / test_file,
    )

    local_file = rsync.pull_path(pull_path, tmp_path)
    assert local_file == str(Path(tmp_path) / test_file)
    with open(local_file, encoding="ascii") as file:
        assert file.read().strip() == TESTING_STRING_1 + path_type


def test_rsync_pull_outside_failure(executor, host_workdir, tmp_path, path_type):
    """Test raise of exception when user try to pull file which is not
    stored in the data directory. Absolute and relative paths are tested
    separately.
    """

    rsync = Rsync(executor)

    if path_type == "absolute":
        pull_path = f"{host_workdir}/file.txt"
    else:
        # relpath is like '../testsuite_testing/rsync_workdir'
        host_workdir_relpath = os.path.relpath(host_workdir, rsync.get_data_directory())
        pull_path = f"{host_workdir_relpath}/file.txt"

    create_file_on_host(executor, TESTING_STRING_2, Path(host_workdir) / "file.txt")

    with pytest.raises(RsyncException):
        rsync.pull_path(pull_path, tmp_path)


def test_rsync_create_file(executor):
    """Test of create_file method."""

    rsync = Rsync(executor)

    newfile = rsync.create_file("testing_newfile1.txt")
    content, _ = Tool(["cat", newfile], executor=executor).run()
    assert newfile == str(Path(rsync.get_data_directory()) / "testing_newfile1.txt")
    assert content.strip() == ""


def test_rsync_remove(executor, path_type):
    """Test of remove_path method. Absolute and relative paths are
    tested separately.
    """

    rsync = Rsync(executor)

    test_file = "testing_file1.txt"
    if path_type == "absolute":
        rm_path = Path(rsync.get_data_directory()) / test_file
    else:
        rm_path = test_file

    newfile = rsync.create_file(test_file)
    Tool(["test", "-f", newfile], executor=executor).run()
    rsync.remove_path(rm_path)
    Tool(f"! test -f {newfile}", executor=executor).run()


def test_rsync_remove_outside_failure(executor, host_workdir, path_type):
    """Test raise of exception when user try to remove file which is not
    stored in the data directory. Relative path is passed to the method.
    """

    rsync = Rsync(executor)

    if path_type == "absolute":
        pull_path = f"{host_workdir}/file.txt"
    else:
        # relpath is like '../testsuite_testing/rsync_workdir'
        host_workdir_relpath = os.path.relpath(host_workdir, rsync.get_data_directory())
        pull_path = f"{host_workdir_relpath}/file.txt"

    create_file_on_host(executor, TESTING_STRING_2, Path(host_workdir) / "file.txt")

    with pytest.raises(RsyncException):
        rsync.remove_path(pull_path)


def test_rsync_wipe_data_directory(executor):
    """Test of wipe_data_directory method."""

    rsync = Rsync(executor)

    newfile1 = rsync.create_file("testing_file1.txt")
    Tool(["test", "-f", newfile1], executor=executor).run()
    newfile2 = rsync.create_file("testing_file2.txt")
    Tool(["test", "-f", newfile2], executor=executor).run()
    newdir = Path(rsync.get_data_directory()) / "testing_folder"
    Tool(["mkdir", str(newdir)], executor=executor).run()
    Tool(["test", "-d", str(newdir)], executor=executor).run()
    rsync.wipe_data_directory()

    Tool(f'test -z "$(ls -A {rsync.get_data_directory()})"', executor=executor).run()
