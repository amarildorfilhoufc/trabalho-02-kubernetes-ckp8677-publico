import boto3

# Conexão com DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id='REPLACE_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='REPLACE_AWS_SECRET_ACCESS_KEY',
    region_name='us-east-1'
)

log_table = dynamodb.Table('Logs')  # Nome da tabela

# Buscar todos os logs
response = log_table.scan()

# Imprimir logs
for item in response['Items']:
    print(item)

