import boto3
import json
from typing import Dict, Any
import re

def extract_text_from_document(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ferramenta 2: Extração de texto de documento usando Textract
    """
    try:
        # Configurar cliente Textract
        textract_client = boto3.client('textract')
        
        # Extrair parâmetros
        parameters = event.get('parameters', [])
        bucket_name = None
        object_key = None
        
        # Buscar parâmetros
        for param in parameters:
            if param['name'] == 'bucket':
                bucket_name = param['value']
            elif param['name'] == 'key':
                object_key = param['value']
        
        if not bucket_name or not object_key:
            return {
                'response': {
                    'error': 'Parâmetros bucket e key são obrigatórios'
                }
            }
        
        # Analisar documento
        response = textract_client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            },
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        # Extrair texto completo
        extracted_text = ""
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                extracted_text += block['Text'] + " "
        
        # Extrair dados específicos
        dados_extraidos = extract_document_data(extracted_text)
        
        return {
            'response': {
                'success': True,
                'raw_text': extracted_text.strip(),
                'extracted_data': dados_extraidos,
                'message': 'Dados extraídos com sucesso do documento'
            }
        }
        
    except Exception as e:
        return {
            'response': {
                'error': f'Erro ao extrair texto: {str(e)}'
            }
        }

def extract_document_data(text: str) -> Dict[str, str]:
    """
    Extrai CPF, nome e data de nascimento do texto
    """
    dados = {
        'cpf': None,
        'nome': None,
        'data_nascimento': None
    }
    
    # Padrões regex
    cpf_pattern = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    data_pattern = r'\b\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}\b'
    
    # Buscar CPF
    cpf_match = re.search(cpf_pattern, text)
    if cpf_match:
        cpf = cpf_match.group()
        # Normalizar CPF (remover pontos e traços)
        dados['cpf'] = re.sub(r'[^\d]', '', cpf)
    
    # Buscar data de nascimento
    data_matches = re.findall(data_pattern, text)
    if data_matches:
        # Pegar a primeira data encontrada (assumindo que é a data de nascimento)
        dados['data_nascimento'] = data_matches[0]
    
    # Buscar nome (lógica mais complexa - tentar identificar nome próprio)
    # Procurar por palavras em maiúsculo que possam ser nome
    palavras = text.split()
    possivel_nome = []
    
    for i, palavra in enumerate(palavras):
        # Se a palavra está em maiúsculas e tem mais de 2 caracteres
        if palavra.isupper() and len(palavra) > 2 and palavra.isalpha():
            possivel_nome.append(palavra)
            # Pegar próximas palavras em maiúsculo também
            for j in range(i+1, min(i+4, len(palavras))):
                if palavras[j].isupper() and palavras[j].isalpha() and len(palavras[j]) > 1:
                    possivel_nome.append(palavras[j])
                else:
                    break
            break
    
    if possivel_nome:
        dados['nome'] = ' '.join(possivel_nome)
    
    # Se não encontrou nome em maiúsculo, procurar padrão "NOME:" ou similar
    nome_patterns = [
        r'NOME[:\s]+([A-Z\s]{10,50})',
        r'NOME COMPLETO[:\s]+([A-Z\s]{10,50})',
        r'TITULAR[:\s]+([A-Z\s]{10,50})'
    ]
    
    for pattern in nome_patterns:
        match = re.search(pattern, text)
        if match and not dados['nome']:
            dados['nome'] = match.group(1).strip()
            break
    
    return dados

# Função para o Action Group
def lambda_handler(event, context):
    """Handler principal para o Action Group"""
    action = event.get('actionGroup', '')
    function = event.get('function', '')
    
    if function == 'extract_text_from_document':
        return extract_text_from_document(event)
    
    return {
        'response': {
            'error': 'Função não encontrada'
        }
    }