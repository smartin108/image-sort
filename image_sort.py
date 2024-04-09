"""

Notes about prior versions were offloaded to a separate file 20220301

feature-20240217: adding a card id to the json storage, cleanups

    ... which is currently undergoing scope-creep

        but I need to add another thing or two. 
            after transfer, report out the volume use and capacity,
            preferably in terms of the semantic scale you defined somewhere
                lol, today

feature-20240229: Leap Day Edition!

    *   Objective: Add a report showing utilzation of the removable storage
    The CEO was just quoted as saying "this is perfect! Thumbs-up to the 
    developer!" as he emphatically waved a thumbs-up. 

feature-20240301: In which we endeavor to eliminate the scolling updates 
    once and for all!


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
import re
import banner

global_window_width = 100 # characters; hopefully this is conservative
target_exif_tags = ['xImage DateTime', 'Image Make', 'Image Model', 'EXIF DateTimeOriginal']
default_root = '/home/andy/Pictures/sorted'


def sleep_with_feedback(message='', sleep_time:float=5.0, trailing_spaces:int=5):
    """display a countdown timer while sleeping"""
    if sleep_time < 0.5:
        sleep(sleep_time)
    else:
        countdown = floor(sleep_time)
        while countdown > -1e-10:
            regular_message = message.replace('%', str(int(countdown)))
            stdout.write(f'\r{regular_message}{" "*trailing_spaces}')
            stdout.flush()
            sleep(0.1)
            countdown -= 0.1
        print('\n')
    return 1


def shorten(message, char_count):
    """shrink a long name so it fits on the screen"""
    if len(message) > char_count:
        return message[:char_count//2-4] + ' ... ' + message[-char_count//2+4:]
    else:
        return message


def get_file_extension(filename):
    return filename.split('.')[-1].lower()


def make_short_date(long_date):
    std_date = datetime.datetime.strptime(long_date, '%Y:%m:%d %H:%M:%S')
    return f'{std_date.year}-{std_date.month:02}-{std_date.day:02}'


def ignore_path(pathname: str):
    """it's best to ignore some folders:
        ignore designated folders
        ignore folders that are likely already processed camera files"""
    camera_type_path = r'^.*\d{4}-\d{2}-\d{2} \w+ [\w\-]+[ \(raw\)]*$'
    ignore = False
    if '.ignore' in pathname.lower():
        ignore = True
    elif re.match(camera_type_path, pathname):
        ignore = True
    return ignore


def get_disk_util(db:JSONDb):
    proxy_jpg_size = 5839000
    proxy_raw_size = 19495000
    remote_storage_device_name = db.get_storage_device()
    util = shutil.disk_usage(remote_storage_device_name)
    used_bytes = util.used
    free_bytes = util.free
    total_bytes = util.total
    percent_used = (100.5*used_bytes)//total_bytes
    percent_free = (100.5*free_bytes)//total_bytes
    remaining_jpg = free_bytes // proxy_jpg_size
    remaining_raw = free_bytes // proxy_raw_size
    if remaining_jpg < 500:
        warn = '!!!'
    elif remaining_jpg < 2000:
        warn = '!'
    else:
        warn = ''
    report = \
    f"""

Disk Report for {remote_storage_device_name}

            {'bytes':>15}
    used    {used_bytes:>15,}   ({percent_used}%)
    free    {free_bytes:>15,}   ({percent_free}%)   ({remaining_jpg} jpg / {remaining_raw} raw) {warn}
    total   {total_bytes:>15,}

    """
    return report


print(f'\n{banner.banner}\n')
# print('\n\n\n                             *** Image Sorter ***\n\n')

image_exif_dict = {}
try:
    requested_root = sys.argv[1]
except IndexError as e:
    requested_root = None

if requested_root:
    source_root = requested_root
    accept_default = input(f'Continue with {requested_root} ? (y/Y/1 to accept, any other to abort) ')
    if not accept_default.lower() in ['y','1']:
        sleep_with_feedback(r'halting in % seconds',5)
        exit()
else:
    source_root =  default_root
    try:
        db = JSONDb(f='db.json')
        disk_util_report = get_disk_util(db)
        print(disk_util_report)
        db.copy_files()
    except PermissionError:
        sleep_with_feedback('Continuing in %', 5)
target_root =  source_root
print(f'source_root resolves as {source_root}')


# Plant a dummy file in the source folder. 
# This intentionally has .jpg extension but no EXIF data. An error is thrown later, which we can handle gracefully.
# This seems to make the PermissionError go away. #KLUDGE
dummy_filename = '___ImageSorterTempFile___.jpg' 
with open(source_root+dummy_filename, 'w') as f:    
    f.write('made you look!')


# loop through files and read EXIF
skipped = []
for dirpath, dirnames, filenames in os.walk(source_root):
    if not ignore_path(dirpath):
        file_count = len(filenames)
        my_count = 0
        my_count_length = len(str(my_count))
        for filename in filenames:
            file_metadata = {}
            ticker = f'\rreading {my_count}/{file_count}: '
            status_message = f'{ticker}{shorten(dirpath+"/"+filename,(global_window_width-21)-len(ticker))} ({get_file_extension(filename)})'
            spaces = global_window_width-len(status_message)
            if spaces < 0:
                spaces = 0
            stdout.write(f'\r{status_message}{" "*spaces}')
            stdout.flush()
            source_rel_path = os.path.join(dirpath, filename)
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

print(f'\n\ndiscovered {len(image_exif_dict)} files with EXIF data')

# this needs to be split up so badly lol
# #features as commits lol

print(f'\n\nreorganizing files...\n')
i = 0
for (source_rel_path, file_metadata) in image_exif_dict.items():
    i += 1
    try:
        folder_date = make_short_date(file_metadata['EXIF DateTimeOriginal'])
    except KeyError as e:
        folder_date = '!Date'
    try:
        camera_make = file_metadata['Image Make']
    except KeyError as e:
        camera_make = '!Make'
    try:
        camera_model = file_metadata['Image Model']
    except KeyError as e:
        camera_model = '!Model'

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
        status_message = f'\rmoving {i}/{len(image_exif_dict.items())}: {shorten(source_rel_path, global_window_width-40)}'
        spaces = global_window_width-len(status_message)
        if spaces < 0:
            spaces = 0
        stdout.write(f'\r{status_message}{" "*spaces}')
        stdout.flush()
        shutil.move(source_rel_path, target_path)
    except PermissionError:
        print(f'\n\n>>>  {source_rel_path}\n>>>  PermissionError ignored during processing. A copy of this file might be in the target folder\n>>>  {target_folder}')
    except shutil.SameFileError: 
        print(f'\n\n>>>  {source_rel_path}\n>>>  SameFileError ignored during processing. A copy of this file might be in the target folder\n>>>  {target_folder}')


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

print('EOJ')

if requested_root:
    print('\n\ndone. you can safely close this window')
    sleep_with_feedback(r'this window will close automatically in % seconds',1000)
else:
    print('\n')
    sleep_with_feedback(r'this window will close automatically in % seconds',5)

