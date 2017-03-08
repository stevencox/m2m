import pronto
from collections import defaultdict
from triplestore import TripleStore

class Disease(object):
    def __init__ (self, xref, lineage):
        self.xref = xref
        self.lineage = lineage

def parse_ontology ():
    ont = pronto.Ontology ('/projects/stars/m2m/var/diseaseontology/dis.obo')
    #print (ont.json)
    hierarchy_map = {}
    for term in ont:
        xref = None
        if 'xref' in term.other:
            for x in term.other['xref']:
                if x.startswith ("MESH:"):
                    xref = x
                    break
        disease = Disease (xref=xref, lineage=map ( lambda t : t.id, term.rparents ()))
        hierarchy_map[term.id.upper ()] = disease

    for k in hierarchy_map:
        print ("{0} {1} {2}".format (k, hierarchy_map[k].xref, hierarchy_map[k].lineage))

    return hierarchy_map

query = """
PREFIX db_resource:      <http://chem2bio2rdf.org/drugbank/resource/>
PREFIX ctd_chem_disease: <http://chem2bio2rdf.org/ctd/resource/ctd_chem_disease/>
PREFIX biordf:           <http://bio2rdf.org/>
PREFIX ctd:              <http://chem2bio2rdf.org/ctd/resource/>
PREFIX pubchem:          <http://chem2bio2rdf.org/ctd/resource/>

SELECT DISTINCT ?chem_disease ?meshid ?compound 
WHERE {
  ?chem_disease ctd:diseaseid ?meshid .
  ?chem_disease ctd:cid       ?compound .
}
"""

def get_disease_drug_associations (triplestore):
    disease_compound = {}
    result = triplestore.execute_query (query)    
    for bind in result.bindings:
        chem_disease = bind['chem_disease'].value.rsplit('/', 1)[-1]
        mesh_id = bind['meshid'].value.rsplit('/', 1)[-1].upper ()
        compound = bind['compound'].value.rsplit('/', 1)[-1]
        disease_compound [mesh_id] = compound
    return disease_compound

triplestore_uri = "http://stars-blazegraph.renci.org/bigdata/sparql"
triplestore = TripleStore (triplestore_uri)

disease_compound = get_disease_drug_associations (triplestore)
hierarchy_map = parse_ontology ()

for term_id in hierarchy_map:
    disease = hierarchy_map [term_id]
    if disease.xref in disease_compound:
        compound = disease_compound [disease.xref]
        print ("disease item: {0} is treated by: {1}".format (term_id, compound))
