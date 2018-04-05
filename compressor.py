import parser
import os
import collections
import math
import functools


class Compressor:
    """ Heuristic text compressor """
    def __init__(self, path, parsed_input=True):
        if parsed_input:
            self.read_parses(path)
        else:
            self.parse_data(path)
        self.init_tfidf()

    def read_parses(self, path):
        """ Read parses from file """
        files = [f for f in os.listdir(path) if '.conll' in f]
        self.docs = []
        for i, filename in enumerate(files):
            if i % 1000 == 0:
                print("Reading... %d/%d" % (i,len(files)))
            parse = open(path+filename).read()
            self.docs.append(parser.read_conll(parse))

    def parse_data(self, path):
        """ Read text from file and parse """
        buffer = ""
        for i, filename in enumerate(os.listdir(path)):
            if i % 1000 == 0:
                print("Reading... %d" % i)
            if '.txt' not in filename:
                continue
            buffer += open(path+filename).read()+'\nDOCUMENT-SEPARATOR.\n'

        print("Parsing", len(buffer)/1000, "kB...")
        self.docs = []
        doc = []
        for sent in parser.parse(buffer):
            if sent[0]['token'] == 'DOCUMENT-SEPARATOR':
                self.docs.append(doc)
                doc = []
            else:
                doc.append(sent)

    def init_tfidf(self):
        """ Count word occurrences in data """
        self.df = collections.defaultdict(lambda: 0)
        self.tf = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
        self.idf = (lambda term: math.log(float(len(self.docs))/self.df[term]))
        self.tfidf = (lambda term, doc_i: (1+math.log(self.tf[doc_i][term]))*self.idf(term))

        print("Computing TF-IDF...")
        for i, doc in enumerate(self.docs):
            seen = set()
            for sent in doc:
                for term in [x['lemma'] for x in sent]:
                    self.tf[i][term] += 1
                    if term not in seen:
                        self.df[term] += 1
                    seen.add(term)


    def compute_tfidf(self, tokens, doc_i):
        return [dict(token.items() + [('tfidf', self.tfidf(token['lemma'], doc_i))]) for token in tokens]


    def traverse(self, tree, node=0, chain=[0]):
        """ Produce paths from root to each token """
        chains = []
        for child in tree[node]:
            chains.append(self.traverse(tree, node=child['idx'], chain=chain+[child['idx']]))
        if not tree[node]:
            return [tuple(chain)]
        else:
            return functools.reduce(lambda a,b: a+b, chains)


    def compress(self, tokens, rate=0.5):
        """ Compress sentence by specified rate """
        tree = collections.defaultdict(lambda: [])
        token_dict = {}
        CCs = []
        conjs = []
        for token in tokens:
            if token['rel'] == 'punct': # Remove punctuation
                continue
            if token['rel'] == 'cc': # Remember CCs
                CCs.append(token)
            if token['rel'] == 'conj': # Remember conjunctions
                conjs.append(token)
            tree[token['head']].append(token)
            token_dict[token['idx']] = token
        #
        for token in conjs:
            for sibling in tree[token['head']]:
                if sibling['rel'] == 'cc':
                    # Add link from cc to conj
                    tree[sibling['idx']].append(token)
        #
        paths = self.traverse(tree)
        #dict([(x['idx'], x) for x in functools.reduce(lambda a,b: a+b, tree.values())])
        """ranking = sorted([
            ([node for node in tree[path[-2]]
                if node['idx'] == path[-1]
             ][0]['tfidf'],
              path)
            for path in paths
        ], reverse=True)"""
        try:
            ranking = sorted([(token_dict[path[-1]]['tfidf'], path) for path in paths], reverse=True)
        except KeyError:
            return "" # Return empty line for empty path set (failed compression)
        output = set()
        assert rate > 0 and rate < 1
        last_token = None
        for _, path in ranking:
            if len(output) > len(token_dict)*rate and last_idx != path[-1]:
                break
            last_idx = path[-1]
            for idx in path:
                if idx != 0:
                    output.add(idx)
        #
        """for cc in CCs:
            siblings = tree[cc['head']]
            i = [node['idx'] for node in siblings].index(cc['idx'])
            left, right = siblings[i-1], siblings[i+1]
            if left['idx'] in output and right['idx'] in output:
                output.add(cc['idx'])"""
        #
        #return str(round(float(len(output))/len(token_dict)*100))+'%: '+' '.join([token_dict[idx]['token'] for idx in sorted(output)])
        return ' '.join([token_dict[idx]['token'] for idx in sorted(output)])


    def compress_doc(self, doc_tokens, rate=0.5):
        """ Compress document by specified rate """
        ranking = []
        token_dict = collections.defaultdict(lambda: {})
        for sent_i, tokens in enumerate(doc_tokens):
            tree = collections.defaultdict(lambda: [])
            for token in tokens:
                tree[token['head']].append(token)
                token_dict[sent_i][token['idx']] = token
            paths = self.traverse(tree)
            #
            #dict([(x['idx'], x) for x in functools.reduce(lambda a,b: a+b, tree.values())])
            """ranking = sorted([
                ([node for node in tree[path[-2]]
                    if node['idx'] == path[-1]
                 ][0]['tfidf'],
                  path)
                for path in paths
            ], reverse=True)"""
            ranking += [(token_dict[sent_i][path[-1]]['tfidf'], sent_i, path) for path in paths]
        #
        output = [set() for _ in range(len(doc_tokens))]
        assert rate > 0 and rate < 1
        for _, sent_i, path in sorted(ranking, reverse=True):
            if sum(map(len, output)) > sum(map(len,token_dict.values()))*rate:
                break
            for idx in path:
                if idx != 0:
                    output[sent_i].add(idx)
        #
        outstr = '\n'.join([' '.join([token_dict[sent_i][idx]['token'] for idx in sorted(sent)]) for sent_i, sent in enumerate(output) if sent])
        return str(round(float(sum(map(len, output)))/sum(map(len,token_dict.values()))*100))+'%:\n '+outstr


    def compress_all_sents(self, rate=0.5, output=None):
        print("Compressing sentences...")
        if output:
            outf = open(output, "w")
            outf2 = open(output+'.orig', "w")
        for doc_i, doc in enumerate(self.docs):
            for sent_i, sent in enumerate(doc):
                tokens = self.compute_tfidf(sent, doc_i)
                self.docs[doc_i][sent_i] = tokens
                result = self.compress(tokens, rate)
                if output:
                    outf.write(result+'\n')
                    outf2.write(' '.join([t['token'] for t in tokens])+'\n')
                else:
                    print(result)
            if not output:
                print
        if output:
            outf.close()
            outf2.close()

"""
for doc_i, doc in enumerate(docs[:10]):
    tokens = [[dict(token.items() + [('tfidf', tfidf(token['lemma'], doc_i))]) for token in sent] for sent in doc]
    rate = 0.5
    print compress_doc(tokens, rate)
    print
"""
