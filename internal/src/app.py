from flask import Flask, redirect, request, render_template, jsonify
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jwt, os, uuid
import logging

app = Flask(__name__)

def set_owner(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
        user = records[0]['n']
        tx.run("MATCH (n:User {email: $email}) SET n.isMember = True, n.isOwner = True RETURN n", email=email)
        return user
    else:
        user = Node('User', id=str(uuid4()), email=email, isMember=True, isOwner=True)
        tx.create(user)
        return user

@app.route('/init', methods=['POST'])
def review_post():
    data = request.get_json()
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    tx = graph.begin()
    set_owner(tx, data.get('owner_email'))
    graph.commit(tx)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
