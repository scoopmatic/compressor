#!/usr/bin/python

import os, subprocess, re

PARSER_DIR = "/home/samuel/code/stt/lib/Finnish-dep-parser/"

def parse(text):
    #Introduce space after end-of-sentence punctuation, if missing
    text=re.sub("(\.|!|\?)[A-Z]\w+",(lambda x: x.group(0)[0]+' '+x.group(0)[1:]),text,flags=re.U)

    dir = os.getcwd()
    os.chdir(PARSER_DIR)
    proc = subprocess.Popen(["./parser_wrapper.sh"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    text = text.replace('\n', ' ')
    output = proc.communicate(input=text)[0]
    os.chdir(dir)
    return output

def read_conll(conll):
    #print("Converting format...")
    indata = conll.split('\n')
    indata.append("")

    sents = []
    words = {'0': 'ROOT'}
    sent = []

    for line in indata:
        if line == '':
            if len(sent) > 0:
                sents.append(sent)
            # reset
            words = {'0': 'ROOT'}
            sent = []
            continue

        #w_id, wrd, _, w_lemma, w_pos, _, w_feat, _, w_head, _, w_rel, _, _, _ = line.split('\t')
        w_id, wrd, w_lemma, w_pos, _, w_feat, w_head, w_rel, _, _ = line.split('\t')
        sent.append({'idx': int(w_id), 'token': wrd, 'lemma': w_lemma, 'pos': w_pos, 'feat': w_feat, 'head': int(w_head), 'rel': w_rel})

    return sents


def process(text):
    return read_conll(parse(text))
