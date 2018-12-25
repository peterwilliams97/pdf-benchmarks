import re
import os


def get_lines(path):
    lines = []
    with open(path, 'rt') as f:
        for ln in f:
            lines.append(ln.rstrip('\n'))
    return lines


# private static final Object[][] STANDARD_ENCODING_TABLE = {
start_re = re.compile(r'^\s*private\s+static\s+final.*TABLE\s*=\s*\{\s*$')
# };
end_re = re.compile(r'^\s*\}\s*;\s*$')
# {0350, "Lslash"},
line_re = re.compile(r'\{\s*(\d+)\s*,\s*"(.*?)"\s*\}\s*')

if True:
    s1 = '  private static final Object[][] STANDARD_ENCODING_TABLE = {  '
    s2 = '    };  '
    s3 = ' {0350, "Lslash"}, '
    s4 = '            {0101, "A"},'
    m1 = start_re.search(s1)
    assert m1, s1
    m2 = end_re.search(s2)
    assert m2, s2
    m3 = line_re.search(s3)
    assert m3, s3
    m4 = line_re.search(s4)
    assert m4, s4

ENCODING_DIR = '/Users/pcadmin/pdf/pdfbox.orig//pdfbox/src/main/java/org/apache/pdfbox/pdmodel/font/encoding'
STANDARD_ENCODING = 'StandardEncoding.java'
SYMBOL_ENCODING = 'SymbolEncoding.java'

lines = get_lines(os.path.join(ENCODING_DIR, SYMBOL_ENCODING))
enc_lines = []
in_enc = False

code_glyph = {}
for i, ln in enumerate(lines):
    m = start_re.search(ln)
    if m is not None:
        assert not in_enc, (i, ln)
        in_enc = True
        continue
    if in_enc:
        m = end_re.search(ln)
        if m is not None:
            break
        m = line_re.search(ln)
        assert m, (i, ln)
        code = int(m.group(1), 8)
        glyph = m.group(2)
        code_glyph[code] = glyph

print('%d codes' % len(code_glyph))
for i, code in enumerate(sorted(code_glyph)):
    glyph = code_glyph[code]
    print('%3d: %04o=0x%02x=%d "%s"' % (i, code, code, code, glyph))
