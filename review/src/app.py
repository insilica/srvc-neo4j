from flask import Flask, redirect, request, render_template, jsonify
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid
import logging

app = Flask(__name__)

def get_labels():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    labels = graph.run("MATCH (l:Label) RETURN l").data()
    labels = [dict(x['l']) for x in labels]
    return labels

def get_node_by_id(tx, node_id):
    result = tx.run("MATCH (n {id: $id}) RETURN n", id=node_id)
    records = result.data()
    return records[0]['n'] if records else None
    
@app.route('/submit_review', methods=['POST'])
def review_post():
    print("HOLLA AT YA BOI")
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    doc_id = request.form['doc-id']
    tx = graph.begin()

    labels = get_labels()

    for label in labels:
        # Decide answer type
        v = request.form.get('label-' + label['id'])
        answer = True if v == 'on' else False if 'boolean' == label['type'] else v

        node = Node('Answer', id=str(uuid4()), answer=json.dumps(answer))
        tx.create(node)

        # Create relationships
        doc_node = get_node_by_id(tx, doc_id)
        label_node = get_node_by_id(tx, label['id'])
        rel = Relationship(node, "HAS_DOCUMENT", doc_node)
        tx.create(rel)
        rel = Relationship(node, "HAS_LABEL", label_node)
        tx.create(rel)

    graph.commit(tx)

    return jsonify({'status': 'success', 'message': 'Document reviewed successfully'})

def get_unreviewed_document():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document) WHERE NOT EXISTS ((o)<-[:HAS_DOCUMENT]-(:Answer)) RETURN o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    for document in documents:
        document['content'] = json.loads(document['content'])
    return documents[0] if documents else None

@app.route('/')
def review_form():
    return render_template('review.html', document=get_unreviewed_document(), labels=get_labels())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
