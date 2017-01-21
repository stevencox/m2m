from io import StringIO
import os
import sys
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



word_embedding_path = "/projects/stars/var/chemotext/w2v/gensim/cumulative/pmc-2016.w2v"
root = "/projects/stars/m2m/dev/m2m"
hostname = "http://stars-blazegraph.renci.org/bigdata/sparql"
triplestore = TripleStore (hostname)
repurpose (root, triplestore, word_embedding_path)


