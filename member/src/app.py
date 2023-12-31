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

def get_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']

def get_users():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    users = graph.run("MATCH (n:User) RETURN n").data()
    return [dict(x['n']) for x in users]

def set_member(tx, email):
    query = """
    MERGE (u:User {email: $email})
    ON CREATE SET u.id = $id, u.isMember = True
    ON MATCH SET u.isMember = True
    RETURN u
    """
    result = tx.run(query, email=email, id=str(uuid4()))
    return result.data()[0]['u']

@app.route('/add-member', methods=['POST'])
def add_member():
    member_email = request.form['email']
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    tx = graph.begin()
    set_member(tx, member_email)
    graph.commit(tx)
    return redirect('../' + os.getenv('MEMBER_PATH')), 303

@app.route('/')
def home():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    members = get_users()
    return render_template('list.html', members=members, member_path=os.getenv('MEMBER_PATH'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
