#!/usr/bin/env python3

# TODO:
# * Error handling
# * Log all commands into workspace
# * De-couple WorkSpace from GitRepos
# * Write unit tests
# * Handle corrupt dependencies.json
# * Handle exceptional conditions
# * Use a real logger
# * Handle partial sha1s correctly

import subprocess
import sys
import shutil
import os
from .witlogger import getLogger
from .workspace import WorkSpace, PackageNotInWorkspaceError
from .dependency import parse_dependency_tag
from .dependency import Dependency
from .inspect import inspect_tree
from pathlib import Path
from typing import cast, List, Tuple  # noqa: F401
from .common import error, WitUserError, print_errors
from .env import git_reference_workspace
from .gitrepo import GitRepo, GitCommitNotFound
from .manifest import Manifest
from .package import WitBug
from .parser import parser, add_dep_parser
from .version import __version__
from argparse import Namespace
import re
import json
import logging
log = getLogger()


class NotAPackageError(WitUserError):
    pass
class NoSuchMethod(Exception):
  def __init__(self, command):
    self.command = command
  def __str__(self) -> str:
      return f"No such Method as {self.command}"

def get_command(command):
  command = command.replace("-","_")
  if hasattr(sys.modules[__name__], command):
    return getattr(sys.modules[__name__], command.replace("-","_"))
  else:
      return test_command
    # raise NoSuchMethod(command)

def test_command(orgWs, args):
    orignalLevel = log.getLevelName()
    log.setLevel(logging.CRITICAL)
    subprocess.run(["rm", "-rf", ".temp"], stdout=subprocess.DEVNULL)
    ws = WorkSpace.create(".temp", parse_repo_path(args), args.jobs)
    dependencies = [] if args.source_pkg is None else args.source_pkg
    names = [ each.split("/")[-1].replace(".git","") for (each, _) in dependencies]
    print(names)
    for dep in dependencies:
        print(dep)
        ws.add_dependency(dep)
        # print(dep)
    print(ws)
    log.setLevel(orignalLevel)
    packages, errors = ws.resolve(download=True)
    if len(errors) != 0:
        print_errors(errors)
        sys.exit(1)
    argsDict = vars(args)

    cwd = Path(os.getcwd()).resolve()
    manifest_path = cwd/GitRepo.PKG_DEPENDENCY_FILE
    print(manifest_path)
    if manifest_path.exists():
        manifest = Manifest.read_manifest(manifest_path)
    else:
        manifest = Manifest([])

    # make sure the dependency is not already in the cwd's manifest


    for (key, value) in packages.items():
        if key in names and not args.include_repo:
            continue
        argsDict["pkg"] = (value.source, value.revision)
        argsDict["message"] = None
        namespace = Namespace(**argsDict)
        print(manifest.contains_dependency(key))
        if manifest.contains_dependency(key):
            update_dep(orgWs, namespace)
        else:
            # print(key)
            add_dep(orgWs, namespace)
        # add_dep(orgWs, (value.source, value.revision), args.target_package, args.overwrite)
    # print(args)
# def add_dep_import(ws, args, td, overwrite):
#     # print(args)
#     """ Resolve a Dependency then add it to the cwd's wit-manifest.json """
#     packages = {pkg.name: pkg for pkg in ws.lock.packages}
#     req_dep = dependency_from_tag(ws.root, args)

#     cwd = Path(os.path.join(os.getcwd(),  td)).resolve()
#     if cwd == ws.root:
#         error("add-dep must be run inside of a package, not the workspace root.\n\n" +
#               add_dep_parser.format_help())
#     cwd_dirname = cwd.relative_to(ws.root).parts[0]
#     if not ws.lock.contains_package(cwd_dirname):
#         raise NotAPackageError(
#             "'{}' is not a package in workspace at '{}'".format(cwd_dirname, ws.path))

#     # in order to resolve the revision, we need to bind
#     # the req_dep to disk, cloning into .wit if neccesary
#     req_dep.load(packages, ws.repo_paths, ws.root, True)
#     try:
#         req_dep.package.revision = req_dep.resolved_rev()
#     except GitCommitNotFound:
#         raise WitUserError("Could not find commit or reference '{}' in '{}'"
#                            "".format(req_dep.specified_revision, req_dep.name))

#     check_submodule_only(cwd)

#     manifest_path = cwd/GitRepo.PKG_DEPENDENCY_FILE
#     if manifest_path.exists():
#         manifest = Manifest.read_manifest(manifest_path)
#     else:
#         manifest = Manifest([])

#     # make sure the dependency is not already in the cwd's manifest
#     if manifest.contains_dependency(req_dep.name):
#         if not overwrite:
#             log.error("'{}' already depends on '{}'".format(cwd_dirname, req_dep.name))
#             sys.exit(1)
#         else:

#     manifest.add_dependency(req_dep)
#     manifest.write(manifest_path)

#     log.info("'{}' now depends on '{}'".format(cwd_dirname, req_dep.package.id()))


# def update_dep(ws, args) -> None:
#     packages = {pkg.name: pkg for pkg in ws.lock.packages}
#     req_dep = dependency_from_tag(ws.root, args.pkg, message=args.message)

#     cwd = Path(os.getcwd()).resolve()

#     if cwd == ws.root:
#         error("update-dep must be run inside of a package, not the workspace root.\n"
#               "  A dependency is updated in the package determined by the current working "
#               "directory,\n  which can also be set by -C.")

#     cwd_dirname = cwd.relative_to(ws.root).parts[0]

#     check_submodule_only(cwd)
#     manifest = Manifest.read_manifest(cwd/GitRepo.PKG_DEPENDENCY_FILE)

#     # make sure the package is already in the cwd's manifest
#     if not manifest.contains_dependency(req_dep.name):
#         log.error("'{}' does not depend on '{}'".format(cwd_dirname, req_dep.name))
#         sys.exit(1)

#     req_dep.load(packages, ws.repo_paths, ws.root, True)
#     req_pkg = req_dep.package
#     try:
#         req_pkg.revision = req_dep.resolved_rev()
#     except GitCommitNotFound:
#         raise WitUserError("Could not find commit or reference '{}' in '{}'"
#                            "".format(req_dep.specified_revision, req_dep.name))

#     # check if the requested repo is missing from disk
#     if req_pkg.repo is None:
#         msg = "'{}' not found in workspace. Have you run 'wit update'?".format(req_dep.name)
#         raise PackageNotInWorkspaceError(msg)

#     log.info("Updating to {}".format(req_dep.resolved_rev()))
#     manifest.replace_dependency(req_dep)
#     manifest.write(cwd/GitRepo.PKG_DEPENDENCY_FILE)

#     log.info("'{}' now depends on '{}'".format(cwd_dirname, req_pkg.id()))


def main() -> None:

    if git_reference_workspace and not Path(git_reference_workspace).is_absolute():
        log.error("Environment variable $WIT_WORKSPACE_REFERENCE contains a relative path: "
                  "'{}'. Please use an absolute path.".format(git_reference_workspace))
        sys.exit(1)

    args = parser.parse_args()
    if args.verbose >= 4:
        log.setLevel('SPAM')
    elif args.verbose == 3:
        log.setLevel('TRACE')
    elif args.verbose == 2:
        log.setLevel('DEBUG')
    elif args.verbose == 1:
        log.setLevel('VERBOSE')
    else:
        log.setLevel('INFO')

    log.debug("Log level: {}".format(log.getLevelName()))

    if args.prepend_repo_path and args.repo_path:
        args.repo_path = " ".join([args.prepend_repo_path, args.repo_path])
    elif args.prepend_repo_path:
        args.repo_path = args.prepend_repo_path

    if args.version:
        version()
        sys.exit(0)

    try:
        lst_workspace_not_needed = ["init", "restore"]
        if args.command in lst_workspace_not_needed:
          get_command(args.command)(args)
        else:
            try:
                ws = WorkSpace.find(Path.cwd(), parse_repo_path(args), args.jobs)
            except FileNotFoundError as e:
                log.error("Unable to find workspace root [{}]. Cannot continue.".format(e))
                sys.exit(1)
            get_command(args.command)(ws, args)

    except WitUserError as e:
        error(e)
    except AssertionError as e:
        raise WitBug(e)


def foreach(ws, args):
    has_fail = False
    for pkg in ws.lock.packages:
        env = os.environ.copy()
        env["WIT_REPO_NAME"] = pkg.name
        env["WIT_REPO_PATH"] = str(ws.root / pkg.name)
        env["WIT_LOCK_SOURCE"] = pkg.source
        env["WIT_LOCK_COMMIT"] = pkg.revision
        env["WIT_WORKSPACE"] = str(ws.root)

        log.info("Entering '{}'".format(pkg.name))

        location = str(ws.root / pkg.name)
        command = [args.cmd] + args.args
        proc = subprocess.run(command, env=env, cwd=location, universal_newlines=True)

        if proc.returncode != 0:
            has_fail = True
            log.error("Command '{}' in '{}' failed with exitcode: {}"
                      .format(command, location, proc.returncode))
            if not args.continue_on_fail:
                sys.exit(proc.returncode)

    if has_fail:
        sys.exit(1)


def parse_repo_path(args):
    return args.repo_path.split(' ') if args.repo_path else []


def init(args) -> None:
    if args.add_pkg is None:
        dependencies = []  # type: List[Tuple[str, str]]
    else:
        dependencies = args.add_pkg

    ws = WorkSpace.create(args.workspace_name, parse_repo_path(args), args.jobs)
    for dep in dependencies:
        ws.add_dependency(dep)

    if args.update:
        update(ws, args)


# A user can restore a workspace in the current directory, or in a new directory.
# A wit-lock.json and wit-workspace.json needs to be found either in the current directory
# or separately specified by arguments.
def restore(args) -> None:
    current_dir = Path.cwd()
    lock_dir = current_dir
    dest_ws = current_dir

    if args.workspace_name:
        dest_ws = current_dir / args.workspace_name
        if dest_ws.exists():
            log.error("New workspace directory [{}] already exists.".format(str(dest_ws)))
            sys.exit(1)
        else:
            log.info("Creating new workspace [{}]".format(str(dest_ws)))
            dest_ws.mkdir()

    dotwit = dest_ws/'.wit'
    if dotwit.exists():
        log.error("Directory [{}] is already a workspace, contains a .wit directory."
                  .format(str(dest_ws)))
        sys.exit(1)
    dotwit.mkdir()

    if args.from_workspace:
        lock_dir = Path(args.from_workspace)

    ws = 'wit-workspace.json'
    lock = 'wit-lock.json'
    if not (lock_dir/lock).exists():
        log.error("Could not find {}".format(str(lock_dir/lock)))
        sys.exit(1)
    if not (lock_dir/ws).exists():
        log.error("Could not find {}".format(str(lock_dir/ws)))
        sys.exit(1)

    if args.from_workspace or args.workspace_name:
        shutil.copy(str(lock_dir/ws), str(dest_ws/ws))
        shutil.copy(str(lock_dir/lock), str(dest_ws/lock))

    WorkSpace.restore(dest_ws)

def inspect(ws, args) -> None:
    if args.dot or args.tree:
        inspect_tree(ws, args)
    else:
        log.error('`wit inspect` must be run with a flag')
        print(parser.parse_args('inspect -h'.split()))
        sys.exit(1)
def add_pkg(ws, args) -> None:
    log.info("Adding package to workspace")
    ws.add_dependency(args.repo)


def update_pkg(ws, args) -> None:
    ws.update_dependency(args.repo)


def dependency_from_tag(wsroot, tag, message=None):
    source, revision = tag

    dotwit = wsroot / ".wit"
    if (wsroot/source).exists() and (wsroot/source).parent == wsroot:
        repo = GitRepo((wsroot/source).name, wsroot)
        source = repo.get_remote()
    elif (dotwit/source).exists() and (dotwit/source).parent == dotwit:
        repo = GitRepo((dotwit/source).name, dotwit)
        source = repo.get_remote()
    elif (wsroot/source).exists():
        source = str((wsroot/source).resolve())
    elif Path(source).exists():
        source = str(Path(source).resolve())

    return Dependency(None, source, revision, message)


def check_submodule_only(repo_path):
    """ Refuse to modify dependencies on repositories that only use git submodules"""
    dirname = os.path.basename(str(repo_path))
    manifest_path = repo_path/GitRepo.PKG_DEPENDENCY_FILE
    submodule_path = repo_path/GitRepo.SUBMODULE_FILE
    if not manifest_path.exists() and submodule_path.exists():
        log.error("{} uses git submodules to specify dependencies".format(dirname))
        sys.exit(1)


def add_dep(ws, args) -> None:
    """ Resolve a Dependency then add it to the cwd's wit-manifest.json """
    packages = {pkg.name: pkg for pkg in ws.lock.packages}
    req_dep = dependency_from_tag(ws.root, args.pkg, message=args.message)

    cwd = Path(os.getcwd()).resolve()
    if cwd == ws.root:
        error("add-dep must be run inside of a package, not the workspace root.\n\n" +
              add_dep_parser.format_help())
    cwd_dirname = cwd.relative_to(ws.root).parts[0]
    if not ws.lock.contains_package(cwd_dirname):
        raise NotAPackageError(
            "'{}' is not a package in workspace at '{}'".format(cwd_dirname, ws.path))

    # in order to resolve the revision, we need to bind
    # the req_dep to disk, cloning into .wit if neccesary
    req_dep.load(packages, ws.repo_paths, ws.root, True)
    try:
        req_dep.package.revision = req_dep.resolved_rev()
    except GitCommitNotFound:
        raise WitUserError("Could not find commit or reference '{}' in '{}'"
                           "".format(req_dep.specified_revision, req_dep.name))

    check_submodule_only(cwd)

    manifest_path = cwd/GitRepo.PKG_DEPENDENCY_FILE
    if manifest_path.exists():
        manifest = Manifest.read_manifest(manifest_path)
    else:
        manifest = Manifest([])

    # make sure the dependency is not already in the cwd's manifest
    if manifest.contains_dependency(req_dep.name):
        log.error("'{}' already depends on '{}'".format(cwd_dirname, req_dep.name))
        sys.exit(1)

    manifest.add_dependency(req_dep)
    manifest.write(manifest_path)

    log.info("'{}' now depends on '{}'".format(cwd_dirname, req_dep.package.id()))


def update_dep(ws, args) -> None:
    packages = {pkg.name: pkg for pkg in ws.lock.packages}
    req_dep = dependency_from_tag(ws.root, args.pkg, message=args.message)

    cwd = Path(os.getcwd()).resolve()

    if cwd == ws.root:
        error("update-dep must be run inside of a package, not the workspace root.\n"
              "  A dependency is updated in the package determined by the current working "
              "directory,\n  which can also be set by -C.")

    cwd_dirname = cwd.relative_to(ws.root).parts[0]

    check_submodule_only(cwd)
    manifest = Manifest.read_manifest(cwd/GitRepo.PKG_DEPENDENCY_FILE)

    # make sure the package is already in the cwd's manifest
    if not manifest.contains_dependency(req_dep.name):
        log.error("'{}' does not depend on '{}'".format(cwd_dirname, req_dep.name))
        sys.exit(1)

    req_dep.load(packages, ws.repo_paths, ws.root, True)
    req_pkg = req_dep.package
    try:
        req_pkg.revision = req_dep.resolved_rev()
    except GitCommitNotFound:
        raise WitUserError("Could not find commit or reference '{}' in '{}'"
                           "".format(req_dep.specified_revision, req_dep.name))

    # check if the requested repo is missing from disk
    if req_pkg.repo is None:
        msg = "'{}' not found in workspace. Have you run 'wit update'?".format(req_dep.name)
        raise PackageNotInWorkspaceError(msg)

    log.info("Updating to {}".format(req_dep.resolved_rev()))
    manifest.replace_dependency(req_dep)
    manifest.write(cwd/GitRepo.PKG_DEPENDENCY_FILE)

    log.info("'{}' now depends on '{}'".format(cwd_dirname, req_pkg.id()))


def status(ws, args) -> None:
    log.debug("Checking workspace status")
    if not ws.lock:
        log.info("{} is empty. Have you run `wit update`?".format(ws.LOCK))
        return

    clean = []
    dirty = []
    untracked = []
    missing = []
    seen_paths = {}
    for package in ws.lock.packages:
        package.load(ws.root, False)
        if package.repo is None:
            missing.append(package)
            continue
        seen_paths[package.repo.path] = True

        lock_commit = package.revision
        latest_commit = package.repo.get_head_commit()

        new_commits = lock_commit != latest_commit

        if new_commits or not package.repo.clean():
            status = []
            if new_commits:
                status.append("new commits")
            if package.repo.modified():
                status.append("modified content")
            if package.repo.untracked():
                status.append("untracked content")
            dirty.append((package, status))
        else:
            clean.append(package)

    for path in ws.root.iterdir():
        if path not in seen_paths and path.is_dir() and GitRepo.is_git_repo(path):
            untracked.append(path)
        seen_paths[path] = True

    log.info("Clean packages:")
    for package in clean:
        log.info("    {}".format(package.name))
    log.info("Dirty packages:")
    for package, content in dirty:
        msg = ", ".join(content)
        log.info("    {} ({})".format(package.name, msg))
    if len(untracked) > 0:
        log.info("Untracked packages:")
        for path in untracked:
            relpath = path.relative_to(ws.root)
            log.info("    {}".format(relpath))
    if len(missing) > 0:
        log.info("Missing packages:")
        for package in missing:
            log.info("    {}".format(package.name))

    packages, errors = ws.resolve()
    for name in packages:
        package = packages[name]
        s = package.status(ws.lock)
        if s:
            print(package.name, s)

    print_errors(errors)


def update(ws, args) -> None:
    packages, errors = ws.resolve(download=True)
    if len(errors) == 0:
        ws.checkout(packages)
    else:
        print_errors(errors)
        sys.exit(1)

def version() -> None:
    version = get_git_version()
    if not version:
        version = get_dist_version()
    print("wit {}".format(version))


def get_git_version():
    # not an official release, use git to get an explicit version
    path = Path(__file__).resolve().parent.parent.parent
    log.spam("Running [git -C {} describe --tags --dirty]".format(str(path)))
    proc = subprocess.run(['git', '-C', str(path), 'describe', '--tags', '--dirty'],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    version = proc.stdout.decode('utf-8').rstrip()
    log.spam("Output: [{}]".format(version))
    return re.sub(r"^v", "", version)


def get_dist_version():
    return __version__
