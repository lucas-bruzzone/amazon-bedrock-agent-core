import boto3
import base64
import json
from typing import Dict, Any
from datetime import datetime
import uuid

def upload_to_s3(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ferramenta 1: Upload de imagem em base64 para S3
    """
    try:
        # Configurar cliente S3
        s3_client = boto3.client('s3')
        
        # Extrair parâmetros
        parameters = event.get('parameters', [])
        image_base64 = None
        bucket_name = 'document-validation-poc'  # Configurar seu bucket
        
        # Buscar parâmetro image_data
        for param in parameters:
            if param['name'] == 'image_data':
                image_base64 = param['value']
                break
                
        if not image_base64:
            return {
                'response': {
                    'error': 'Parâmetro image_data não encontrado'
                }
            }
        
        # Remover prefixo data:image/... se existir
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decodificar base64
        image_bytes = base64.b64decode(image_base64)
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_key = f"images/{timestamp}_{unique_id}.jpg"
        
        # Upload para S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        
        # Retornar informações do upload
        s3_uri = f"s3://{bucket_name}/{file_key}"
        
        return {
            'response': {
                'success': True,
                'bucket': bucket_name,
                'key': file_key,
                's3_uri': s3_uri,
                'message': f'Imagem uploaded com sucesso para {s3_uri}'
            }
        }
        
    except Exception as e:
        return {
            'response': {
                'error': f'Erro ao fazer upload: {str(e)}'
            }
        }

# Função para o Action Group
def lambda_handler(event, context):
    """Handler principal para o Action Group"""
    action = event.get('actionGroup', '')
    function = event.get('function', '')
    
    if function == 'upload_to_s3':
        return upload_to_s3(event)
    
    return {
        'response': {
            'error': 'Função não encontrada'
        }
    }