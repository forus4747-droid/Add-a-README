# -*- coding: utf-8 -*-
"""LibreOffice's round-trip mangles a few font records into <name val="<int>"/>
with every other attribute dropped. Only Sprint-tab cells reference them
(verified), so restore the three intended definitions in place."""
import re, shutil, sys, zipfile

PATH = sys.argv[1]

FIXES = {
    '70': '<font><i val="true"/><sz val="8"/><color rgb="FF808080"/><name val="Arial"/><family val="0"/><charset val="1"/></font>',
    '55': '<font><b val="true"/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Arial"/><family val="0"/><charset val="1"/></font>',
    '56': '<font><b val="true"/><sz val="8"/><color rgb="FFFFFFFF"/><name val="Arial"/><family val="0"/><charset val="1"/></font>',
}

with zipfile.ZipFile(PATH) as z:
    names = z.namelist()
    blobs = {n: z.read(n) for n in names}

styles = blobs['xl/styles.xml'].decode('utf-8')
block = re.search(r'<fonts.*?</fonts>', styles, re.S).group(0)
new_block = block
patched = []
for m in re.finditer(r'<font>(?:(?!</font>).)*?</font>', block, re.S):
    frag = m.group(0)
    nm = re.search(r'<name val="(\d+)"\s*/>', frag)
    if not nm:
        continue
    key = nm.group(1)
    if key not in FIXES:
        raise SystemExit(f'unexpected mangled font name {key!r}: {frag}')
    new_block = new_block.replace(frag, FIXES[key])
    patched.append(key)

if not patched:
    print('nothing to patch')
    sys.exit(0)

styles = styles.replace(block, new_block)
blobs['xl/styles.xml'] = styles.encode('utf-8')

shutil.copy(PATH, PATH + '.bak')
with zipfile.ZipFile(PATH, 'w', zipfile.ZIP_DEFLATED) as z:
    for n in names:
        z.writestr(n, blobs[n])
print('patched fonts:', patched)
