from flask import Flask, request, render_template, redirect, url_for, jsonify
from py2neo import Graph, Node
from uuid import uuid4
import jwt, os

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

def get_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']

@app.route('/create', methods=['POST'])
def create_label():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    id = str(uuid4())
    name = request.form.get('name')
    categories = request.form.get('categories')
    description = request.form.get('description')
    label_type = request.form.get('type')

    if name and description and label_type:  # Ensure no empty fields
        tx = graph.begin()
        tx.run("""
            MERGE (label:Label {id: $id, name: $name, categories: $categories, description: $description, type: $type})
            """, id=id, name=name, categories=categories, description=description, type=label_type)
        tx.commit()

    return jsonify({'status': 'success', 'message': 'Label created successfully'})

@app.route('/edit/<id>', methods=['POST'])
def edit_label(id):
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    name = request.form.get('name')
    categories = request.form.get('categories')
    description = request.form.get('description')
    label_type = request.form.get('type')

    if name and description and label_type:  # Ensure no empty fields
        tx = graph.begin()
        tx.run("""
            MATCH (label:Label {id: $id})
            SET label.name = $name, label.categories = $categories, label.description = $description, label.type = $type
            """, id=id, name=name, categories=categories, description=description, type=label_type)
        tx.commit()

    return jsonify({'status': 'success', 'message': 'Label edited successfully'})

@app.route('/delete/<id>', methods=['POST'])
def delete_label(id):
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    # TODO also delete any answers that have this label
    tx = graph.begin()
    tx.run("""
        MATCH (label:Label {id: $id}) DETACH DELETE label
        """, id=id)
    tx.commit()

    return jsonify({'status': 'success', 'message': 'Label deleted successfully'})

@app.route('/', methods=['GET'])
def label_editor():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    q = "MATCH (l:Label) RETURN l.id AS id, l.name AS name,"
    q = f"{q} l.description AS description, l.type AS type, l.categories AS categories"
    labels = graph.run(q).data()
    labels = list(enumerate(labels, start=1))  # Add index for each label
    return render_template('labels.html', labels=labels, labels_path=os.getenv('LABELS_PATH'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
