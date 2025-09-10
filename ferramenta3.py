import boto3
import json
from typing import Dict, Any

def compare_faces(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ferramenta 3: Comparação de faces usando Rekognition
    """
    try:
        # Configurar cliente Rekognition
        rekognition_client = boto3.client('rekognition')
        
        # Extrair parâmetros
        parameters = event.get('parameters', [])
        source_bucket = None
        source_key = None
        target_bucket = None
        target_key = None
        
        # Buscar parâmetros
        for param in parameters:
            if param['name'] == 'source_bucket':
                source_bucket = param['value']
            elif param['name'] == 'source_key':
                source_key = param['value']
            elif param['name'] == 'target_bucket':
                target_bucket = param['value']
            elif param['name'] == 'target_key':
                target_key = param['value']
        
        if not all([source_bucket, source_key, target_bucket, target_key]):
            return {
                'response': {
                    'error': 'Todos os parâmetros são obrigatórios: source_bucket, source_key, target_bucket, target_key'
                }
            }
        
        # Comparar faces
        response = rekognition_client.compare_faces(
            SourceImage={
                'S3Object': {
                    'Bucket': source_bucket,
                    'Name': source_key
                }
            },
            TargetImage={
                'S3Object': {
                    'Bucket': target_bucket,
                    'Name': target_key
                }
            },
            SimilarityThreshold=80.0  # 80% threshold conforme solicitado
        )
        
        # Analisar resultado
        face_matches = response.get('FaceMatches', [])
        
        if face_matches:
            # Pegar a maior similaridade encontrada
            best_match = max(face_matches, key=lambda x: x['Similarity'])
            similarity = best_match['Similarity']
            
            # Determinar se passou na validação
            validated = similarity >= 80.0
            
            return {
                'response': {
                    'success': True,
                    'validated': validated,
                    'similarity': round(similarity, 2),
                    'threshold': 80.0,
                    'face_matches_found': len(face_matches),
                    'message': f'Comparação realizada. Similaridade: {similarity:.2f}%. {"Validado" if validated else "Não validado"}'
                }
            }
        else:
            return {
                'response': {
                    'success': True,
                    'validated': False,
                    'similarity': 0.0,
                    'threshold': 80.0,
                    'face_matches_found': 0,
                    'message': 'Nenhuma correspondência facial encontrada acima do threshold de 80%'
                }
            }
        
    except Exception as e:
        # Tratar erros específicos do Rekognition
        error_message = str(e)
        
        if 'InvalidImageFormatException' in error_message:
            return {
                'response': {
                    'error': 'Formato de imagem inválido. Use JPG ou PNG.'
                }
            }
        elif 'InvalidS3ObjectException' in error_message:
            return {
                'response': {
                    'error': 'Objeto não encontrado no S3 ou inacessível.'
                }
            }
        elif 'InvalidParameterException' in error_message:
            return {
                'response': {
                    'error': 'Nenhuma face detectada em uma das imagens.'
                }
            }
        else:
            return {
                'response': {
                    'error': f'Erro na comparação de faces: {error_message}'
                }
            }

def get_face_details(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função auxiliar para detectar faces em uma imagem
    """
    try:
        rekognition_client = boto3.client('rekognition')
        
        parameters = event.get('parameters', [])
        bucket = None
        key = None
        
        for param in parameters:
            if param['name'] == 'bucket':
                bucket = param['value']
            elif param['name'] == 'key':
                key = param['value']
        
        if not bucket or not key:
            return {
                'response': {
                    'error': 'Parâmetros bucket e key são obrigatórios'
                }
            }
        
        response = rekognition_client.detect_faces(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            Attributes=['ALL']
        )
        
        faces = response.get('FaceDetails', [])
        
        return {
            'response': {
                'success': True,
                'faces_detected': len(faces),
                'face_details': faces,
                'message': f'{len(faces)} face(s) detectada(s) na imagem'
            }
        }
        
    except Exception as e:
        return {
            'response': {
                'error': f'Erro ao detectar faces: {str(e)}'
            }
        }

# Função para o Action Group
def lambda_handler(event, context):
    """Handler principal para o Action Group"""
    action = event.get('actionGroup', '')
    function = event.get('function', '')
    
    if function == 'compare_faces':
        return compare_faces(event)
    elif function == 'get_face_details':
        return get_face_details(event)
    
    return {
        'response': {
            'error': 'Função não encontrada'
        }
    }