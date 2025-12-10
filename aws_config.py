import json
import uuid
import datetime
import boto3
import os
from botocore.exceptions import ClientError

# =============================
# CONFIG MINIO (SUBSTITUI O S3)
# =============================
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "MINIO_PLACEHOLDER")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "MINIO_PLACEHOLDER")
S3_BUCKET = os.getenv("S3_BUCKET", "bucket-periodicos")

# =============================
# CONFIG DYNAMODB (MANTÉM AWS)
# =============================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DDB_TABLE = os.getenv("DDB_TABLE", "Logs")

session = boto3.session.Session(region_name=AWS_REGION)

dynamodb = session.resource("dynamodb")


# =============================
# MINIO CLIENT (BOTO3)
# =============================
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,                 # <<< ESSENCIAL
    aws_access_key_id=S3_ACCESS_KEY,         # <<< ESSENCIAL
    aws_secret_access_key=S3_SECRET_KEY,     # <<< ESSENCIAL
)

# =============================
# CARREGAR TABELA DYNAMODB
# =============================
try:
    log_table = dynamodb.Table(DDB_TABLE)
    log_table.load()
    print(f"✅ DynamoDB conectado: {DDB_TABLE}")
except Exception as e:
    print(f"❌ Erro DynamoDB: {e}")
    log_table = None

# =============================
# UPLOAD PARA MINIO
# =============================
def upload_s3(file_obj, key):
    try:
        s3.upload_fileobj(file_obj, S3_BUCKET, key)
        print(f"📁 Upload feito no MinIO: {key}")
        return True
    except Exception as e:
        print(f"❌ Erro upload MinIO: {e}")
        return False

# =============================
# LOG NO DYNAMODB
# =============================
def log_dynamodb(acao, dados):
    if log_table:
        try:
            log_table.put_item(
                Item={
                    "id": str(uuid.uuid4()),
                    "acao": acao,
                    "dados": json.dumps(dados, ensure_ascii=False),
                    "hora": datetime.datetime.now().isoformat(),
                    "timestamp": int(datetime.datetime.now().timestamp()),
                }
            )
            print(f"🪵 Log gravado no DynamoDB: {acao}")
        except ClientError as e:
            print(f"❌ Erro no DynamoDB: {e.response['Error']['Message']}")
    else:
        print("⚠️ DynamoDB indisponível.")

