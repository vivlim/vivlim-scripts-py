#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["plumbum"]
# ///

import argparse
import os.path
from plumbum import local
from plumbum.cmd import sudo, btrfs, mv, cp, chown, chmod

parser = argparse.ArgumentParser()
parser.add_argument('p', nargs='?')
args = parser.parse_args()
p = args.p

if not p:
    print("missing target path")
    exit()

if not os.path.isdir(p):
    print(f"path doesn't exist: {p}")
    exit()


def test_volume_exists(p):
    (ret, stdout, stderr)=sudo[btrfs['subvolume', 'show', p]].run(retcode=None)
    return ret == 0

def get_mode(p):
    from plumbum.cmd import stat
    return stat('-c', '%a', p).strip()

def get_owner(p):
    from plumbum.cmd import stat
    return stat('-c', '%U:%G', p).strip()

is_already_subvolume = test_volume_exists(p)    
if is_already_subvolume:
    print("it is already a subvolume")
    exit(1)

from plumbum import local
p_old = local.path(p + "_old")
p = local.path(p)
p_mode = get_mode(p)
p_owner = get_owner(p)

print(f"{p} mode is {p_mode}")
print(f"{p} owner is {p_owner}")
print(f"moving {p} to {p_old}")
sudo[mv[p, p_old]]()
print(f"creating subvolume at {p}")
sudo[btrfs['subvolume', 'create', p]]()

from plumbum.machines import LocalCommand
orig_quote_level = LocalCommand.QUOTE_LEVEL
try:
    sudo[chown[p_owner, p]]()
    sudo[chmod["777", p]]() # 777 so we can copy things in without elevation ... may not work if we aren't allowed to read, idk

    print(f"subvolume created. check that {p} is ok, then remove {p_old}")

    import os
    from os.path import join

    for f in os.listdir(p_old):
        f_source = p_old / f
        f_target= p / f
        print(f"{f_source} -> {f_target}")
        # LocalCommand.QUOTE_LEVEL = 999 # hack to bypass quote escaping https://github.com/tomerfiliba/plumbum/issues/253#issuecomment-310802501
        try:
            cp['--archive', '--one-file-system', '--reflink=always', f_source, f_target]()
            # sudo[cp['--archive', '--one-file-system', '--reflink=always', f"'{f_source}'", f"'{f_target}'"]]()
        finally:
            LocalCommand.QUOTE_LEVEL = orig_quote_level
    sudo[chmod[p_mode, p]]()

    # sudo[cp['--archive', '--one-file-system', '--reflink=always', p_old + "/*", p]]()
    # sudo[cp['--archive', '--one-file-system', '--reflink=always', p_old + "/.*", p]].run(retcode=None)
    #sudo[]
except Exception:
    import traceback
    traceback.print_exc()
    print("rolling back subvolume creation.")
    sudo[btrfs['subvolume', 'delete', p]]()
    sudo[mv[p_old, p]]()
    print("rollback successful?")
    
