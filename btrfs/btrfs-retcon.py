# see: https://www.reddit.com/r/synology/comments/d1id10/psa_you_actually_can_delete_individual_files_from/

import btrfsutil
import os
import argparse
import pathlib
from pathlib import Path
from pprint import pprint

# some examples (check how to add these to ArgumentParser later)
# python3 ./btrfs-retcon.py -V /home/ "vivlim/.local/share/Steam/steamapps/common/GarrysMod/**" --as-glob
# python3 ./btrfs-retcon.py "/var/lib/libvirt/images/**" --as-glob


# ... if you need to flip a snapshot back to ro manually,
#btrfs property set -ts /home/.snapshots/2/snapshot/ ro false

# note to self: i have snapper set up :)
# maybe add some functions here for managing it idk
# snapper configs are at /etc/snapper/configs
# if i want to not snapshot a path it needs to be its own subvolume.
# move the original somewhere, then `btrfs subvolume create /wherever/it/was`
# cp --archive --one-file-system --reflink=always /original /wherever/it/was
# then clean up the original copy

parser = argparse.ArgumentParser(
    prog='btrfs-retcon',
    description='Removes a file from all snapshots it exists in, temporarily making those snapshots rw to do so. if --as-glob is set, the path will be interpreted as a glob pattern instead, and applied to all snapshots in the volume')
parser.add_argument('path_to_remove')
parser.add_argument('--as-glob', default=False, action="store_true")
parser.add_argument('-V', '--volume', default='/')
parser.add_argument('--retcon-all-noninteractively', default=False, action="store_true")
    
args = parser.parse_args()
if args.volume == '':
    # not sure why argparse is not just using the default i specified
    args.volume = '/'

pprint(btrfsutil.is_subvolume(args.volume))
if not btrfsutil.is_subvolume(args.volume):
    raise Exception(f"{args.volume} is not a subvolume.")
target_volume_info = btrfsutil.subvolume_info(args.volume)
print(f"target volume {args.volume} info:")
pprint(target_volume_info)

target_filename = args.path_to_remove

def repl(vars):
    try:
        from ptpython.repl import embed
        history_filename = pathlib.Path.home() / '.btrfs-retcon-history'
        embed(globals(), locals(), history_filename=str(history_filename))
    except:
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
    def __repr__(self):
        return "{" + self.__str__() + "}"
    def __pt_repr__(self):
        from prompt_toolkit.formatted_text import HTML
        return HTML(f'(<yellow>{self.file}</yellow> <green>{self.size_gib}GiB</green> ref, modified <blue>{self.modified}</blue>)')

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
        #print(f'Temporarily making {self.subvol_path} rw to remove {self.file}')
        btrfsutil.set_subvolume_read_only(self.subvol_path, False)
        try:
            print(f'Deleting {self.file}')
            self.file.unlink()
        finally:
            #print(f'Changing {self.subvol_path} back to ro')
            btrfsutil.set_subvolume_read_only(self.subvol_path, True)


# uhhhh it seems very unintuitive for pathlib to be like this
# https://stackoverflow.com/a/78155721
def join_paths(*args: Path):
    """Concatenate paths even if some paths are absolute"""
    return Path(args[0], *[str(arg).lstrip('/') for arg in args[1:]])

import typing, itertools

def bulk_retcon(bulk_targets: typing.List[FoundSnapshotFile]):
    def by_snapshot(f: FoundSnapshotFile):
        return f.subvol_path
    grouped_by_snapshot = itertools.groupby(sorted(bulk_targets, key=by_snapshot), key=by_snapshot)
    for snapshot, snapshot_targets in grouped_by_snapshot:
        snapshot_targets = list(snapshot_targets)
        print(f"retconning from snapshot {snapshot} {len(snapshot_targets)} files...")
        started_ro = btrfsutil.get_subvolume_read_only(snapshot)
        print(f"safety check: is {snapshot} a read-only volume? {started_ro}")
        if not started_ro:
            raise Exception(f'Subvolume {snapshot} is not read only to start, it is {started_ro}')
        # unlock it
        btrfsutil.set_subvolume_read_only(snapshot, False)
        unlink_count = 0
        try:
            for t in snapshot_targets:
                if not t.file.exists():
                    print(f"target no longer exists: {t}")
                    continue
                t.file.unlink()
                unlink_count += 1
        finally:
            btrfsutil.set_subvolume_read_only(snapshot, True)
        print(f"... finished, retconned {unlink_count} files.")


class FileToRetcon:
    def __init__(self, path, target_volume):
        self.target_volume = target_volume
        self.path_orig = path
        if path.startswith(target_volume) and len(target_volume) > 1:
            self.path = path[len(target_volume):]
        else:
            self.path = path

    def to_pathlib_for_snapshot(self, snapshot_path):
        return join_paths(Path(self.target_volume), snapshot_path, self.path)

target_files = []
snapshots_with_file = []

target_files.append(FileToRetcon(target_filename, args.volume))

def build_snapshot_path(volume, snapshot_path, target_filename):
    if target_filename.startswith(volume) and len(volume) > 1:
        return join_paths(Path(volume), snapshot_path, (target_filename[len(volume):]))
    return join_paths(Path(volume), snapshot_path, target_filename)

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
            glob_search_root = join_paths(volume_root, subvolume_path)
            print(f"glob search: in {glob_search_root} for {target_filename}")
            for g in glob.glob(target_filename, root_dir=glob_search_root, recursive=True, include_hidden=True):
                g_path = join_paths(glob_search_root, g)
                if not g_path.is_file():
                    continue
                print(f"{g} -> {g_path}")
                started_ro = btrfsutil.get_subvolume_read_only(args.volume + subvolume_path)
                print(f'subvol {subvolume_path} glob result "{g}" read only: {started_ro}')
                if started_ro:
                    snapshots_with_file.append(FoundSnapshotFile(str(glob_search_root), id_, g_path))


if len(snapshots_with_file) == 0:
    print(f'{target_filename} was not found in any snapshots.')
    exit(1)

for f in snapshots_with_file:
    print(f)

import glob
import itertools


class RetconGroup:
    def __init__(self, key, items):
        self.key = key
        self.items = items
    def __str__(self):
        return f"[{self.key} ({len(self.items)})]"
    def __repr__(self) -> str:
        return self.__str__()
    def __pt_repr__(self):
        from prompt_toolkit.formatted_text import HTML
        return HTML(f"<grey>[</grey><yellow>{self.key}</yellow> ({len(self.items)})<grey>]</grey>")
    def __getitem__(self, item):
        return self.items.__getitem__(item)

    def retcon(self):
        """
        retcons all items in this group
        """
        bulk_retcon(self.items)

def groups(key_func=(lambda x: x.file.name), print_each=False):
    """
    Groups the found snapshot files by using key_func (by default, this is by name: x.file.name)
    if print_each is True, each item will be printed
    Groupings are returned as a list of objects that you may call retcon() on individually (to retcon an entire group at once)
    you can use by_year, by_month, by_day as predefined key functions
    """
    sorted_files = sorted(snapshots_with_file, key=key_func)
    # the way this is unpacked into a dictionary and then put back into tuples is weird, i changed my mind after writing most of it
    # tuples are more ergonomic in a simple repl
    ret = []
    d = {k: list(v) for k, v in itertools.groupby(sorted_files, key=key_func)}
    if (len(d.keys()) == 0):
        print("1 group")
    else:
        print(f"{len(d.keys())} groups")

    idx = 0
    for group in d.keys():
        print(f"{idx}. {group} [{len(d[group])}]")
        if print_each:
            for i in d[group]:
                print(f"    - {i}")
        ret.append(RetconGroup(group, list(d[group])))
        idx += 1

    return ret

def retcon_all():
    """
    Retcons everything that was found.
    """
    bulk_retcon(snapshots_with_file)
    #for f in snapshots_with_file:
    #    f.retcon()

def by_year(x: FoundSnapshotFile):
    return str(x.modified.year)

def by_month(x: FoundSnapshotFile):
    return f"{x.modified.year}-{x.modified.month}"

def by_day(x: FoundSnapshotFile):
    return f"{x.modified.year}-{x.modified.month}-{x.modified.day}"

import pydoc
pydoc.pager = pydoc.plainpager
helpers = [groups, RetconGroup, retcon_all]

def halp():
    for h in helpers:
        help(h)


def examples():
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
    print("groups(by_month, print_each=True)")
    print("groups(by_month, print_each=True)[0].retcon()")
    print("================================")

if args.retcon_all_noninteractively:
    retcon_all()
else:

    print()
    print("================================")
    #print(f"If you'd like to retcon (unlink) '{target_filename}' from ALL of those snapshots, type 'retcon' to continue. Any other input will abort.")
    print(f"Entering repl for inspection and to execute cleanup.")
    print(f"snapshots_with_file[{len(snapshots_with_file)}] is an array of instances where a target file was found in a snapshot.")
    print("Call the .retcon() method on each of them to unlink them. Otherwise they will be left alone.")
    print("================================")
    print("- halp(): print info about some helper functions and classes")
    print("- examples(): print some examples")
    print("- ctrl-d (or quit()): get outta here")
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
