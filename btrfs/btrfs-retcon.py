# see: https://www.reddit.com/r/synology/comments/d1id10/psa_you_actually_can_delete_individual_files_from/

import btrfsutil
import os
import argparse
import pathlib
from pathlib import Path
from pprint import pprint

parser = argparse.ArgumentParser(
    prog='btrfs-retcon',
    description='Removes a file from all snapshots it exists in, temporarily making those snapshots rw to do so. if --as-glob is set, the path will be interpreted as a glob pattern instead, and applied to all snapshots in the volume')
parser.add_argument('path_to_remove')
parser.add_argument('--as-glob', default=False, action="store_true")
parser.add_argument('-V', '--volume', default='/')
    
args = parser.parse_args()
pprint(btrfsutil.is_subvolume(args.volume))
if not btrfsutil.is_subvolume(args.volume):
    raise Exception(f"{args.volume} is not a subvolume.")
target_volume_info = btrfsutil.subvolume_info(args.volume)
print("target volume:")
pprint(target_volume_info)

target_filename = args.path_to_remove

def repl(vars):
    import code
    import readline
    import rlcompleter
    readline.set_completer(rlcompleter.Completer(vars).complete)
    readline.parse_and_bind("tab: complete")
    code.InteractiveConsole(vars).interact()
    
class FoundSnapshotFile:
    def __init__(self, subvol_path: str, id_: int, file: pathlib.Path):
        if '.snapshots' not in str(file):
            raise Exception(f'The path {file} is not in a snapshot?')
        self.subvol_path = subvol_path
        self.id = id_
        self.file = file
        self.stat = file.stat()
        self.size_gib = self.stat.st_size / 1024 / 1024
        import datetime
        self.modified = datetime.datetime.fromtimestamp(self.stat.st_mtime)
    def __str__(self):
        return f'{self.file} {self.size_gib}GiB ref, modified {self.modified}'
    def _retcon_safety_check(self):
        # safety check: does the file still exist?
        if not self.file.exists():
            raise Exception(f'File does not exist at {self.file}, will not attempt retcon')
        # safety check: only operate on ro subvolumes
        started_ro = btrfsutil.get_subvolume_read_only(self.subvol_path)
        if not started_ro:
            raise Exception(f'Subvolume {self.subvol_path} is not read only to start, it is {started_ro}')
    def retcon(self):
        self._retcon_safety_check()
        print(f'Temporarily making {self.subvol_path} rw to remove {self.file}')
        btrfsutil.set_subvolume_read_only(self.subvol_path, False)
        try:
            print(f'Deleting {self.file}')
            self.file.unlink()
        finally:
            print(f'Changing {self.subvol_path} back to ro')
            btrfsutil.set_subvolume_read_only(self.subvol_path, True)

class FileToRetcon:
    def __init__(self, path, target_volume):
        self.target_volume = target_volume
        self.path_orig = path
        if path.startswith(target_volume) and len(target_volume) > 1:
            self.path = path[len(target_volume):]
        else:
            self.path = path

    def to_pathlib_for_snapshot(self, snapshot_path):
        return Path(self.target_volume) / snapshot_path / self.path

target_files = []
snapshots_with_file = []

target_files.append(FileToRetcon(target_filename, args.volume))

def build_snapshot_path(volume, snapshot_path, target_filename):
    if target_filename.startswith(volume) and len(volume) > 1:
        return Path(volume) / snapshot_path / (target_filename[len(volume):])
    return Path(volume) / snapshot_path / target_filename

# id was hardcoded to 256. i guess that's just /?
if not args.as_glob:
    with btrfsutil.SubvolumeIterator(args.volume, target_volume_info.id) as it:
        # This is just an example use-case for fileno(). It is not necessary.
        #btrfsutil.sync(it.fileno())
        for path, id_ in it:
            print(f"sviter: {id_}, {path}")
            if not path.startswith('.snapshots'):
                continue
            for target_to_retcon in target_files:
                target = target_to_retcon.to_pathlib_for_snapshot(path)
                print(f"checking: {target}")
                if target.exists():
                    print(f'{target} exists')
                    started_ro = btrfsutil.get_subvolume_read_only(args.volume + path)
                    print(f'subvol {path} read only: {started_ro}')
                    if started_ro:
                        snapshots_with_file.append(FoundSnapshotFile(args.volume + path, id_, target))
else:
    import glob
    with btrfsutil.SubvolumeIterator(args.volume, target_volume_info.id) as it:
        for subvolume_path, id_ in it:
            if not subvolume_path.startswith('.snapshots'):
                continue

            volume_root = Path(args.volume)
            glob_search_root = volume_root / subvolume_path
            print(f"glob search: in {glob_search_root} for {target_filename}")
            for g in glob.glob(target_filename, root_dir=glob_search_root, recursive=True, include_hidden=True):
                g_path = glob_search_root / g
                if not g_path.is_file():
                    continue
                print(g)
                started_ro = btrfsutil.get_subvolume_read_only(args.volume + subvolume_path)
                print(f'subvol {subvolume_path} glob result "{g}" read only: {started_ro}')
                if started_ro:
                    snapshots_with_file.append(FoundSnapshotFile(args.volume + subvolume_path, id_, g_path))


if len(snapshots_with_file) == 0:
    print(f'{target_filename} was not found in any snapshots.')
    exit(1)

for f in snapshots_with_file:
    print(f)

import glob
import itertools
def groups(key_func=(lambda x: x.file.name), print_each=False):
    """
    Groups the found snapshot files by using key_func (by default, this is by name: x.file.name)
    if print_each is True, each item will be printed
    Groupings are returned as a dictionary (so that you may call retcon() on items you want to get rid of)
    """
    sorted_files = sorted(snapshots_with_file, key=key_func)
    d = {k: list(v) for k, v in itertools.groupby(sorted_files, key=key_func)}
    if (len(d.keys()) == 0):
        print("1 group")
    else:
        print(f"{len(d.keys())} groups")

    for group in d.keys():
        print(f"- {group} [{len(d[group])}]")
        if print_each:
            for i in d[group]:
                print(f"    - {i}")
    return d

import pydoc
pydoc.pager = pydoc.plainpager
helpers = [groups]

print()
print("================================")
#print(f"If you'd like to retcon (unlink) '{target_filename}' from ALL of those snapshots, type 'retcon' to continue. Any other input will abort.")
print(f"Entering repl for inspection and to execute cleanup.")
print(f"snapshots_with_file[{len(snapshots_with_file)}] is an array of instances where a target file was found in a snapshot.")
print("Call the .retcon() method on each of them to unlink them. Otherwise they will be left alone.")
print()
print("================================")
print("helpers:")
print("================================")
for h in helpers:
    help(h)
print("================================")
print(f"examples:")
print("================================")
print("for f in snapshots_with_file: f.retcon()")
print()
print("for f in snapshots_with_file: print(f)")
print()
print("groups(lambda x: x.file.name)")
print("groups(lambda x: x.size_gib)")
print()
print("# group by impacted subvolume")
print("groups(lambda x: x.subvol_path)")
print("================================")
print()


repl(locals())
#user_input_str = input('retcon? ')
#
#if user_input_str != 'retcon':
    #print(f"aborting.")
    #quit(1)

#for f in snapshots_with_file:
#    f.retcon()

#repl(locals())
