from flask import Flask, redirect, request, render_template, jsonify
from json2html import json2html
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, jwt, os, uuid
import logging

app = Flask(__name__)

def get_current_email():
    auth_token = request.cookies.get('token')
    if not auth_token:
      raise Exception('Invalid token. Please log in again.')

    try:
        payload = jwt.decode(auth_token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        user_email = payload.get('email')
        if not user_email:
            raise Exception('No email in the token')
        return user_email

    except jwt.ExpiredSignatureError:
        raise Exception('Signature expired. Please log in again.')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token. Please log in again.')

def get_labels():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    labels = graph.run("MATCH (l:Label) RETURN l").data()
    labels = [dict(x['l']) for x in labels]
    return labels

def get_node_by_id(tx, node_id):
    result = tx.run("MATCH (n {id: $id}) RETURN n", id=node_id)
    records = result.data()
    return records[0]['n'] if records else None

def get_or_create_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']
    else:
      return Node('User', id=str(uuid4()), email=email)

def get_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']

@app.route('/submit_review', methods=['POST'])
def review_post():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    doc_id = request.form['doc-id']

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    labels = get_labels()

    tx = graph.begin()
    for label in labels:
        # Decide answer type
        v = request.form.get('label-' + label['id'])
        answer = True if v == 'yes' else False if 'boolean' == label['type'] else v

        node = Node('Answer', id=str(uuid4()), answer=json.dumps(answer))
        tx.create(node)

        # Create relationships
        doc_node = get_node_by_id(tx, doc_id)
        label_node = get_node_by_id(tx, label['id'])
        rel = Relationship(node, "HAS_DOCUMENT", doc_node)
        tx.create(rel)
        rel = Relationship(node, "HAS_LABEL", label_node)
        tx.create(rel)
        user_node = get_or_create_user(tx, email)
        tx.create(Relationship(node, "HAS_USER", user_node))

    graph.commit(tx)

    return jsonify({'status': 'success', 'message': 'Document reviewed successfully'})

def get_unreviewed_document():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document) WHERE NOT EXISTS ((o)<-[:HAS_DOCUMENT]-(:Answer)) RETURN o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    for document in documents:
        document['html'] = json2html.convert(document['content'])
        document['content'] = json.loads(document['content'])
    return documents[0] if documents else None

@app.route('/')
def review_form():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    return render_template('review.html', document=get_unreviewed_document(), labels=get_labels(), review_path=os.getenv('REVIEW_PATH'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
