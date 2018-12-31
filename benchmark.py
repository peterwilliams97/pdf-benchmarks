"""
   Compare unidoc to poppler for text extraction over a corpus.

   Usage: python benchmark.py ~/testdata/*.pdf ~/testdata/**/*.pdf

"""
import sys
from os.path import getsize, basename
from collections import defaultdict
import hashlib
import os
import re
from subprocess import call, Popen, PIPE
import spacy


SHA1_LEN = 10         # We use the first 10 hex characters of PDF files SHA-1 hash for indexing.
MB = 1024.0 * 1024.0
TMP = 'temp.txt'


def read(path):
    "read returns the contents of text file `path`"
    with open(path, 'rt') as f:
        return f.read()


def write(path, text):
    "write writes the string `text` to file `path`"
    with open(path, 'wt') as f:
        f.write(text)


def file_sha1(path):
    "file_sha1 returns the first 10 hex characters of the SHA-1 hash of file `path`."
    with open(path, 'rb') as f:
        data = f.read()
    sha1 = hashlib.sha1(data).hexdigest()
    return sha1[:SHA1_LEN].rjust(SHA1_LEN, '0')


RE_PATH = re.compile('Input file:\\s*(.+?)\\s*$')
RE_VERSION = re.compile('PDF Version:\\s*(\\d+\\.\\d+)?')
RE_PAGES = re.compile('Num Pages:\\s*(\\d+)$')
RE_ENCRYPTED = re.compile('Is Encrypted:\\s*(true|false)')
RE_VIEWABLE = re.compile('Is Viewable \\(without pass\\):\\s*(true|false)')


def get_val(regex, lines):
    llines = lines.split('\n')
    for line in llines:
        m = regex.search(line)
        if m:
            return m.group(1)
    return None


def parse_info(output):
    """
        PDF Version: 1.5
        Num Pages: 248
        Is Encrypted: false
        Is Viewable (without pass): true
    """
    path = get_val(RE_PATH, output)
    info = {
        'path': path,
        'size': getsize(path) / MB
    }
    version = get_val(RE_VERSION, output)
    if version is not None:
        info['version'] = version
    pages = get_val(RE_PAGES, output)
    if pages is not None:
        info['pages'] = int(pages)
    encrypted = get_val(RE_ENCRYPTED, output)
    if encrypted is not None:
        info['encrypted'] = encrypted == 'true'
    viewable = get_val(RE_VIEWABLE, output)
    if viewable is not None:
        info['viewable'] = viewable == 'true'
    return info


def pdf_info(path):
    process = Popen(['./pdf_info', path], stdout=PIPE, universal_newlines=True)
    output, err = process.communicate()
    exit_code = process.wait()
    if exit_code != 0:
        return {'path': path, 'size': getsize(path)}
    info = parse_info(output)
    assert info['path'] == path, (path, info, output)
    return info


def read_info(info_path):
    with open(info_path, 'rt') as f:
        output = f.read()
    # output = read(info_path)
    return parse_info(output)


def write_info(info_path, info):
    parts = [
        'Input file: %s\n' % info['path'],
        'Size: %.3f MB\n' % info['size'],
    ]
    if 'version' in info:
        parts.extend([
        'PDF Version: %s\n' % info['version'],
        'Num Pages: %d\n' % info['pages'],
        'Is Encrypted: %s\n' % str(info['encrypted']).lower(),
        'Is Viewable (without pass): %s\n' % str(info['viewable']).lower(),
    ])
    write(info_path, ''.join(parts))


def info_str(info, with_path=True):
    if not info_good(info):
        msg ='INVALID %5.3f MB' % info['size']
    else:
        version = info['version']
        if version is None:
            version = '---'
        msg = '[%s] %5.3f MB %3d pages' % (version, info['size'], info['pages'])
    if with_path:
        msg = '%s %s' % (msg, info['path'])
    return msg


def info_good(info):
    if not info:
        return False
    return all((key in info) for key in ['version', 'pages'])


RE_SECTION = re.compile(r'========= Subtype\s+(.+?)\s+[=]+ Subtype', re.DOTALL)
RE_SUBTYPE = re.compile(r'\d+: (Type\d+\S*)\s+\d+\s+occurrences', re.DOTALL | re.MULTILINE)


def parse_fonts(text):
    """
        ===================================================== Subtype
        All versions
        1 files tested
        15 font subtype occurrences
        2 subtypes
         0: Type0:CIDFontType0    2 occurrences (13%) Occurred in   1 (100%) of files.
         1: Type1                13 occurrences (87%) Occurred in   1 (100%) of files.
        ===================================================== Subtype
    """
    m = RE_SECTION.search(text)
    if not m: return {}
    assert m, text
    section = m.group(1)
    subtypes = defaultdict(int)
    for m in RE_SUBTYPE.finditer(section):
        subtypes[m.group(1)] += 1
    return subtypes


def pdf_fonts(path):
    process = Popen(['./pdf_fonts', path], stdout=PIPE, universal_newlines=True)
    output, err = process.communicate()
    exit_code = process.wait()
    if exit_code != 0:
        return {}
    try:
        fonts = parse_fonts(output)
    except AssertionError:
        print('>>>>>>>>path=%s' % path, file=sys.stderr)
        raise
    return {k: v for k, v in fonts.items()}


def read_fonts(font_path):
    return parse_fonts(read(font_path))


def write_fonts(font_path, fonts):
    parts = []
    parts.append('===================================================== Subtype\n')
    for i, (font, count) in enumerate(sorted(fonts.items())):
        parts.append('%d: %s %d occurrences \n' % (i, font, count))
    parts.append('===================================================== Subtype\n')
    write(font_path, ''.join(parts))


def run_mutool(path, tmp_path):
    call(['mutool', 'draw', '-F', 'txt', '-o', tmp_path, path])


def run_pstopdf(path, tmp_path):
    call(['pdftotext', '-enc', 'UTF-8', path, tmp_path])


PDFBOX_app = '~/pdf/pdfbox.orig/app/target/pdfbox-app-2.0.9-SNAPSHOT.jar'
PDFBOX_app = os.path.expanduser(PDFBOX_app)


def run_pdfbox(path, tmp_path):
    process = Popen(['java', '-jar', PDFBOX_app, 'ExtractText', '-sort', path, tmp_path],
        stdout=PIPE, stderr=PIPE, universal_newlines=True)
    output, err = process.communicate()
    exit_code = process.wait()


def run_unidoc(path, tmp_path):
    call(['./pdf_to_text', path, tmp_path])


def exec_runner(path, runner, tmp_path):
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    runner(path, tmp_path)
    return os.path.exists(tmp_path)


def run_test(path, runner, tmp_path, dest):
    if os.path.exists(dest):
        return True
    if not exec_runner(path, runner, tmp_path):
        return False
    os.rename(tmp_path, dest)
    return True


RE_SPACE = re.compile(r'[\n\s]+', re.MULTILINE | re.DOTALL)
nlp = spacy.load('en_core_web_sm')


def tokenize(data):
    """tokenize returns the words in byte array `data`."""
    s = str(data)
    s = RE_SPACE.sub(' ', s)
    doc = nlp(s)
    return [token.text for token in doc]


if False:
    sentence = "It's been a good day. Here is my 1st example?"
    words = tokenize(sentence)
    print(words)
    assert False


def make_path(results_dir, sha1):
    return os.path.join(results_dir, '%10s.txt' % sha1[:10])


def count_set(words):
    word_count = defaultdict(int)
    for w in words:
        word_count[w] += 1
    return {w: c for w, c in word_count.items()}


def diff_count_set(word_count1, word_count2):
    union = set(word_count1) | set(word_count2)
    return {word_count1.get(w, 0) - word_count2.get(w, 0) for w in union}


def word_count_key(diff_count, w):
    return diff_count[w], len(w), w


def word_set_key(w):
    return len(w), w


def diff_words(words1, words2):
    """Returns: diff1-2 diff2-1
        where diff1-2 = words in `words1` that aren't in `words2`
              diff2-1 = words in `words2` that aren't in `words1`
    """
    words1, words2 = set(words1), set(words2)
    return sorted(words1 - words2, key=word_set_key), sorted(words2 - words1, key=word_set_key)


def n_grams(words, n):
    return {' '.join(words[i:i+n]) for i in range(len(words)-n+1)}


def diff_jaccard(words1, words2, n):
    words1, words2 = n_grams(words1, n), n_grams(words2, n)
    num = len(words1 & words2)
    den = len(words1 | words2)
    if den == 0:
        return 1.0

    return 1.0 - num / den


def to_words(path):
    return tokenize(read(path))


def sort_key(path):
    return getsize(path), -path.count('/'), len(basename(path)), path


def get_test_files(argv, max_size_mb=None, max_files=None):
    path_list = sys.argv[1:]
    print('%d files' % len(path_list))
    path_list.sort(key=sort_key)
    if max_size_mb is not None:
        path_list = [path for path in path_list if getsize(path) <= max_size_mb * MB]
        print('%d files < %.1f MB' % (max_size_mb, len(path_list)), flush=True)
    if max_files is not None:
        path_list = path_list[:max_files]
    return path_list


def get_sha1_info(path_list, min_version='1.3', max_pages=100):
    results_dir = os.path.join('results', 'info')
    os.makedirs(results_dir, exist_ok=True)
    path_sha1 = {}
    sha1_info = {}
    for i, path in enumerate(path_list):
        assert path not in path_sha1, path
        sha1 = file_sha1(path)
        if sha1 in sha1_info:
            print('**! DUPLICATE (%d of %d) %s (%s)' % (i + 1, len(path_list), path,
                sha1_info[sha1]), flush=True)
            continue
        info_path = os.path.join(results_dir, '%s.info' % sha1)
        if os.path.exists(info_path):
            info = read_info(info_path)
        else:
            info = pdf_info(path)
            write_info(info_path, info)

        if not info_good(info) or info['encrypted'] or not info['viewable'] or info['version'] < min_version:
            print('**- %s (%d of %d) %s' % (info_str(info, False), i + 1, len(path_list), path), flush=True)
            continue
        if info['pages'] > max_pages:
            print('**+ %s (%d of %d) %s' % (info_str(info, False), i + 1, len(path_list), path), flush=True)
            continue

        font_path = os.path.join(results_dir, '%s.fonts' % sha1)
        if os.path.exists(font_path) and False:
            font = read_fonts(font_path)
        else:
            fonts = pdf_fonts(path)
            write_fonts(font_path, fonts)

        if 'Type3' in fonts or 'Type0:CIDFontType0' in fonts:
            print('**x %s (%d of %d) %s' % (fonts, i + 1, len(path_list), path), flush=True)
            continue

        path_sha1[path] = sha1
        sha1_info[sha1] = info

    path_list = [path for path in path_list if path in path_sha1]
    return path_list, path_sha1, sha1_info


TESTS = {
    # 'ghostscript': run_mutool,
    'poppler': run_pstopdf,
    # 'pdfbox': run_pdfbox,
    'unidoc': run_unidoc,
}


def main():
    path_list = get_test_files(sys.argv)
    print('get_test_files: %d files' % len(path_list))
    path_list, path_sha1, sha1_info = get_sha1_info(path_list)
    print('get_sha1_info: %d files' % len(path_list))

    # Run the runners on all the files in `path_list`.
    for test in sorted(TESTS):
        runner = TESTS[test]
        tmp_path = os.path.join('results', 'tmp.%s.txt' % test)
        results_dir = os.path.join('results', test)
        os.makedirs(results_dir, exist_ok=True)
        for path in path_list:
            if path not in path_sha1:
                print("Duplicate?: %s" % path)
                continue
            sha1 = path_sha1[path]
            info = sha1_info[sha1]
            dest = make_path(results_dir, sha1)
            if not run_test(path, runner, tmp_path, dest):
                print('%s failed. %s' % (test, info_str(info)), flush=True)

    # Reader the runners' extracted texts.
    print('+' * 80, flush=True)
    sha1_successes = defaultdict(list)
    for i, path in enumerate(path_list):
        sha1 = path_sha1[path]

        dests = [make_path(os.path.join('results', test), sha1) for test in TESTS]
        successes = [dst for dst in dests if os.path.exists(dst)]
        if len(successes) != len(TESTS):
            print('No match: %s' % dests)
            continue

        num_words = 0
        try:
            num_words = sum(len(read(dest)) for dest in successes)
        except UnicodeDecodeError:
            print("@@@@@ Could not read path=%s %s " % (path, successes))
            continue
        if num_words < 100:
            continue
        sha1_successes[sha1] = successes
        # if len(sha1_successes) >= 20:
        #     break

    # Compute differences between the results.
    print('#' * 80, flush=True)
    scores = {}
    name_sha1 = {}
    for sha1, paths in sorted(sha1_successes.items()):
        path1, path2 = paths
        name = os.path.basename(path1)
        try:
            words1, words2 = to_words(path1), to_words(path2)
        except UnicodeDecodeError:
            print("@@@@@ Could not read path1=%s path1=%s " % (path1, path2))
            continue
        diff1, diff2 = diff_words(words1, words2)
        jac = [diff_jaccard(words1, words2, n) for n in (1, 2, 3)]
        scores[name] = jac
        name_sha1[name] = sha1
        info = sha1_info[sha1]
        print("$" * 80)
        print("name=%s jac=%.2f %.2f %.2f n=%d %d %s" % (
            name, jac[0], jac[1], jac[2], len(words1), len(words2), info_str(info)))
        print("1) %d %s" % (len(diff1), diff1[:10]))
        print("2) %d %s" % (len(diff2), diff2[:10]), flush=True)

    print("&" * 80)
    for i, name in enumerate(sorted(scores, key=lambda n: (scores[n][0], scores[n][1], scores[n][2], n))):
        info = info_str(sha1_info[name_sha1[name]])
        print('%4d %.3f %.3f %.3f: %s %s' % (i, scores[name][0], scores[name][1], scores[name][2], name, info))

    jac_mean = [0.0, 0.0, 0.0]
    if scores:
        for i in 0, 1, 2:
            for jac in scores.values():
                jac_mean[i] += jac[i]
            jac_mean[i] /= len(scores)

    print(';' * 80)
    print('%d files compared' % len(scores))
    print('mean=%.3f %.3f %.3f' % (jac_mean[0], jac_mean[1], jac_mean[2]))


main()
