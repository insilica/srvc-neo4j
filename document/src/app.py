from flask import Flask, request, render_template, render_template_string
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid

app = Flask(__name__)

template = "{{doc.content.content}}"

def parse_content(d):
    if d['content_type'] == 'json':
            d['content'] = json.loads(d['content'])
    return d

@app.route('/')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document) return o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    documents = [parse_content(d) for d in documents]

    for d in documents:
        d['rendered_content'] = render_template_string(template, doc=d)

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
