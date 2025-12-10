import boto3
import json
import uuid
import os
from datetime import datetime
from PIL import Image

# ------------------ CONFIGURAÇÃO AWS ------------------

# S3
s3 = boto3.client(
    's3',
    aws_access_key_id='REPLACE_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='REPLACE_AWS_SECRET_ACCESS_KEY',
    region_name='us-east-1'
)
BUCKET = 'bucket-periodicos'

# DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id='REPLACE_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='REPLACE_AWS_SECRET_ACCESS_KEY',
    region_name='us-east-1'
)
log_table = dynamodb.Table('Logs')

# SQS
sqs = boto3.client(
    'sqs',
    aws_access_key_id='REPLACE_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='REPLACE_AWS_SECRET_ACCESS_KEY',
    region_name='us-east-1'
)
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/166025968035/ArquivoUploadsQueue'

# ------------------ FUNÇÃO DE LOG ------------------
def log_acao(acao, tipo, dados):
    log_table.put_item(
        Item={
            'id': str(uuid.uuid4()),
            'acao': acao,
            'tipo': tipo,
            'dados': json.dumps(dados),
            'hora': datetime.utcnow().isoformat()
        }
    )

# ------------------ WORKER ------------------
print("Worker iniciado e aguardando mensagens da fila SQS...")

while True:
    try:
        resp = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        messages = resp.get('Messages', [])
        if not messages:
            continue

        for msg in messages:
            body = json.loads(msg['Body'])
            chave = body.get('arquivo')
            if not chave:
                print("[ERRO] Mensagem sem 'arquivo'")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                continue

            # Extrair extensão do arquivo
            _, ext = os.path.splitext(chave)
            if ext.lower() not in ['.jpg', '.jpeg', '.png']:
                print(f"[ERRO] Extensão desconhecida: {ext} para {chave}")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                continue

            # Baixar arquivo do S3
            file_local = f"/tmp/{uuid.uuid4()}{ext}"
            s3.download_file(BUCKET, chave, file_local)

            # Processar imagem (exemplo: redimensionar)
            try:
                img = Image.open(file_local)
                img = img.resize((800, 600))
                img.save(file_local)  # sobrescreve arquivo processado

                # Opcional: enviar de volta para S3 em uma pasta de processados
                chave_processado = chave.replace("revistas/", "revistas_processadas/")
                s3.upload_file(file_local, BUCKET, chave_processado)

                log_acao('processar', 'imagem', {'arquivo_original': chave, 'arquivo_processado': chave_processado})
                print(f"[OK] Imagem processada: {chave}")

            except Exception as e:
                print(f"[ERRO] Falha ao processar imagem {chave}: {e}")

            # Deletar mensagem da fila
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])

    except Exception as e:
        print(f"[ERRO] Falha no worker: {e}")

