"""
   Remove duplicates from a corpus.

   Usage: python remove_duplicates.py ~/testdata/*.pdf ~/testdata/**/*.pdf

"""
import sys
from os.path import getsize, basename
from collections import defaultdict
import hashlib
import os
import re
from subprocess import call, Popen, PIPE
import spacy

nlp = spacy.load('en_core_web_sm')

MB = 1024.0 * 1024.0

# RESULTS_PSTOPDF = 'results.pdftotext'
TMP = 'temp.txt'


RE_VERSION = re.compile(r'PDF Version:\s*(\d+\.\d+)?')
RE_PAGES = re.compile(r'Num Pages:\s*(\d+)')
RE_ENCRYPTED = re.compile(r'Is Encrypted:\s*(true|false)')
RE_VIEWABLE = re.compile(r'Is Viewable \(without pass\):\s*(true|false)')


def get_val(regex, output):
    m = regex.search(str(output))
    assert m, (path, regex.pattern, output)
    return m.group(1)


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


def info_str(info):
    if not info:
        return 'INVALID'
    return '[%s] %5.3f MB %3d pages %s' % (
        info['version'], info['size'], info['pages'], info['path'])


def run_pstopdf(path):
    call(['pdftotext', '-enc', 'UTF-8', path, TMP])


def run_unidoc(path):
    call(['./pdf_to_text', path, TMP])


def read(path):
    with open(path, 'rt') as f:
        return f.read()


def file_sha1(path):
    with open(path, 'rb') as f:
        data = f.read()
    return hashlib.sha1(data).hexdigest()


def sort_key(path):
    return getsize(path), -path.count('/'), len(basename(path)), path


def run_test(path, runner):
    if os.path.exists(TMP):
        os.remove(TMP)
    runner(path)
    if not os.path.exists(TMP):
        return False
    return True
    data = read(TMP)
    return len(data) > 1000 and 'Lorem ipsum' not in data


RE_SPACE = re.compile(r'[\n\s]+', re.MULTILINE | re.DOTALL)


def tokenize(data):
    # print('`' * 80)
    # print(data)
    s = str(data)
    s = RE_SPACE.sub(' ', s)
    # print('"' * 80)
    # print(s)
    # print('*' * 80)
    doc = nlp(s)
    return [token.text for token in doc]


if False:
    sentence = "It's been a good day. Here is my 1st example?"
    words = tokenize(sentence)
    print(words)
    assert False


def make_path(results_dir, i, sha1):
    return os.path.join(results_dir, '%05d-%s.txt' % (i, sha1[:6]))


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


# def diff_jaccard(words1, words2):
#     words1, words2 = set(words1), set(words2)
#     num = len(words1 & words2)
#     den = len(words1 | words2)
#     if den == 0:
#         return 1.0
#     return 1.0 - num / den


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


# def compare_files(path1, path2):
#     return compare(read(path1), read(path2))


TESTS = {
    'poppler': run_pstopdf,
    'unidoc': run_unidoc,
}

path_list = sys.argv[1:]
print('%d files' % len(path_list))
path_list.sort(key=sort_key)
path_list = [path for path in path_list if getsize(path) <= MB]
print('%d files < 1 MB' % len(path_list), flush=True)


for i, path in enumerate(path_list[:10]):
    print('%4d: %s %s' % (i, file_sha1(path), info_str(pdf_info(path))))

for test in TESTS:
    results_dir = 'results.%s' % test
    os.makedirs(results_dir, exist_ok=True)
    # print("-" * 80)

hash_info = {}
test_successes = defaultdict(list)

for i, path in enumerate(path_list):
    sha1 = file_sha1(path)
    assert sha1 not in hash_info
    info = pdf_info(path)
    if not info or info['encrypted'] or not info['viewable'] or info['version'] < '1.3':
        print('**+ %s' % info_str(info))
        continue
    if info['pages'] > 100:
        print('**- %s' % info_str(info))
        continue
    hash_info[sha1] = info

    # if i < 36:
    #     continue
    # elif i > 36:
    #     break

    successes = []
    for test, runner in TESTS.items():
        results_dir = 'results.%s' % test
        dest = make_path(results_dir, i, sha1)
        # if os.path.exists(dest):
        #     continue
        if run_test(path, runner):
            os.rename(TMP, dest)
            successes.append(dest)
        else:
            print('%s failed. %s' % (test, info_str(info)), flush=True)
    if len(successes) != len(TESTS):
        continue
    num_words = 0
    try:
        num_words = len(read(successes[0]))
    except UnicodeDecodeError:
        print("@@@@@ Could not read path=%s %s " % (path, successes[0]))
        continue
    if num_words < 100:
        continue
    test_successes[sha1] = successes
    if len(test_successes) >= 200000:
        break

print('#' * 80)
scores = {}
name_sha1 = {}
for sha1, paths in sorted(test_successes.items()):
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
    info = hash_info[sha1]
    print("$" * 80)
    print("name=%s jac=%.2f %.2f %.2f n=%d %d %s" % (
        name, jac[0], jac[1], jac[2], len(words1), len(words2), info_str(info)))
    print("1) %d %s" % (len(diff1), diff1[:10]))
    print("2) %d %s" % (len(diff2), diff2[:10]))

print("&" * 80)
for i, name in enumerate(sorted(scores, key=lambda n: (scores[n][0], scores[n][1], scores[n][2], n))):
    info = info_str(hash_info[name_sha1[name]])
    print('%4d %.3f %.3f %.3f: %s %s' % (i, scores[name][0], scores[name][1], scores[name][2], name, info))

jac_mean = [0.0, 0.0, 0.0]
for i in 0, 1, 2:
    for jac in scores.values():
        jac_mean[i] += jac[i]
    jac_mean[i] /= len(scores)

print(';' * 80)
print('%d files compared' % len(scores))
print('mean=%.3f %.3f %.3f' % (jac_mean[0], jac_mean[1], jac_mean[2]))
