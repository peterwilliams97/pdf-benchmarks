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


MB = 1024.0 * 1024.0
TMP = 'temp.txt'


def read(path):
    with open(path, 'rt') as f:
        return f.read()


def file_sha1(path):
    with open(path, 'rb') as f:
        data = f.read()
    return hashlib.sha1(data).hexdigest()


RE_VERSION = re.compile(r'PDF Version:\s*(\d+\.\d+)?')
RE_PAGES = re.compile(r'Num Pages:\s*(\d+)')
RE_ENCRYPTED = re.compile(r'Is Encrypted:\s*(true|false)')
RE_VIEWABLE = re.compile(r'Is Viewable \(without pass\):\s*(true|false)')


def get_val(regex, output):
    m = regex.search(str(output))
    assert m, (regex.pattern, output)
    val = m.group(1)
    # assert val is not None
    # assert val != 'None'
    return val


def pdf_info(path):
    """
        PDF Version: 1.5
        Num Pages: 248
        Is Encrypted: false
        Is Viewable (without pass): true
    """
    process = Popen(['./pdf_info', path], stdout=PIPE)
    output, err = process.communicate()
    exit_code = process.wait()
    if exit_code != 0:
        return {}
    return {
        'path': path,
        'size': getsize(path) / MB,
        'version': get_val(RE_VERSION, output),
        'pages': int(get_val(RE_PAGES, output)),
        'encrypted': get_val(RE_ENCRYPTED, output) == 'true',
        'viewable': get_val(RE_VIEWABLE, output) == 'true',
    }


def info_str(info, with_path=True):
    if not info:
        return 'INVALID'
    version = info['version']
    if version is None:
        version = '---'
    msg = '[%s] %5.3f MB %3d pages' % (version, info['size'], info['pages'])
    if with_path:
        msg = '%s %s' % (msg, info['path'])
    return msg


def run_mutool(path, tmp_path):
    call(['mutool', 'draw', '-F', 'txt', '-o', tmp_path, path])


def run_pstopdf(path, tmp_path):
    call(['pdftotext', '-enc', 'UTF-8', path, tmp_path])


def run_unidoc(path, tmp_path):
    print('run_unidoc:', ['./pdf_to_text', path, tmp_path])
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
    """tokenize returns the words in byte array `data`"""
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
    path_sha1 = {}
    sha1_info = {}
    for i, path in enumerate(path_list):
        assert path not in path_sha1, path
        sha1 = file_sha1(path)
        if sha1 in sha1_info:
            print('**! DUPLICATE (%d of %d) %s (%s)' % (i + 1, len(path_list), path,
                sha1_info[sha1]), flush=True)
            continue
        info = pdf_info(path)
        if not info or info['encrypted'] or not info['viewable'] or info['version'] < min_version:
            print('**- %s (%d of %d) %s' % (info_str(info, False), i + 1, len(path_list), path), flush=True)
            continue
        if info['pages'] > max_pages:
            print('**+ %s (%d of %d) %s' % (info_str(info, False), i + 1, len(path_list), path), flush=True)
            continue
        path_sha1[path] = sha1
        sha1_info[sha1] = info

    path_list = [path for path in path_list if path in path_sha1]
    return path_list, path_sha1, sha1_info


TESTS = {
    # 'ghostscript': run_mutool,
    'poppler': run_pstopdf,
    'unidoc': run_unidoc,
}


def main():
    path_list = get_test_files(sys.argv)
    print('get_test_files: %d files' % len(path_list))
    path_list, path_sha1, sha1_info = get_sha1_info(path_list)
    print('get_sha1_info: %d files' % len(path_list))

    # Run the runners on all the files in path_list.
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

    print('#' * 80)
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
        print("2) %d %s" % (len(diff2), diff2[:10]))

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
