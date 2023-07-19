from flask import Flask, request, render_template, render_template_string, redirect
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from json2html import json2html
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, jwt, os, uuid

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

def get_project_visibility(tx):
    result = tx.run("MATCH (n:Setting {group: $group, key: $k}) RETURN n", group='Project', k='visibility')
    records = result.data()
    if records:
      return records[0]['n']

app = Flask(__name__)

template = "{{doc.content}}"

def parse_content(d):
    if d['content_type'] == 'json':
            d['content'] = json.loads(d['content'])
    return d

@app.route('/')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    visibility = get_project_visibility(graph)

    if not visibility or visibility['value'] != 'public':
        try:
            email = get_current_email()
        except:
            return redirect('/login'), 303
        user = get_user(graph, email)
        if not (user and user.get('isMember')):
            return 'Forbidden', 403

    q = "MATCH (o:Document) return o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    documents = [parse_content(d) for d in documents]

    for d in documents:
        d['html'] = json2html.convert(d['content'])
        d['rendered_content'] = render_template_string(template, doc=d)

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
