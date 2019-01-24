"""
    Compare various pdf→text converters.
    1) Build map of files in corpus keyed on sha-1 hash of files (to remove duplicate_paths)
    2) Map value contains
        original file name
        file size
        number of PDF pages
        number of words in pdftotext
    3) Run pdf→text converter and save results as results/<converter name>/<hash>.txt
    4) Run text similarity algo
"""
import sys
from os.path import getsize, basename
import hashlib
from collections import defaultdict
from glob import glob
import os
from shutil import move


MB = 1024.0 * 1024.0


def my_size(path):
    try:
        return getsize(path)
    except:
       print('my_size: path="%s"' % path)
       raise


def my_glob(pattern):
    pattern = os.path.expanduser(pattern)
    if '[' in pattern or ']' in pattern:
        return [pattern]
    try:
        paths = glob(pattern, recursive=True)
    except:
       print('my_glob: pattern="%s"' % pattern)
       raise
    return paths


def file_sha1(path):
    with open(path, 'rb') as f:
        data = f.read()
        return hashlib.sha1(data).hexdigest()


def sort_key(path):
    return path_size[path], -path.count('/'), len(basename(path)), path


pattern_list = sys.argv[1:]
print('%d patterns' % len(pattern_list))
path_list = [path for pattern in pattern_list
                  for path in my_glob(pattern)]
print('%d files' % len(path_list))
path_list = list(set(path_list))
print('%d files (unique)' % len(path_list))

path_size = {path: my_size(path) for path in path_list}
path_list.sort(key=sort_key)
size_path = defaultdict(list)
for path, size in path_size.items():
    size_path[size].append(path)
perc = 100.0 * len(size_path) / len(path_list) if path_list else 0.0
print('%d = %d - %d unique file sizes = %.1f%% = 100%% - %.1f%%' % (
      len(size_path), len(path_list),
      len(path_list) - len(size_path), perc, 100.0 - perc))

for i, path in enumerate(path_list[:10]):
    print('%4d: %6.3f MB %s "%s"' % (i, my_size(path)/MB, file_sha1(path), path))

print("-" * 80)

hash_path = {}
duplicate_paths = defaultdict(list)
for i, path in enumerate(path_list):
    assert size_path[path_size[path]], path
    if len(size_path[path_size[path]]) == 1:
        continue
    sha1 = file_sha1(path)
    if sha1 in hash_path:
        path0 = hash_path[sha1]
        print('%4d: %6.3f MB "%s"\n\t\t"%s"' % (i, path_size[path]/MB, path, path0))
        duplicate_paths[path0].append(path)
    hash_path[sha1] = path

print("=" * 80)
print('%d duplicate_paths' % len(duplicate_paths))
for i, path0 in enumerate(sorted(duplicate_paths, key=getsize)):
    print('%4d:     "%s"' % (i, path0))
    for j, path in enumerate(duplicate_paths[path0]):
        print('%8d: "%s"' % (j, path))

duplicates = []
for path0 in sorted(duplicate_paths, key=sort_key):
    duplicates.extend(duplicate_paths[path0])

print("~" * 80)
print('%d duplicates' % len(duplicates))
for i, path in enumerate(duplicates):
    print('%4d: "%s"' % (i, path))

DUPLICATES = './duplicates'
os.makedirs(DUPLICATES, exist_ok=True)
print("+" * 80)
for i, path in enumerate(duplicates):
    sha1 = file_sha1(path)
    dest = os.path.join(DUPLICATES, sha1)
    move(path, dest)
    print('%4d: "%s"→"%s"' % (i, path, dest))
