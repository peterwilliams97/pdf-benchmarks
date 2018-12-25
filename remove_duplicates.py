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
import os


MB = 1024.0 * 1024.0


def sort_key(path):
    return getsize(path), -path.count('/'), len(basename(path)), path


path_list = sys.argv[1:]
print('%d files' % len(path_list))
path_list.sort(key=sort_key)


def file_sha1(path):
    with open(path, 'rb') as f:
        data = f.read()
        return hashlib.sha1(data).hexdigest()


for i, path in enumerate(path_list[:10]):
    print('%4d: %6.3f MB %s "%s"' % (i, getsize(path)/MB, file_sha1(path), path))

print("-" * 80)
hash_path = {}
duplicate_paths = defaultdict(list)
for i, path in enumerate(path_list):
    sha1 = file_sha1(path)
    if sha1 in hash_path:
        path0 = hash_path[sha1]
        print('%4d: %6.3f MB "%s"\n\t\t"%s"' % (i, getsize(path)/MB, path, path0))
        duplicate_paths[path0].append(path)
    hash_path[sha1] = path

print("=" * 80)
print('%d duplicate_paths' % len(duplicate_paths))
for i, path0 in enumerate(sorted(duplicate_paths, key=getsize)):
    print('%4d:     "%s"' % (i, path0))
    for j, path in enumerate(duplicate_paths[path0]):
        print('%8d: "%s"' % (j, path))

duplicates = []
for path0 in sorted(duplicate_paths, key=getsize):
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
    os.rename(path, dest)
    print('%4d: "%s"→"%s"' % (i, path, dest))


