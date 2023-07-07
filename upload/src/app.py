from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask import send_from_directory
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from SPARQLWrapper import SPARQLWrapper, SPARQLWrapper2, DIGEST, JSON
from uuid import uuid4
from werkzeug.utils import secure_filename
import json, os, requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/srvc-upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

sparql_endpoint = 'http://jena:3030/srvc/'
username = 'admin'
password = 'test1234'

@app.route('/upload')
def upload():
    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setCredentials(username, password)  # Set the credentials for authentication
    sparql.setQuery('''
        PREFIX neo: <http://neo4j.org#>
        SELECT ?source (COUNT(?d) AS ?documents) WHERE {
            ?s neo:name ?source .
            ?s neo:SOURCE_OF ?d .
        }
        GROUP BY ?source
    ''')
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    sources = []
    for result in results["results"]["bindings"]:
        source = result["source"]["value"]
        documents = int(result["documents"]["value"])
        sources.append({"source": source, "documents": documents})

    return render_template('upload.html', sources=sources)

@app.route('/upload/source', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        filename = secure_filename(f.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(file_path)

        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        triples = create_triples(data, filename)

                        if not triples:  # Skip graph update if no triples are generated
                            continue

                        for triple in triples:
                            subject, predicate, obj = triple

                            # SPARQL query to insert the triple into the graph
                            insert_query = '''
                            PREFIX neo: <http://neo4j.org#>
                            INSERT DATA {{
                                GRAPH <http://example.com/data> {{
                                    {} {} {} .
                                }}
                            }}
                            '''.format(subject.n3(), predicate.n3(), obj.n3())

                            # Send the SPARQL query to the Fuseki endpoint
                            response = requests.post('http://jena:3030/srvc/update', data=insert_query, auth=(username, password))
                            if response.status_code != 204:
                                print(f"Failed to insert triple: {insert_query}")

                    except json.JSONDecodeError:
                        print(f"Skipped invalid JSON line: {line}")
                        continue

        return redirect(url_for('upload'))

@app.route('/upload/delete/<source_name>', methods=['POST'])
def delete_source(source_name):
    if request.method == 'POST':
        sparql = SPARQLWrapper(sparql_endpoint)
        sparql.setCredentials(username, password)  # Set the credentials for authentication
        delete_from_jena(source_name, sparql)

        return redirect(url_for('upload'))

def create_triples(data, filename):
    triples = [
        (URIRef('http://neo4j.org#document'), URIRef('http://neo4j.org#id'), Literal(str(uuid4()))),
        (URIRef('http://neo4j.org#document'), URIRef('http://neo4j.org#json_data'), Literal(json.dumps(data))),
        (URIRef('http://neo4j.org#document'), URIRef('http://neo4j.org#type'), Literal(data.get('type'))),
        (URIRef('http://neo4j.org#document'), URIRef('http://neo4j.org#uri'), Literal(data.get('uri'))),
        (URIRef('http://neo4j.org#document_source'), URIRef('http://neo4j.org#name'), Literal(filename)),
        (URIRef('http://neo4j.org#document_source'), URIRef('http://neo4j.org#SOURCE_OF'), URIRef('http://neo4j.org#document')),
    ]
    return triples

def delete_from_jena(source_name, sparql):
    delete_query = '''
    PREFIX neo: <http://neo4j.org#>
    DELETE WHERE {
        GRAPH <http://example.com/data> {
            ?s neo:name "%s" ;
               neo:SOURCE_OF ?d .
        }
    }
    ''' % source_name

    sparql.setQuery(delete_query)
    sparql.setMethod('POST')
    sparql.query()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
