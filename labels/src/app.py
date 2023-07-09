from flask import Flask, request, render_template, redirect, url_for
from py2neo import Graph, Node
from uuid import uuid4

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def label_editor():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    
    if request.method == 'POST':
        id = str(uuid4())
        name = request.form.get('name')
        description = request.form.get('description')
        label_type = request.form.get('type')
        tx = graph.begin()
        tx.run("""
            MERGE (label:Label {id: $id, name: $name, description: $description, type: $type})
            """, id=id, name=name, description=description, type=label_type)
        tx.commit()
        return redirect(url_for('label_editor'))

    labels = graph.run("MATCH (label:Label) RETURN label.id AS id, label.name AS name, label.description AS description, label.type AS type").data()
    return render_template('labels.html', labels=labels)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')