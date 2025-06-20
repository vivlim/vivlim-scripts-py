# see: https://www.reddit.com/r/synology/comments/d1id10/psa_you_actually_can_delete_individual_files_from/

import btrfsutil
import os
import argparse
import pathlib

parser = argparse.ArgumentParser(
    prog='btrfs-retcon',
    description='Removes a file from all snapshots it exists in, temporarily making those snapshots rw to do so')
parser.add_argument('path_to_remove')
parser.add_argument('-V', '--volume', default='/') # todo: make this work correctly. it doesn't!
    
args = parser.parse_args()

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
    def retcon(self):
        # safety check: does the file still exist?
        if not self.file.exists():
            raise Exception(f'File does not exist at {self.file}, will not attempt retcon')
        # safety check: only operate on ro subvolumes
        started_ro = btrfsutil.get_subvolume_read_only(self.subvol_path)
        if not started_ro:
            raise Exception(f'Subvolume {self.subvol_path} is not read only to start, it is {started_ro}')
        print(f'Temporarily making {self.subvol_path} rw to remove {self.file}')
        btrfsutil.set_subvolume_read_only(self.subvol_path, False)
        try:
            print(f'Deleting {self.file}')
            self.file.unlink()
        finally:
            print(f'Changing {self.subvol_path} back to ro')
            btrfsutil.set_subvolume_read_only(self.subvol_path, True)


snapshots_with_file = []

with btrfsutil.SubvolumeIterator(args.volume, 256) as it:
    # This is just an example use-case for fileno(). It is not necessary.
    #btrfsutil.sync(it.fileno())
    for path, id_ in it:
        if not path.startswith('.snapshots'):
            continue
        #print(id_, path)
        target = pathlib.Path(args.volume + path + target_filename)
        if target.exists():
            print(f'{target} exists')
            started_ro = btrfsutil.get_subvolume_read_only(args.volume + path)
            print(f'subvol {path} read only: {started_ro}')
            if started_ro:
                snapshots_with_file.append(FoundSnapshotFile(args.volume + path, id_, target))

if len(snapshots_with_file) == 0:
    print(f'{target_filename} was not found in any snapshots.')
    exit(1)

for f in snapshots_with_file:
    print(f)

print(f"If you'd like to retcon (unlink) '{target_filename}' from ALL of those snapshots, type 'retcon' to continue. Any other input will abort.")

user_input_str = input('retcon? ')

if user_input_str != 'retcon':
    print(f"aborting.")
    quit(1)

for f in snapshots_with_file:
    f.retcon()

#repl(locals())
