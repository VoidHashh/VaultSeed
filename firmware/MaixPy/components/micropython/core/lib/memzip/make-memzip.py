#!/usr/bin/env python
#
# Takes a directory of files and zips them up (as uncompressed files).
# This then gets converted into a C data structure which can be read
# like a filesystem at runtime.
#
# This is somewhat like frozen modules in python, but allows arbitrary files
# to be used.

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import types
import zipfile

def create_zip(zip_filename, zip_dir):
    """
    Create a zip file from the contents of the given directory.
    Sorting them for better reproducibility.
    """
    abs_zip_filename = os.path.abspath(zip_filename)
    save_cwd = os.getcwd()
    os.chdir(zip_dir)

    if os.path.exists(abs_zip_filename):
        os.remove(abs_zip_filename)

    with zipfile.ZipFile(abs_zip_filename, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk('.'):
            dirs.sort()  # Sort directories
            files.sort()  # Sort files
            for file in files:
                file_path = os.path.join(root, file)
                if file_path.endswith(('.py', '.md')):  # Check if the file is a Python or Markdown file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Converts every line ending to '\n' (LF)
                    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.write(content)
                
                # Set the timestamp to the time the Bitcoin genesis block was mined
                os.utime(file_path, (1231006505, 1231006505))  # January 3, 2009, 18:15:05 UTC

                # Set to a uniform file permission
                os.chmod(file_path, 0o0644)
                
                zipf.write(file_path, arcname=os.path.relpath(file_path, start=zip_dir))

    os.chdir(save_cwd)


def create_c_from_file(c_filename, zip_filename):
    with open(zip_filename, 'rb') as zip_file:
        with open(c_filename, 'w') as c_file:
            print('#include <stdint.h>', file=c_file)
            print('', file=c_file)
            print('const uint8_t memzip_data[] = {', file=c_file)
            while True:
                buf = zip_file.read(16)
                if not buf:
                    break
                print('   ', end='', file=c_file)
                for byte in buf:
                    print(' 0x{:02x},'.format(byte), end='', file=c_file)
                print('', file=c_file)
            print('};', file=c_file)

def main():
    parser = argparse.ArgumentParser(
        prog='make-memzip.py',
        usage='%(prog)s [options] [command]',
        description='Generates a C source memzip file.'
    )
    parser.add_argument(
        '-z', '--zip-file',
        dest='zip_filename',
        help='Specifies the name of the created zip file.',
        default='memzip_files.zip'
    )
    parser.add_argument(
        '-c', '--c-file',
        dest='c_filename',
        help='Specifies the name of the created C source file.',
        default='memzip_files.c'
    )
    parser.add_argument(
        dest='source_dir',
        default='memzip_files'
    )
    args = parser.parse_args(sys.argv[1:])

    print('args.zip_filename =', args.zip_filename)
    print('args.c_filename =', args.c_filename)
    print('args.source_dir =', args.source_dir)

    create_zip(args.zip_filename, args.source_dir)
    create_c_from_file(args.c_filename, args.zip_filename)

if __name__ == "__main__":
    main()

