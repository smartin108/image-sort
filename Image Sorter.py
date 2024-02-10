"""
This script will examine EXIF data of JPG files in the current directory,
create a folder for each unique Image DateTime, and move the image to that folder.

For now it's janky: Copy your pictures to ./source and run the script. Processed
files will be placed in subfolders of ./done by date+camera make+camera model.

Do be careful
*   Work with copies! 
*   Images without EXIF cannot be parsed with this. They will simply
remain behind in the root folder.
*   non-JPG files will be ignored as well, and remain behind in the root folder

Change Log:

2022 01 29 AH - New
2022 08 13 AH - New features:
    *   Now uses ./source folder for source files, ./done for processed files
    *   Now parses all files and files in subfolders of ./source
    *   Now reads camera make and model from EXIF data and builds a target folder name with that information
        *   NOTE this is irrespective of which subfolder the source file was found in
    *   Better comunication of files that were not processed
    *   Removes source folders that are empty after reorganizing their contents
2023 09 28 AH v3.1 - in which we move the data storage to a different drive
2024 01 14 AH v3.3 - New features:
    *   now accepts optional root folder to parse as a sys.argv via Windows SendTo
        *   invoke it from Windows Explorer as a folder action!
    *   clearer progress feedback
    *   now puts files with EXIF read errors in a Default Location instead of skipping them
2024 02 10 AH
    *   Source now managed in Git repo
    *   Added JSONDb automated file tracking, fulfilling this feature request:
        *   Automatically read requested storage device and figure out what needs to be offloaded to
            source_root. Journal the devices & files copied so you know where to ontinue on next run.
            Bonus round: log each file type the camera is capable of separately, e.g., JPG and
            whatever video formats it supports.


Bugs & Feature Reqs:

    *   Designate a folder in source_root that will be ignored. So that you can dump processed files 
            here before offloading them to permanent storage.


"""

import os
import exifread
import datetime
import shutil
from sys import exit
from sys import stdout
import sys
from time import sleep
from pprint import pprint
from math import floor
from JSONDb import JSONDb

target_exif_tags = ['xImage DateTime', 'Image Make', 'Image Model', 'EXIF DateTimeOriginal']

def sleep_with_feedback(message='', sleep_time:float=5.0, trailing_spaces:int=5):
    """display a countdown timer while sleeping"""
    if sleep_time < 0.5:
        sleep(sleep_time)
    else:
        countdown = floor(sleep_time)
        while countdown > 0:
            regular_message = message.replace('%', str(int(countdown)))
            sys.stdout.write(f'\r{regular_message}{" "*trailing_spaces}')
            sys.stdout.flush()
            sleep(1)
            countdown -= 1
        print('\n')
    return 1


def shorten(message, char_count):
    """shrink a long name so it fits on the screen"""
    if len(message) > char_count:
        return message[:char_count//2-4] + ' ... ' + message[-char_count//2+4:]
    else:
        return message


print('*** Image Sorter ***\n\n')

db = JSONDb(f='db.json', reset=1)
db.find_folders()

image_exif_dict = {}
try:
    requested_root = sys.argv[1]
except IndexError as e:
    requested_root = None

if requested_root:
    source_root = requested_root
    accept_default = input(f'Continue with {requested_root} ? (default:no) ')
    if not accept_default.lower() in ['y','1']:
        sleep_with_feedback(r'halting in % seconds',5)
        exit()
else:
    source_root =  r'H:/Camera Rips'
target_root =  source_root
skipped = []
print(f'source_root resolves as {source_root}')
sleep_with_feedback(r'continuing in % seconds', 2)


# Plant a dummy file in the source folder. 
# This intentionally has .jpg extension but no EXIF data. An error is thrown later, which we can handle gracefully.
# This seems to make the PermissionError go away. #KLUDGE
dummy_filename = 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzlol.jpg' 
with open(source_root+dummy_filename, 'w') as f:
    f.write('made you look!')


def get_file_extension(filename):
    return filename.split('.')[-1].lower()


def make_short_date(long_date):
    std_date = datetime.datetime.strptime(long_date, '%Y:%m:%d %H:%M:%S')
    return f'{std_date.year}-{std_date.month:02}-{std_date.day:02}'


for dirpath, dirnames, filenames in os.walk(source_root):
    file_count = len(filenames)
    my_count = 0
    my_count_length = len(str(my_count))
    for filename in filenames:
        file_metadata = {}
        ticker = f'\rreading {my_count}/{file_count}: '
        status_message = f'{ticker}{shorten(dirpath+filename,100-len(ticker))} ({get_file_extension(filename)})'
        print(f'{status_message}{" "*(119-len(status_message))}', end='')
        stdout.flush()
        source_rel_path = f'{dirpath}\\{filename}'
        file_extension = get_file_extension(source_rel_path)
        if file_extension in ['jpg','jpeg','heic','rw2']:
            exif_tags = open(source_rel_path, 'rb')
            tags = exifread.process_file(exif_tags)
            exif_array = []

            for i in tags:
                compile = i, str(tags[i])
                exif_array.append(compile)

            file_metadata['filename'] = filename
            for properties in exif_array:
                if properties[0] in target_exif_tags:
                    file_metadata[properties[0]] = properties[1]

            if file_extension in ['rw2']:
                file_metadata['raw'] = True
            else:
                file_metadata['raw'] = False

            image_exif_dict[source_rel_path] = file_metadata
        elif file_extension in ['mp4','mpg','mpeg','avi','xmov', 'mts']:
            # handle video metadata (not supported yet)
            skipped.append(source_rel_path)
        else:
            skipped.append(source_rel_path)
        my_count += 1
print('\n')

print(f'\n\ndiscovered {len(image_exif_dict)} files with EXIF data')

print(f'\n\nreorganizing files...\n')
i = 0
for (source_rel_path, file_metadata) in image_exif_dict.items():
    i += 1
    try:
        folder_date = make_short_date(file_metadata['EXIF DateTimeOriginal'])
    except KeyError as e:
        folder_date = '!Default Date'
    try:
        camera_make = file_metadata['Image Make']
    except KeyError as e:
        camera_make = '!Default Make'
    try:
        camera_model = file_metadata['Image Model']
    except KeyError as e:
        camera_model = '!Default Model'

    # I think this is going to fail the next time you hit a folder with raw files
    if file_metadata['raw']:
        target_folder = f'{target_root}/{folder_date} {camera_make} {camera_model} (raw)/'
    else:
        target_folder = f'{target_root}/{folder_date} {camera_make} {camera_model}/'

    try:
        os.mkdir(target_folder)
    except FileExistsError:
        pass
    except OSError as e:
        print(f'\n\n\nYOW! I crashed processing {source_rel_path}\nWhile trying to create {target_folder}, this happened:\n{str(e)})')
        exit()
    
    try:
        target_path = target_folder+file_metadata['filename']
        status_message = f'\rmoving {i}/{len(image_exif_dict.items())}: {shorten(source_rel_path, 80)}'
        print(f'{status_message}{" "*(119-len(status_message))}', end='')
        stdout.flush()
        shutil.move(source_rel_path, target_path)
    except PermissionError:
        print(f'\n\n>>>  {source_rel_path} <-- PermissionError ignored during processing. A copy of this file might be in the target folder {target_folder}')
    except shutil.SameFileError: 
        print(f'\n\n>>>  {source_rel_path} <-- SameFileError ignored during processing. A copy of this file might be in the target folder {target_folder}')


print('\n')
sleep_with_feedback('cleaning up source folders in %', 3)
# print('cleaning up source folders...')
for dirpath, dirnames, filenames in os.walk(source_root, topdown=False):
    try:
        thumb = f'{dirpath}\\Thumbs.db'
        os.remove(thumb)
    except FileNotFoundError:
        pass
    if not (dirnames or filenames) and dirpath != source_root:
        print(f'removing folder {dirpath}')
        os.rmdir(dirpath)


try:
    os.remove(source_root+dummy_filename)
except PermissionError:
    print('could not remove dummy file')


if requested_root:
    print('\n\ndone. you can safely close this window')
    sleep_with_feedback(r'this window will close automatically in % seconds',1000)
else:
    sleep_with_feedback(r'this window will close automatically in % seconds',1000)
print('\n\ndone.')