"""

"""
import os
import json
from sys import exit
from sys import stdout
import re
from shutil import copyfile
from shutil import move
from collections import namedtuple

file_spec = namedtuple("file_spec", ["source", "dest", "file_size", "file_name", "extension"])

class JSONDb:
    """docstring for JSONDb"""


    def __init__(self, **arg):

        # storage_device :: Device ID where the removable media is expected
        # self.storage_device = r'F:'
        self.storage_device = r'/run/media/andy/LUMIX/'
        # self.storage_device = r'V:'

        # id_location :: file name where the camera's name is expected to be found
        #       this is always in the root folder of storage_device
        self.id_location = 'camera-id'

        # camera_id :: the camera's name, expected to match EXIF
        self.camera_id = ''

        # d_passed :: [dictionary or json object?] passed as parameter
        self.d_passed = None

        # name of the file this instance will maintain in this session
        self.filename = ''

        # reset :: pass anything to recreate the file with defaults 
        self.reset = False

        # d_untested :: json object read from file
        self.d_untested = None

        # files_to_copy :: list of filespecs that have been identified to be copied
        self.files_to_copy = []

        # file_types_to_copy :: set of file extensions that have been identified to be copied
        self.file_types_to_copy = set()

        # total_bytes_to_copy :: size of files_to_copy
        self.total_bytes_to_copy = 0

        # d :: the working details. also serves as new file defaults
        self.d = {}


        for kwd in ['f', 'file', 'filename']:
            """ scan the parameters for one of the keyword names
                if the keyword matches
                    save the payload
                --> if multiple parameters match, only the last match will be considered
            """
            if kwd in (k.lower() for k in arg.keys()):
                # got something
                self.filename = arg[kwd]

        for kwd in ['d', 'dict', 'dictionary', 'configs']:
            """ scan the parameters for one of the keyword names
                if the keyword matches
                    save the payload
                --> if multiple parameters match, only the last match will be considered
            """
            if kwd in (k.lower() for k in arg.keys()):
                if arg[kwd] != None:
                    self.d_passed = arg[kwd]

        for kwd in ['r', 'reset']:
            if kwd in (k.lower() for k in arg.keys()):
                self.reset = True

        # args obtained, now finish setting up
        self.setup()


    def get_storage_device(self):
        return self.storage_device


    def read_camera_id(self):
        """ read the camera id from the file where we expect it to be """
        fqpn = f'{self.storage_device}{self.id_location}'
        try:
            with open(fqpn, 'r') as f:
                while True:
                    line = f.readline().replace('\n','')
                    if line[0] != '#':
                        print(line)
                        return line
        except PermissionError as e:
            print(f'fqpn : {fqpn}\nin JSONDb.py.read_camera_id()\nhas it failed here?')
            print(f'\nI got PermissionError:\n  i:    {e}\n\n  >:    Is the card inserted?\n  >:    Is it inserted into the correct drive?\n')
            raise
        except FileNotFoundError as e:
            print('FileNotFoundError. Probably the stoprage card is not inserted? (linux version)')
            print(f'The original error was {e}')
            raise

    def setup(self):
        """ set up particulars for this session:
            * get the filename of the transfer tracking file
            * decide whether any passed dictionary should be used
        """
        self.camera_id = self.read_camera_id()
        if self.filename:
            file_exists = self.open_file()
        else:
            raise TypeError('No filename was found in the parameters')
            exit()

        if file_exists:
            # we opened an existing file, so check the dictionary
            adopted = self.evaluate(self.d_untested)
            if not adopted:
                # bad dict or none found in the file
                print(f'Ignoring dictionary in parameter (not a valid dictionary)')


    def backup(self):
        """make backup(s) of the json db"""
        for i in [3,2]:
            try:
                move(f'{self.filename}.{i-1}', f'{self.filename}.{i}')
            except FileNotFoundError:
                pass
        move(f'{self.filename}', f'{self.filename}.1')


    def write_file(self):
        """ [re]create a file using the dictionary onboard self """
        self.backup()
        try:
            with open(self.filename, 'w') as f:
                payload = json.dumps(self.d)        # .dumps :: Python obj --> json
                f.write(payload)
        except FileNotFoundError as e:
            print(f'Unable to write file {self.filename}')
            exit()
        except Exception as e:
            print(f'\n>>> :( unhandled exception :(\n{e}')
            exit()


    def open_file(self):
        """determine whether we open existing or create anew"""
        if self.reset:
            self.write_file()
            result = False
        else:
            try:
                with open(self.filename, 'r') as f:
                    self.d_untested = f.read()
                result = True
            except FileNotFoundError:
                self.write_file()
                result = False
            except Exception as e:
                # we'll handle a "file not found error"
                print(f'>>> :( unhandled exception :(\n>>> {e}')
                exit()
        return result


    def evaluate(self, data):
        """ evaluate data as a dictionary; if it's good, keep it """
        try:
            d_tentative = json.loads(data)      # .loads :: json --> Python obj
            result = True
            # having gotten this far, 
            # we accept the data as our new dictionary, replacing the default
            self.d = d_tentative
        except json.decoder.JSONDecodeError:
            result = False
        except TypeError:
            result = False
        return result


    def _find_files(self):
        """ enumerate folders that might have the files we want """

        """this method needs to be split up
        the actual file copy task should probably go up to the main application"""

        patterns = {}

        def get_patterns():
            """enumerate the file name patterns we want"""
            pattern_count = 0
            try:
                for pattern in self.d[self.camera_id]["Properties"]["Patterns"].values():
                    patterns[pattern_count] = {
                        "Path": pattern["Path"],
                        "Last": pattern["Last"]
                        }
                    pattern_count += 1
            except KeyError as e:
                print(f'>>> :( unhandled exception :(\n>>> {e}')
                raise
                exit()
            return patterns


        def check_file(filename):
            """ check a specific file to determine whether it should be moved """
            extpart = filename.split('.')[-1]
            filepart = filename.split('/')[-1].split('.')[0]
            result = False, None
            # print(f'patterns: {patterns}')
            for i in range(len(patterns)):
                last = patterns[i]["Last"]
                last_ext = last.split('.')[-1]
                last_file = last.split('.')[0]
                if filepart > last_file and extpart == last_ext:
                    return True, extpart
                # print(f'filename: {filename} | filepart: {filepart} | last_file: {last_file} | extpart: {extpart}')
            return result


        # walk the path, noting any files that need to be copied
        # print(f'd: {self.d}\n')
        dest_path = self.d[self.camera_id]["Properties"]["Target"]
        patterns = get_patterns()
        # print(f'patterns: {patterns}\n')
        for p, d, f in os.walk(self.storage_device):
            # print(f'p, d, f: \n{p}\n{d}\n{f}\n')
            for file_name in f:
                candidate_file = os.path.join(p, file_name)
                for i in range(len(patterns)):
                    if re.search(patterns[i]["Path"], candidate_file):
                        copy_this, extension = check_file(candidate_file)
                        self.file_types_to_copy.add(extension)
                        if copy_this:
                            dest = os.path.join(dest_path, file_name)
                            file_size = os.path.getsize(candidate_file)
                            self.total_bytes_to_copy += file_size
                            self.files_to_copy.append(file_spec(candidate_file, dest, file_size, file_name, extension))
                    # else:
                    # print(f'patterns[i]["Path"], candidate_file : {patterns[i]["Path"], candidate_file}')


    def _copy_file_worker(self):
        # copy the files
        if self.files_to_copy:
            # actual_len = len(self.files_to_copy)
            # get log 10 of the length
            # "round" it to one decimal
            # convert that to a common power of ten-based semantic label like "20.3 GB (19.7 GiB)" (I'm sure I didn't do that right here)
            # use the converted semantics in the next print statement:
            print(f'found {len(self.files_to_copy)} files to copy ({self.total_bytes_to_copy:,} bytes)')
            bytes_moved = 0
            for file in self.files_to_copy:
                copyfile(file.source, file.dest)
                bytes_moved += file.file_size
                print(f'\rcopying files... ({(100*bytes_moved)//self.total_bytes_to_copy}%)', end='')
                stdout.flush()
            print('\n')
            self._update_storage_db()


    def _update_storage_db(self):
        # update storage db with last file name per file type
        for extension in self.file_types_to_copy:
            if extension:
                filtered = [f for f in self.files_to_copy if f.extension == extension]
                last = sorted(filtered, key=lambda f: f.file_name, reverse=True)[0]
                self.d[self.camera_id]['Properties']['Patterns'][extension]['Last'] = last.file_name
        self.write_file()


    def copy_files(self):
        """friendly interface to find and copy files"""
        # print('called copy_files\n')
        self._find_files()
        self._copy_file_worker()
