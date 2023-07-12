from bs4 import BeautifulSoup
from flask import Flask, redirect, request, render_template, Response
import os, requests

app = Flask(__name__)

from bs4 import BeautifulSoup

def embed_response(service_url):
    if request.method == 'POST':
        files = {name: (file.filename, file.stream.read(), file.content_type) for name, file in request.files.items()}
        response = requests.post(service_url, data=request.form, files=files)
    elif request.method == 'HEAD':
        response = requests.head(service_url)
    else:
        response = requests.get(service_url, params=request.args)

    soup = BeautifulSoup(response.content, 'html.parser')
    if soup.head is not None:
        extra_head = ''.join(str(child) for child in soup.head.children)
    else:
        extra_head = ''
    if soup.head is not None:
        content = ''.join(str(child) for child in soup.body.children)
    else:
        content = ''

    rel_path = ''
    document_path = rel_path + os.getenv('DOCUMENT_PATH')
    review_path = rel_path + os.getenv('REVIEW_PATH')
    upload_path = rel_path + os.getenv('UPLOAD_PATH')
    labels_path = rel_path + os.getenv('LABELS_PATH')
    settings_path = rel_path + os.getenv('SETTINGS_PATH')

    final_content = render_template('index.html',
                           extra_head=extra_head,
                           content=content,
                           document_path=document_path,
                           review_path=review_path,
                           upload_path=upload_path,
                           labels_path=labels_path,
                           settings_path=settings_path)

    return Response(final_content, mimetype=response.headers.get('content-type'))

@app.route('/<string:service_name>', defaults={'subpath': None}, methods=['GET', 'POST', 'HEAD'])
@app.route('/<string:service_name>/<path:subpath>', methods=['GET', 'POST', 'HEAD'])
def user_project_service(service_name, subpath):
    if subpath:
        return embed_response(f"http://{service_name}:5000/{subpath}")
    else:
        return embed_response(f"http://{service_name}:5000/")

@app.route('/')
def index():
    rel_path = '/'
    return redirect(rel_path + 'document')
    document_path = rel_path + os.getenv('DOCUMENT_PATH')
    review_path = rel_path + os.getenv('REVIEW_PATH')
    upload_path = rel_path + os.getenv('UPLOAD_PATH')
    labels_path = rel_path + os.getenv('LABELS_PATH')
    settings_path = rel_path + os.getenv('SETTINGS_PATH')
    return render_template('index.html',
                           document_path=document_path,
                           review_path=review_path,
                           upload_path=upload_path,
                           labels_path=labels_path,
                           settings_path=settings_path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
