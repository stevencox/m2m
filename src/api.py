import json
from io import StringIO
import os
import sys
from collections import defaultdict
from pymantic import sparql
from gensim.models import word2vec

class TripleStore(object):
    def __init__(self, hostname):
        self.server = sparql.SPARQLServer (hostname)
    def execute_query (self, query_file):
        result = None
        with open (query_file, "r") as stream:
            query = stream.read ()
            result = self.server.query (query)
        return result

def test ():
    query_file = os.path.join (root, "sparql", "drug-gene.sparql")
    result = triplestore.execute_query (query_file)    
    for binding in result['results']['bindings']:
        for var in result['head']['vars']:
            print ("{0} -> {1}".format (var, binding[var]['value'].encode('utf-8')))

def annotate_gene (gene, drug, gene_drug):
    if gene in gene_drug:
        drugs = gene_drug[gene]
        drugs.append (drug)
    else:
        gene_drug[gene] = [ drug ]

def repurpose (root, triplestore, word_embedding_path, threshold=0.8):
    query_file = os.path.join (root, "src", "query", "drug-gene.sparql")
    result = triplestore.execute_query (query_file)    
    gene_drug = {}
    visits = {}
    for binding in result['results']['bindings']:
        gene = binding['gene']['value'].rsplit('/', 1)[-1]
        drug = binding['drug']['value'].rsplit('/', 1)[-1]
        annotate_gene (gene, drug, gene_drug) 

    print ("loading word embedding model: {0}".format (word_embedding_path))
    model = word2vec.Word2Vec.load (word_embedding_path)
    for g_a in gene_drug:
        gene_a = g_a.lower ()
        for g_b in gene_drug:
            gene_b = g_b.lower ()
            if gene_a == gene_b:
                continue
            if not gene_a in model.vocab or not gene_b in model.vocab:
                continue
            key_1 = "{0}.{1}".format (gene_a, gene_b)
            key_2 = "{0}.{1}".format (gene_b, gene_a)
            if key_1 in visits or key_2 in visits:
                continue
            similarity = model.similarity (gene_a, gene_b)
            if similarity > threshold:
                a_b_applicability, a_b_similarity = calculate_applicability (gene_drug [g_a], gene_drug [g_b], model)
                b_a_applicability, b_a_similarity = calculate_applicability (gene_drug [g_b], gene_drug [g_a], model)
                print ("    genes: {0} {1} sim: {2} ab_app: {3}, ab_sim: {4} ba_app: {5}, ba_sim: {6} )".format 
                       (gene_a, gene_b, similarity, a_b_applicability, a_b_similarity, b_a_applicability, b_a_similarity ))
                print ("       {0} drugs: {1} ".format (gene_a, gene_drug[g_a]))
                print ("       {0} drugs: {1} ".format (gene_b, gene_drug[g_b]))
            visits[key_1] = 1
            visits[key_2] = 1

def calculate_applicability (drugs_a, drugs_b, model):
    result = 0
    similarity = 0
    similarity_map = {}
    for d_a in drugs_a:
        if d_a in drugs_b:
            result = result + 1
        else:
            drug_a = d_a.lower ()
            for d_b in drugs_b:
                drug_b = d_b.lower ()
                if drug_a not in model.vocab or drug_b not in model.vocab:
                    continue
                similarity = similarity + model.similarity (drug_a, drug_b)
            total = len (drugs_b)
            if total > 0:
                similarity = similarity / len(drugs_b)
            similarity_map [drug_a] = similarity
    return result, similarity

class GeneDrug(object):
    def __init__(self, threshold=0.4):
        self.gene_drug = defaultdict(list)
        self.drug_gene = defaultdict(list)
        self.threshold = threshold
    def add (self, gene, drug):
        self.gene_drug[gene].append (drug)
        self.drug_gene[drug].append (gene)
    def get_target_similarity (self, L_drug, R_drug, model):
        similarity = 0
        if L_drug in self.drug_gene and R_drug in self.drug_gene:
            visits = {}
            hits = 0
            for L in self.drug_gene[L_drug]:
                for R in self.drug_gene[R_drug]:
                    if L in model.vocab and R in model.vocab:
                        key_1 = "{0}.{1}".format (L, R)
                        key_2 = "{0}.{1}".format (R, L)
                        if key_1 not in visits and key_2 not in visits:
                            gene_similarity = model.similarity (L, R)
                            if gene_similarity > self.threshold:
                                similarity = similarity + gene_similarity
                                hits = hits + 1
                                print ("    Lg: {0} Rg: {1} sim: {2}".format (L, R, gene_similarity))
                            visits[key_1] = 1
                            visits[key_2] = 1
            similarity = similarity / hits if hits > 0 else similarity
        return similarity

class RepurposeV2(object):
    def __init__(self, triplestore_uri, root, word_embedding_path, threshold=0.4):
        self.triplestore = TripleStore (triplestore_uri)
        self.root = root
        self.word_embedding_path = word_embedding_path
        self.threshold = threshold
    def run (self):
        query_file = os.path.join (self.root, "src", "query", "drug-indication.sparql")
        result = triplestore.execute_query (query_file)
        indications = defaultdict(list)
        gene_drug = GeneDrug ()
        for binding in result['results']['bindings']:
            drug = binding['name']['value'].rsplit('/', 1)[-1].lower ()
            indication = binding['indication']['value'].rsplit('/', 1)[-1].lower ()
            gene = binding['gene']['value'].rsplit('/', 1)[-1].lower ()
            indications[drug].append(indication)
            gene_drug.add (gene, drug)
        print ("loading word embedding model: {0}".format (word_embedding_path))
        model = word2vec.Word2Vec.load (word_embedding_path)
        novel_indications = defaultdict(list)

        '''
        Given di and cj (assuming di does not treat cj)
           - find all drugs dk that treat cj
              - ni=(number of dk such that semantic similarity of di-dk > 0.4)
              - Sij = ni/(number of dk)
        ref_drug=dk, other_drug=di
        '''
        
        ''' all dk treating some set of cj '''
        for ref_drug in indications: 
            for other_drug in indications:
                if ref_drug != other_drug and ref_drug in model.vocab and other_drug in model.vocab:
                    ''' determine whether two drugs are semantically similar. '''
                    similarity = model.similarity (ref_drug, other_drug)
                    if similarity > self.threshold:
                        ref_indications = indications[ref_drug]
                        other_indications = indications[other_drug]
                        for indication in other_indications:
                            if indication not in ref_indications:
                                ''' di is not known to treat this cj, which dk is known to treat. di!->cj && dk->cj '''
                                ''' now test the semantic similarity of their gene targets. '''
                                gene_profile_similarity = gene_drug.get_target_similarity (ref_drug, other_drug, model)
                                if gene_profile_similarity > 0:
                                    novel_indications[indication].append ( ( other_drug, ref_drug, gene_profile_similarity ) )
        for indication in novel_indications:
            ni = len (novel_indications[indication])
            num_dk = 0
            for drug in indications:
                if indication in indications[drug]:
                    num_dk = num_dk + 1
            Sij = ni / num_dk
            novel = novel_indications[indication]
            print ("ind={0}, ni={1}, num_dk={2}, Sij={3}, alt:{4}".format (indication, ni, num_dk, Sij, len(novel)))
            candidates = sorted(novel, key=lambda candidate: -candidate[2])
            for n in candidates:
                print ("   cand={0}, ref={1}, genesim={2}".format (n[0], n[1], n[2]))

word_embedding_path = "/projects/stars/var/chemotext/w2v/gensim/cumulative/pmc-2016.w2v"
root = "/projects/stars/m2m/dev/m2m"
triplestore_uri = "http://stars-blazegraph.renci.org/bigdata/sparql"
triplestore = TripleStore (triplestore_uri)
#repurpose (root, triplestore, word_embedding_path)

repurpose = RepurposeV2 (triplestore_uri, root, word_embedding_path)
repurpose.run ()


