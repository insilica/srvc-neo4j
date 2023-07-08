from flask import Flask, request, render_template, redirect, url_for
from py2neo import Graph, Node

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def label_editor():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    
    if request.method == 'POST':
        label_id = request.form.get('id')
        question = request.form.get('question')
        label_type = request.form.get('type')
        tx = graph.begin()
        tx.run("""
            MERGE (label:Label {id: $id, question: $question, type: $type})
            """, id=label_id, question=question, type=label_type)
        graph.commit(tx)
        return redirect(url_for('label_editor'))

    labels = graph.run("MATCH (label:Label) RETURN label.id AS id, label.question AS question, label.type AS type").data()
    return render_template('label_editor.html', labels=labels)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
