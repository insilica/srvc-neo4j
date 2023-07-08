from flask import Flask, request, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    document_port = os.getenv('DOCUMENT_PORT')
    review_port = os.getenv('REVIEW_PORT')
    upload_port = os.getenv('UPLOAD_PORT')
    labels_port = os.getenv('LABELS_PORT')
    return render_template('index.html', 
                           document_port=document_port, 
                           review_port=review_port, 
                           upload_port=upload_port,
                           labels_port=labels_port)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
