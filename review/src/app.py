from flask import Flask, redirect, request, render_template
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid

app = Flask(__name__)

labels = [
  {'id': 'include', 'question': 'Include?', 'type': 'boolean'},
  {'id': 'substance', 'question': 'Substance', 'type': 'text'},
]

def create_label_nodes(tx, labels):
    for label in labels:
        # Use MERGE to ensure a node with the specified properties exists
        tx.run("""
        MERGE (label:Object {id: $id, question: $question, type: $type})
        """, id=label['id'], label_type=label['type'], question=label['question'], type='label')

def get_node_by_id(tx, node_id):
    result = tx.run("MATCH (n:Object {id: $id}) RETURN n", id=node_id)
    records = result.data()
    return records[0]['n'] if records else None

def create_label_answer(tx, doc_id, label, v):
    if 'boolean' == label['type']:
      if v == 'on':
        answer = True
      else:
        answer = False
    elif 'text' == label['type']:
      answer = v

    node = Node(
      'Object',
       id=str(uuid4()),
       answer=json.dumps(answer),
       event_id=doc_id,
       label_id=label['id'],
       type='label-answer',
    )
    tx.create(node)

    doc_node = get_node_by_id(tx, doc_id)
    label_node = get_node_by_id(tx, label['id'])
    rel = Relationship(node, "HAS_EVENT", doc_node)
    tx.create(rel)
    rel = Relationship(node, "HAS_LABEL", label_node)
    tx.create(rel)

@app.route('/review', methods=['POST'])
def review_post():
    if request.method == 'POST':
        graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
        doc_id = request.form['doc-id']
        tx = graph.begin()
        create_label_nodes(tx, labels)
        for label in labels:
          create_label_answer(tx, doc_id, label, request.form.get('label-' + label['id']))
        graph.commit(tx)

        return redirect('/review')

def get_unreviewed_document():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    documents = graph.run("""
    MATCH (o:Object {type: "document"})
    WHERE NOT EXISTS ((o)<-[:HAS_EVENT]-(:Object))
    RETURN o.id AS id, o.uri AS uri, o.json_data AS json_data
    LIMIT 1
    """).data()

    for document in documents:
        document['json_data'] = json.loads(document['json_data'])

    return documents[0] if documents else None

@app.route('/review')
def review_form():
    return render_template('review.html', document=get_unreviewed_document(), labels=labels)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
