#!/usr/bin/env python3
"""Confined, symlink-safe creation of private output files and directories (stdlib; python3 -I).

Every output of plan.sh, cleanup.sh, deploy.sh and the timeout helper is created through this module so a
pre-existing path (a symlink to an outside file, a leftover file, an alias of another output) can never make a
script overwrite or truncate something it did not create.

Rules enforced here
  * every path is absolute and holds no ".." component;
  * a path must lie inside the directory named for it (for example the git-ignored plan directory) and inside the
    repository root; an alias of the repository root itself (for example /var versus /private/var) is accepted;
  * no existing component of the path below the repository root may be a symlink;
  * a new output must NOT exist yet (os.path.lexists, so a dangling or live symlink counts as existing);
  * outputs of one run must be pairwise distinct (after case folding, because the default macOS file system is
    case-insensitive) and none may be an ancestor directory of another;
  * the file itself is opened with O_CREAT | O_EXCL | O_NOFOLLOW (never O_TRUNC), walking the directory chain with
    O_NOFOLLOW directory descriptors so a component swapped for a symlink after the check is refused;
  * new directories are 0700 and new files 0600.

CLI (exit 0 ok, 1 refused with a "SAFEIO-REFUSED: <reason>" line on stdout, 2 usage)
  check-new   --root R --entry LABEL WITHIN-NAME WITHIN-ABS PATH ...   validate, create nothing; prints each confined path
  fresh-dir   --root R --within-name N --within W --path P              create P (0700) which must not exist
  ensure-dir  --root R --within-name N --within W --path P              create P and parents if missing (0700)
  create-new  --root R PATH ...                                         create empty 0600 files (O_EXCL)
  write-new   --root R PATH                                             stdin to a new 0600 file (O_EXCL)
  check-file  --root R --within-name N --within W PATH                  an existing regular file, no symlinks
"""
import argparse
import errno
import os
import stat
import sys


class Refused(Exception):
    pass


def _real(path):
    return os.path.realpath(path)


def resolve_under_root(root, path):
    """Normalise an absolute, ".."-free PATH and express it under realpath(ROOT).

    An alias of the root itself is accepted: the deepest ancestor of PATH whose realpath is the root is replaced
    by the real root. Everything below that point is checked component by component afterwards."""
    if not isinstance(path, str) or not os.path.isabs(path):
        raise Refused("path must be absolute: %s" % path)
    if ".." in path.split(os.sep):
        raise Refused("path must not contain '..'")
    path = os.path.normpath(path)
    real_root = _real(root)
    if path == real_root or path.startswith(real_root + os.sep):
        return path
    current = path
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
        if _real(current) == real_root:
            return real_root + path[len(current):]
    raise Refused("path is outside the repository")


def within(path, base):
    return path == base or path.startswith(base + os.sep)


def check_no_symlink_chain(real_root, path):
    relative = os.path.relpath(path, real_root)
    if relative == ".":
        return
    current = real_root
    for part in relative.split(os.sep):
        current = os.path.join(current, part)
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            return  # the remaining components do not exist yet
        if stat.S_ISLNK(mode):
            raise Refused("a path component is a symlink: %s" % os.path.relpath(current, real_root))


def confine(root, path, within_name, within_dir, label="path", allow_base=False):
    """Return the confined absolute path or raise Refused."""
    real_root = _real(root)
    try:
        resolved = resolve_under_root(root, path)
    except Refused as error:
        raise Refused("%s must live inside %s (%s)" % (label, within_name, error))
    base = resolve_under_root(root, within_dir)
    if not within(resolved, base) or (resolved == base and not allow_base):
        raise Refused("%s must live inside %s" % (label, within_name))
    check_no_symlink_chain(real_root, resolved)
    return resolved


def ensure_dirs(real_root, directory):
    """Create DIRECTORY and its missing parents below the root (0700); every existing part must be a real directory."""
    relative = os.path.relpath(directory, real_root)
    if relative == ".":
        return
    current = real_root
    for part in relative.split(os.sep):
        current = os.path.join(current, part)
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            os.mkdir(current, 0o700)
            os.chmod(current, 0o700)
            continue
        if stat.S_ISLNK(mode):
            raise Refused("a path component is a symlink: %s" % os.path.relpath(current, real_root))
        if not stat.S_ISDIR(mode):
            raise Refused("a path component is not a directory: %s" % os.path.relpath(current, real_root))


def _open_dir_chain(real_root, parts):
    """Open the directory REAL_ROOT/parts... with O_NOFOLLOW at every step; returns a directory descriptor."""
    fd = os.open(real_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for part in parts:
            try:
                next_fd = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW, dir_fd=fd)
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise Refused("a path component is a symlink or not a directory: %s" % part)
                raise
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _split_for_open(root, path):
    real_root = _real(root)
    resolved = resolve_under_root(root, path)
    if resolved == real_root:
        raise Refused("path names the repository root")
    parts = os.path.relpath(resolved, real_root).split(os.sep)
    return real_root, resolved, parts


def open_new(root, path, mode=0o600):
    """Create a NEW file: O_CREAT | O_EXCL | O_NOFOLLOW below an O_NOFOLLOW directory chain. Returns a binary file object."""
    real_root, _resolved, parts = _split_for_open(root, path)
    dir_fd = _open_dir_chain(real_root, parts[:-1])
    try:
        try:
            fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=dir_fd)
        except FileExistsError:
            raise Refused("output already exists (never overwritten): %s" % os.path.relpath(_resolved, real_root))
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise Refused("output path is a symlink: %s" % os.path.relpath(_resolved, real_root))
            raise
    finally:
        os.close(dir_fd)
    os.fchmod(fd, mode)
    return os.fdopen(fd, "wb")


def open_append_existing(root, path):
    """Open an EXISTING regular file for appending (no O_CREAT, no O_TRUNC, O_NOFOLLOW everywhere)."""
    real_root, resolved, parts = _split_for_open(root, path)
    dir_fd = _open_dir_chain(real_root, parts[:-1])
    try:
        try:
            fd = os.open(parts[-1], os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=dir_fd)
        except FileNotFoundError:
            raise Refused("log file does not exist (it is created exclusively before use): %s" % os.path.relpath(resolved, real_root))
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise Refused("output path is a symlink: %s" % os.path.relpath(resolved, real_root))
            raise
    finally:
        os.close(dir_fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise Refused("output is not a regular file: %s" % os.path.relpath(resolved, real_root))
    return os.fdopen(fd, "ab")


def open_leaf_nofollow(path, flags, mode=0o600):
    """Open PATH refusing a symlink at the leaf (for private temp files whose directory the caller already made)."""
    try:
        fd = os.open(path, flags | os.O_NOFOLLOW, mode)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise Refused("output path is a symlink: %s" % os.path.basename(path))
        raise
    return fd


def check_new(root, entries):
    """entries: [(label, within_name, within_dir, path)]. Returns the confined paths. Creates nothing."""
    resolved = []
    for label, within_name, within_dir, path in entries:
        confined = confine(root, path, within_name, within_dir, label)
        if os.path.lexists(confined):
            raise Refused("%s already exists (an output path is never reused or overwritten): %s" % (label, os.path.relpath(confined, _real(root))))
        resolved.append((label, confined))
    folded = {}
    for label, confined in resolved:
        key = confined.casefold()
        if key in folded:
            raise Refused("outputs collide: %s and %s resolve to the same file" % (folded[key], label))
        folded[key] = label
    for label, confined in resolved:
        for other_label, other in resolved:
            if other_label != label and other.casefold().startswith(confined.casefold() + os.sep):
                raise Refused("outputs collide: %s is a directory that holds %s" % (label, other_label))
    return [path for _label, path in resolved]


def cmd_check_new(args):
    entries = [tuple(entry) for entry in args.entry]
    for path in check_new(args.root, entries):
        print(path)  # the confined (alias-resolved) path of each entry, in order
    return 0


def cmd_fresh_dir(args):
    real_root = _real(args.root)
    path = confine(args.root, args.path, args.within_name, args.within)
    if os.path.lexists(path):
        raise Refused("directory already exists (a run directory is never reused): %s" % os.path.relpath(path, real_root))
    ensure_dirs(real_root, os.path.dirname(path))
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)
    print(path)
    return 0


def cmd_ensure_dir(args):
    real_root = _real(args.root)
    path = confine(args.root, args.path, args.within_name, args.within, allow_base=True)
    ensure_dirs(real_root, path)
    print(path)
    return 0


def cmd_create_new(args):
    for path in args.paths:
        open_new(args.root, path).close()
    return 0


def cmd_write_new(args):
    handle = open_new(args.root, args.path)
    try:
        for block in iter(lambda: sys.stdin.buffer.read(65536), b""):
            handle.write(block)
    finally:
        handle.close()
    return 0


def cmd_check_file(args):
    path = confine(args.root, args.path, args.within_name, args.within)
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        raise Refused("file does not exist: %s" % os.path.relpath(path, _real(args.root)))
    if not stat.S_ISREG(mode):
        raise Refused("not a regular file: %s" % os.path.relpath(path, _real(args.root)))
    print(path)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check-new")
    p.add_argument("--root", required=True)
    p.add_argument("--entry", nargs=4, action="append", required=True, metavar=("LABEL", "WITHIN_NAME", "WITHIN_ABS", "PATH"))
    p.set_defaults(fn=cmd_check_new)

    for name, fn in (("fresh-dir", cmd_fresh_dir), ("ensure-dir", cmd_ensure_dir)):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.add_argument("--within-name", required=True)
        p.add_argument("--within", required=True)
        p.add_argument("--path", required=True)
        p.set_defaults(fn=fn)

    p = sub.add_parser("create-new")
    p.add_argument("--root", required=True)
    p.add_argument("paths", nargs="+")
    p.set_defaults(fn=cmd_create_new)

    p = sub.add_parser("write-new")
    p.add_argument("--root", required=True)
    p.add_argument("path")
    p.set_defaults(fn=cmd_write_new)

    p = sub.add_parser("check-file")
    p.add_argument("--root", required=True)
    p.add_argument("--within-name", required=True)
    p.add_argument("--within", required=True)
    p.add_argument("path")
    p.set_defaults(fn=cmd_check_file)
    return parser


def main(argv):
    namespace = build_parser().parse_args(argv)
    try:
        return namespace.fn(namespace)
    except Refused as error:
        print("SAFEIO-REFUSED: %s" % error)
        return 1
    except OSError as error:
        print("SAFEIO-REFUSED: %s" % type(error).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
