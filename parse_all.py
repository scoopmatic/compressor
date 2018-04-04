#!/usr/bin/python

import os, sys
import subprocess

try:
    src_path = sys.argv[1]
    trg_path = sys.argv[2]
    assert src_path != trg_path
except:
    print("Usage: %s <input directory> <output directory>" % sys.argv[0])
    sys.exit()

print("Reading text from:",src_path)
print("Saving parses to:",trg_path)
files = [f for f in sorted(os.listdir(src_path)) if '.txt' in f]
batch_size = 5000
for beg in range(0, len(files), batch_size):
    buffer = ""
    print("Batch", int(beg/batch_size))
    print("\tLoading")
    for filename in files[beg:beg+batch_size]:
        buffer += '###C:NEW DOCUMENT:%s\n'%filename + open(src_path+filename).read()+'\n'

    print("\tParsing", round(len(buffer)/1000), "kB")
    docs = []
    doc = ""
    doc_paths = []
    proc = subprocess.Popen(["./call_parser.sh"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = proc.communicate(input=buffer.encode('utf-8'))[0]
    for row in output.decode('utf-8').split('\n'):
        if '###C:NEW DOCUMENT:' in row:
            if doc_paths:
                docs.append(doc)
                doc = ""
            doc_paths.append(row.split(':')[2])
        else:
            doc += row+'\n'

    docs.append(doc)
    assert len(docs) == len(doc_paths)

    print("\tSaving",len(docs),"files")
    for path, content in zip(doc_paths, docs):
        open(trg_path+path.replace('.txt','.conll'), 'w').write(content)
