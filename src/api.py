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


from collections import defaultdict

class GeneDrug(object):

    def __init__(self, threshold=0.4):
        self.gene_drug = defaultdict(list)
        self.drug_gene = defaultdict(list)
        self.threshold = threshold

    def add (gene, drug):
        self.gene_drug[gene].append (drug)
        self.drug_gene[drug].append (gene)
        '''
        if gene in self.gene_drug:
            drugs = self.gene_drug[gene]
            drugs.append (drug)
        else:
            self.gene_drug[gene] = [ drug ]
        '''
    def get_target_similarity (self, L_drug, R_drug, model):
        similarity = 0
        if L_drug in self.drug_gene and R_drug in self.drug_gene:
            L_genes = self.drug_gene[L_drug]
            R_genes = self.drug_gene[R_drug]
            visits = {}
            for L in L_genes:
                for R in R_genes:
                    if L in model.vocab and R in model.vocab:
                        key_1 = "{0}.{1}".format (L, R)
                        key_2 = "{0}.{1}".format (R, L)
                        if key_1 not in visits and key_2 not in visits:
                            similarity = similarity + model.similarity (L, R)
                            visits[key_1] = 1
                            visits[key_2] = 1
            similarity = similarity / len(visits) if len(visits) > 0 else similarity
        return similarity

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

class RepurposeV2(object):

    def __init__(self, triplestore_uri, root, word_embedding_path, threshold=0.4):
        self.triplestore = TripleStore (triplestore_uri)
        self.root = root
        self.word_embedding_path = word_embedding_path
        self.threshold = threshold

    def run (self):
        query_file = os.path.join (self.root, "src", "query", "drug-indication.sparql")
        result = triplestore.execute_query (query_file)
        indications = {}
        gene_drug = GeneDrug ()
        for binding in result['results']['bindings']:
            drug = binding['name']['value'].rsplit('/', 1)[-1].lower ()
            indication = binding['indication']['value'].rsplit('/', 1)[-1].lower ()
            gene = binding['gene']['value'].rsplit('/', 1)[-1].lower ()
            if not drug in indications:
                indications[drug] = [ indication ] 
            else:
                if not indication in indications[drug]:
                    indications[drug].append(indication)
            gene_drug.add (gene, drug)

        print ("loading word embedding model: {0}".format (word_embedding_path))
        model = word2vec.Word2Vec.load (word_embedding_path)
        novel_indications = {}
        for ref_drug in indications:
            for other_drug in indications:
                if ref_drug not in model.vocab or other_drug not in model.vocab:
                    continue
                similarity = model.similarity (ref_drug, other_drug)
                if similarity > self.threshold:
                    ref_indications = indications[ref_drug]
                    other_indications = indications[other_drug]
                    for indication in other_indications:
                        if indication not in ref_indications:
                            if indication in novel_indications:
                                if not other_drug in novel_indications[indication]:
                                    novel_indications[indication].append (other_drug)
                            else:
                                novel_indications[indication] = [ other_drug ]

        for indication in novel_indications:
            ni = len (novel_indications[indication])
            num_dk = 0
            for drug in indications:
                if indication in indications[drug]:
                    num_dk = num_dk + 1
            Sij = ni / num_dk
            print ("indication => {0}: ni={1} num_dk={2} Sij={3} alt:{4}".format (indication, ni, num_dk, Sij, novel_indications[indication]))




word_embedding_path = "/projects/stars/var/chemotext/w2v/gensim/cumulative/pmc-2016.w2v"
root = "/projects/stars/m2m/dev/m2m"
triplestore_uri = "http://stars-blazegraph.renci.org/bigdata/sparql"
triplestore = TripleStore (triplestore_uri)
#repurpose (root, triplestore, word_embedding_path)

repurpose = RepurposeV2 (triplestore_uri, root, word_embedding_path)
repurpose.run ()


