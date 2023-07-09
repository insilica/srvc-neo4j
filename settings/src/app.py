from flask import Flask, request, render_template, redirect, url_for
from py2neo import Graph, Node
from uuid import uuid4

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def settings():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    
    if request.method == 'POST':
        key = request.form.get('key')
        value = request.form.get('value')
        tx = graph.begin()
        tx.run("MERGE (setting:Setting {key: $key, value: $value})", key=key, value=value)
        tx.commit()
        return redirect(url_for('settings'))

    settings = graph.run("MATCH (setting:Setting) RETURN setting.key AS key, setting.value AS value").data()
    return render_template('settings.html', settings=settings)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
