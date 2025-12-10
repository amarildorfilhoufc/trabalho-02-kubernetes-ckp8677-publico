from flask import Flask, request, jsonify
import boto3
import uuid

app = Flask(__name__)

# Configurar S3
s3 = boto3.client('s3')
BUCKET = 'bucket-periodicos'

@app.route('/revistas/upload', methods=['POST'])
def upload_capa():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    chave = f"revistas/{uuid.uuid4()}_{file.filename}"

    # Envia para S3
    s3.upload_fileobj(file, BUCKET, chave)

    url = f"https://{BUCKET}.s3.amazonaws.com/{chave}"
    return jsonify({"mensagem": "Arquivo enviado!", "url": url})
