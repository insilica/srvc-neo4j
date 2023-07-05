from flask import Flask, request, render_template
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid

app = Flask(__name__)

@app.route('/document')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    documents = graph.run("""
    MATCH (o:Object {type: "document"})
    RETURN o.uri AS uri, o.json_data AS json_data
    """).data()

    for document in documents:
        document['json_data'] = json.loads(document['json_data'])

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
