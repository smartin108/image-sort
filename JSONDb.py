"""

"""
import os
import json
from sys import exit
from sys import stdout
import re
from shutil import copyfile
from collections import namedtuple

file_spec = namedtuple("file_spec", ["source", "dest", "file_size", "file_name", "extension"])

class JSONDb:
    """docstring for JSONDb"""


    def __init__(self, **arg):

        # storage_device :: Device ID where the removeable media is expected
        # self.storage_device = r'F:'
        self.storage_device = r'V:'

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

        # d :: the working details. also serves as new file defaults
        self.d = {
                    'Panasonic DMC-G85': {
                        'Properties': {
                            'Patterns': {
                                'JPG': {
                                    'Path': r'^..DCIM\\[0-9]{3}_PANA\\P\d{3}0\d{3}\.JPG$',
                                    'Last': 'P1630839.JPG'
                                    },
                                'RW2': {
                                    'Path': r'^..DCIM\\[0-9]{3}_PANA\\P\d{3}0\d{3}\.RW2$',
                                    'Last': 'P1630839.RW2'
                                    },
                                'MTS': {
                                    'Path': r'^..PRIVATE\\AVCHD\\BDMV\\STREAM\\\d{5}\.MTS$',
                                    'Last': '0.MTS'
                                    }
                                },
                            'Target': 'H:\\Camera Rips'
                            }
                        },
                    'Panasonic Zed-O-Matic': {
                        'Properties': {
                            'Patterns': {
                                'not-yer_JPG': {
                                    'Path': r'^..DCIM\\[0-9]{3}_PANA\\P\d{3}0\d{3}.JPG$',
                                    'Last': 'P1630518.JPG'
                                    },
                                'made_ya_RW2':{
                                    'Path': r'^..DCIM\\[0-9]{3}_PANA\\P\d{3}0\d{3}.RW2$',
                                    'Last': 'P1630568.RW2'
                                    }
                                },
                            'Target': 'H:\\Camera Rips'
                            }
                        },
                    }
                 #

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


    def read_camera_id(self):
        """ read the camera id from the file where we expect it to be """
        fqpn = f'{self.storage_device}{self.id_location}'
        try:
            with open(fqpn, 'r') as f:
                while True:
                    line = f.readline()
                    if line[0] != '#':
                        return line
        except PermissionError as e:
            print(f'\nI got PermissionError:\n  i:    {e}\n\n  >:    Is the card inserted?\n  >:    Is it inserted into the correct drive?\n')
            exit()


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


    def write_file(self):
        """ [re]create a file using the dictionary onboard self """
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


    def find_folders(self):
        """ enumerate folders that might have the files we want """

        def check_file(filename):
            """ check a specific file to determine whether it should be moved """
            extpart = filename.split('.')[-1]
            filepart = filename.split('\\')[-1].split('.')[0]
            result = False, None
            for i in range(pattern_count):
                last = patterns[i]["Last"]
                last_ext = last.split('.')[-1]
                last_file = last.split('.')[0]
                if filepart > last_file and extpart == last_ext:
                    return True, extpart
            return result


        patterns = {}
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

        dest_path = self.d[self.camera_id]["Properties"]["Target"]
        files_to_copy = []
        file_types = set()
        total_bytes = 0
        for p, d, f in os.walk(self.storage_device):
            for file_name in f:
                candidate_file = os.path.join(p, file_name)
                for i in range(pattern_count):
                    if re.search(patterns[i]["Path"], candidate_file):
                        copy_this, extension = check_file(candidate_file)
                        file_types.add(extension)
                        if copy_this:
                            dest = os.path.join(dest_path, file_name)
                            file_size = os.path.getsize(candidate_file)
                            total_bytes += file_size
                            files_to_copy.append(file_spec(candidate_file, dest, file_size, file_name, extension))
                    else:
                        # print('skipped')
                        pass
        if files_to_copy:
            print(f'found {len(files_to_copy)} files to copy ({total_bytes} bytes)')
            bytes_moved = 0
            for file in files_to_copy:
                copyfile(file.source, file.dest)
                bytes_moved += file.file_size
                print(f'\rcopying files... ({(100*bytes_moved)//total_bytes}%)', end='')
                stdout.flush()
            print('\n')

            for extension in file_types:
                if extension:
                    filtered = [f for f in files_to_copy if f.extension == extension]
                    last = sorted(filtered, key=lambda f: f.file_name, reverse=True)[0]
                    self.d[self.camera_id]['Properties']['Patterns'][extension]['Last'] = last.file_name
            self.write_file()
        else:
            print('no files to copy')