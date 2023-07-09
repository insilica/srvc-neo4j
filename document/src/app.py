from flask import Flask, request, render_template
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid

app = Flask(__name__)

@app.route('/')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document)"
    q = f"{q} OPTIONAL MATCH (d)<-[:HAS_DOCUMENT]-(a:Answer)-[:HAS_LABEL]->(l:Label)"
    q = f"{q} RETURN d.uri AS uri, d.json_data AS json_data,"
    q = f"{q} collect({{label: l, answer: a}}) AS label_answers"
    documents = graph.run(q).data()

    for document in documents:
        document['json_data'] = json.loads(document['json_data'])
        document['label_answers'] = [(x['label'], x['answer']) for x in document['label_answers'] if x['label'] and x['answer']]

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
