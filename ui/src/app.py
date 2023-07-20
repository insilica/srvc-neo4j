from bs4 import BeautifulSoup
from flask import Flask, redirect, request, render_template, Response
import json, jwt, os, requests

app = Flask(__name__)

from bs4 import BeautifulSoup

def embed_response(service_url):
    if request.method == 'POST':
        files = {name: (file.filename, file.stream.read(), file.content_type) for name, file in request.files.items()}
        json_data = request.get_json(silent=True)
        if json_data is not None:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(service_url, cookies=request.cookies, allow_redirects=False, data=json.dumps(json_data).encode(), headers=headers)
        elif files:
           response = requests.post(service_url, cookies=request.cookies, allow_redirects=False, data=request.form, files=files)
        else:
           response = requests.post(service_url, cookies=request.cookies, allow_redirects=False, data=request.form)
    elif request.method == 'HEAD':
        response = requests.head(service_url, cookies=request.cookies, allow_redirects=False)
    else:
        response = requests.get(service_url, cookies=request.cookies, allow_redirects=False, params=request.args)

    if not response.headers.get('content-type').startswith('text/html'):
        return Response(response.content, headers=dict(response.headers), status=response.status_code)

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
    data_path = rel_path + os.getenv('DATA_PATH')
    document_path = rel_path + os.getenv('DOCUMENT_PATH')
    import_events_path = rel_path + os.getenv('IMPORT_EVENTS_PATH')
    review_path = rel_path + os.getenv('REVIEW_PATH')
    export_path = rel_path + os.getenv('EXPORT_PATH')
    upload_path = rel_path + os.getenv('UPLOAD_PATH')
    labels_path = rel_path + os.getenv('LABELS_PATH')
    member_path = rel_path + os.getenv('MEMBER_PATH')
    settings_path = rel_path + os.getenv('SETTINGS_PATH')

    final_content = render_template('index.html',
                           extra_head=extra_head,
                           content=content,
                           data_path=data_path,
                           document_path=document_path,
                           import_events_path=import_events_path,
                           review_path=review_path,
                           export_path=export_path,
                           upload_path=upload_path,
                           labels_path=labels_path,
                           member_path=member_path,
                           settings_path=settings_path)
    return Response(final_content, headers=dict(response.headers), status=response.status_code)

@app.route('/<string:service_name>', defaults={'subpath': None}, methods=['GET', 'POST', 'HEAD'])
@app.route('/<string:service_name>/<path:subpath>', methods=['GET', 'POST', 'HEAD'])
def user_project_service(service_name, subpath):
    if service_name.lower() == 'internal':
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(' ')[1]
            payload = jwt.decode(auth_token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
            if payload.get('internal_access') != True:
                return 'Not Found', 404
        else:
            return 'Not Found', 404

    if subpath:
        return embed_response(f"http://{service_name}:5000/{subpath}")
    else:
        return embed_response(f"http://{service_name}:5000/")

@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

@app.route('/')
def index():
    rel_path = './'
    return redirect(rel_path + 'document'), 303

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
