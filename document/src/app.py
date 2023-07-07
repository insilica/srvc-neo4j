from flask import Flask, request, render_template
from SPARQLWrapper import SPARQLWrapper, JSON
from uuid import uuid4
import json, os

app = Flask(__name__)

sparql_endpoint = 'http://jena:3030/srvc/query'  # Update the SPARQL endpoint URL to match your Jena Fuseki configuration
username = 'admin'
password = 'test1234'

@app.route('/document')
def list_documents():
    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setCredentials(username, password)  # Set the credentials for authentication
    sparql.setQuery('''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX neo: <http://neo4j.org#>
        SELECT ?uri ?json_data ?label ?answer WHERE {
            ?d rdf:type neo:Object ;
               neo:type "document" ;
               neo:uri ?uri ;
               neo:json_data ?json_data .
            OPTIONAL {
                ?d neo:HAS_EVENT ?a .
                ?a rdf:type neo:Object ;
                   neo:type "label-answer" ;
                   neo:answer ?answer .
                ?a neo:HAS_LABEL ?l .
                ?l neo:question ?label .
            }
        }
    ''')
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    documents = []
    for result in results["results"]["bindings"]:
        document = {
            "uri": result["uri"]["value"],
            "json_data": json.loads(result["json_data"]["value"]),
            "label_answers": []
        }
        if "label" in result and "answer" in result:
            label = result["label"]["value"]
            answer = result["answer"]["value"]
            document["label_answers"].append((label, answer))
        documents.append(document)

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
