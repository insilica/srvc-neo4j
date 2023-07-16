from flask import Flask, request, render_template, redirect, url_for, jsonify
from py2neo import Graph, Node
from uuid import uuid4

app = Flask(__name__)

@app.route('/create', methods=['POST'])
def create_label():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    id = str(uuid4())
    name = request.form.get('name')
    description = request.form.get('description')
    label_type = request.form.get('type')

    if name and description and label_type:  # Ensure no empty fields
        tx = graph.begin()
        tx.run("""
            MERGE (label:Label {id: $id, name: $name, description: $description, type: $type})
            """, id=id, name=name, description=description, type=label_type)
        tx.commit()

    return jsonify({'status': 'success', 'message': 'Label created successfully'})

@app.route('/edit/<id>', methods=['POST'])
def edit_label(id):
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    name = request.form.get('name')
    description = request.form.get('description')
    label_type = request.form.get('type')

    if name and description and label_type:  # Ensure no empty fields
        tx = graph.begin()
        tx.run("""
            MATCH (label:Label {id: $id}) 
            SET label.name = $name, label.description = $description, label.type = $type
            """, id=id, name=name, description=description, type=label_type)
        tx.commit()

    return jsonify({'status': 'success', 'message': 'Label edited successfully'})

@app.route('/delete/<id>', methods=['POST'])
def delete_label(id):
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    # TODO also delete any answers that have this label
    tx = graph.begin()
    tx.run("""
        MATCH (label:Label {id: $id}) DETACH DELETE label
        """, id=id)
    tx.commit()

    return jsonify({'status': 'success', 'message': 'Label deleted successfully'})

@app.route('/', methods=['GET'])
def label_editor():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    q = "MATCH (l:Label) RETURN l.id AS id, l.name AS name,"
    q = f"{q} l.description AS description, l.type AS type"
    labels = graph.run(q).data()
    labels = list(enumerate(labels, start=1))  # Add index for each label
    return render_template('labels.html', labels=labels)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
