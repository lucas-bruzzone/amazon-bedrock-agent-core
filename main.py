import boto3
import json
import sys
import os
from typing import Dict, Any

# Adicionar diretório tools ao path
sys.path.append('tools')

from ferramenta1 import lambda_handler as upload_handler
from ferramenta2 import lambda_handler as textract_handler
from ferramenta3 import lambda_handler as rekognition_handler

class DocumentValidationAgent:
    def __init__(self):
        self.bedrock_agent_client = boto3.client('bedrock-agent')
        self.bedrock_runtime = boto3.client('bedrock-agent-runtime')
        
        # Configurações do agente
        self.agent_id = None
        self.agent_alias_id = None
        self.session_id = "document-validation-session"
        
        # Estado da conversação
        self.document_s3_info = None
        self.selfie_s3_info = None
        
    def create_agent(self):
        """Criar agente Bedrock"""
        try:
            # Instruções do agente
            instructions = """
            Você é um assistente especializado em validação de documentos com foto.
            
            SEU FLUXO DE TRABALHO:
            
            FASE 1 - DOCUMENTO:
            1. Solicite ao usuário que envie a foto de um documento de identidade (RG, CNH, etc.)
            2. Quando receber a imagem em base64, use a ferramenta upload_to_s3
            3. Em seguida, use a ferramenta extract_text_from_document para extrair os dados
            4. Apresente os dados extraídos (CPF, nome, data de nascimento) ao usuário
            
            FASE 2 - SELFIE E VALIDAÇÃO:
            5. Após extrair os dados do documento, solicite uma selfie do usuário
            6. Quando receber a selfie em base64, use a ferramenta upload_to_s3
            7. Use a ferramenta compare_faces para comparar a face do documento com a selfie
            8. Informe se a validação foi bem-sucedida (similaridade >= 80%)
            
            INSTRUÇÕES IMPORTANTES:
            - Seja claro e educado em suas instruções
            - Explique cada etapa do processo
            - Em caso de erro, explique o problema e oriente o usuário
            - Mantenha o foco no fluxo sequencial: documento → dados → selfie → validação
            """
            
            # Criar agente
            response = self.bedrock_agent_client.create_agent(
                agentName='DocumentValidationAgent',
                agentResourceRoleArn='arn:aws:iam::369409857483:role/BedrockDocumentValidationRole',
                description='Agente para validação de documentos com foto',
                foundationModel='anthropic.claude-3-5-sonnet-20241022-v2:0',
                instruction=instructions,
                idleSessionTTLInSeconds=3600
            )
            
            self.agent_id = response['agent']['agentId']
            print(f"Agente criado com ID: {self.agent_id}")
            
            # Criar action groups
            self._create_action_groups()
            
            # Preparar agente
            self.bedrock_agent_client.prepare_agent(agentId=self.agent_id)
            
            # Criar alias
            alias_response = self.bedrock_agent_client.create_agent_alias(
                agentId=self.agent_id,
                agentAliasName='DRAFT'
            )
            
            self.agent_alias_id = alias_response['agentAlias']['agentAliasId']
            print(f"Alias criado: {self.agent_alias_id}")
            
        except Exception as e:
            print(f"Erro ao criar agente: {e}")
            
    def _create_action_groups(self):
        """Criar action groups para as ferramentas"""
        
        # Action Group 1 - Upload S3
        upload_schema = {
            "type": "object",
            "properties": {
                "image_data": {
                    "type": "string",
                    "description": "Imagem codificada em base64"
                }
            },
            "required": ["image_data"]
        }
        
        self.bedrock_agent_client.create_agent_action_group(
            agentId=self.agent_id,
            agentVersion='DRAFT',
            actionGroupName='upload_to_s3',
            description='Ferramenta para upload de imagens para S3',
            actionGroupExecutor={
                'customControl': 'RETURN_CONTROL'
            },
            functionSchema={
                'functions': [
                    {
                        'name': 'upload_to_s3',
                        'description': 'Faz upload de uma imagem em base64 para o S3',
                        'parameters': upload_schema
                    }
                ]
            }
        )
        
        # Action Group 2 - Textract
        textract_schema = {
            "type": "object",
            "properties": {
                "bucket": {
                    "type": "string",
                    "description": "Nome do bucket S3"
                },
                "key": {
                    "type": "string", 
                    "description": "Chave do objeto no S3"
                }
            },
            "required": ["bucket", "key"]
        }
        
        self.bedrock_agent_client.create_agent_action_group(
            agentId=self.agent_id,
            agentVersion='DRAFT',
            actionGroupName='extract_text_from_document',
            description='Ferramenta para extrair texto de documentos usando Textract',
            actionGroupExecutor={
                'customControl': 'RETURN_CONTROL'
            },
            functionSchema={
                'functions': [
                    {
                        'name': 'extract_text_from_document',
                        'description': 'Extrai texto e dados específicos de um documento',
                        'parameters': textract_schema
                    }
                ]
            }
        )
        
        # Action Group 3 - Rekognition
        rekognition_schema = {
            "type": "object",
            "properties": {
                "source_bucket": {
                    "type": "string",
                    "description": "Bucket da imagem fonte (documento)"
                },
                "source_key": {
                    "type": "string",
                    "description": "Chave da imagem fonte no S3"
                },
                "target_bucket": {
                    "type": "string",
                    "description": "Bucket da imagem alvo (selfie)"
                },
                "target_key": {
                    "type": "string",
                    "description": "Chave da imagem alvo no S3"
                }
            },
            "required": ["source_bucket", "source_key", "target_bucket", "target_key"]
        }
        
        self.bedrock_agent_client.create_agent_action_group(
            agentId=self.agent_id,
            agentVersion='DRAFT',
            actionGroupName='compare_faces',
            description='Ferramenta para comparar faces usando Rekognition',
            actionGroupExecutor={
                'customControl': 'RETURN_CONTROL'
            },
            functionSchema={
                'functions': [
                    {
                        'name': 'compare_faces',
                        'description': 'Compara faces entre duas imagens',
                        'parameters': rekognition_schema
                    }
                ]
            }
        )
        
    def _execute_action(self, action_group: str, function: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Executar ação localmente"""
        
        # Criar evento no formato esperado pelas ferramentas
        event = {
            'actionGroup': action_group,
            'function': function,
            'parameters': [{'name': k, 'value': v} for k, v in parameters.items()]
        }
        
        # Roteamento para handlers apropriados
        if action_group == 'upload_to_s3':
            return upload_handler(event, None)
        elif action_group == 'extract_text_from_document':
            return textract_handler(event, None)
        elif action_group == 'compare_faces':
            return rekognition_handler(event, None)
        else:
            return {'response': {'error': 'Action group não encontrado'}}
    
    def chat(self, user_input: str) -> str:
        """Interface de chat com o agente"""
        try:
            # Invocar agente
            response = self.bedrock_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=self.session_id,
                inputText=user_input
            )
            
            # Processar resposta
            result = ""
            event_stream = response['completion']
            
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result += chunk['bytes'].decode('utf-8')
                elif 'returnControl' in event:
                    # Executar ação solicitada
                    control_event = event['returnControl']
                    invocation_id = control_event['invocationId']
                    
                    if 'invocationInputs' in control_event:
                        for input_item in control_event['invocationInputs']:
                            if 'functionInvocationInput' in input_item:
                                func_input = input_item['functionInvocationInput']
                                action_group = func_input['actionGroup']
                                function = func_input['function']
                                parameters = {p['name']: p['value'] for p in func_input.get('parameters', [])}
                                
                                # Executar função localmente
                                action_result = self._execute_action(action_group, function, parameters)
                                
                                # Retornar resultado para o agente
                                self.bedrock_runtime.invoke_agent(
                                    agentId=self.agent_id,
                                    agentAliasId=self.agent_alias_id,
                                    sessionId=self.session_id,
                                    inputText="",
                                    returnControlInvocationResults=[
                                        {
                                            'functionResult': {
                                                'actionGroup': action_group,
                                                'function': function,
                                                'responseBody': {
                                                    'TEXT': {
                                                        'body': json.dumps(action_result['response'])
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                )
            
            return result
            
        except Exception as e:
            return f"Erro na conversa: {str(e)}"

def main():
    """Função principal"""
    print("Iniciando Agente de Validação de Documentos...")
    
    # Criar instância do agente
    agent = DocumentValidationAgent()
    
    # Opção para usar agente existente ou criar novo
    use_existing = input("Usar agente existente? (s/n): ").lower() == 's'
    
    if use_existing:
        agent.agent_id = input("Digite o ID do agente: ")
        agent.agent_alias_id = input("Digite o ID do alias: ")
    else:
        agent.create_agent()
    
    print("\n" + "="*50)
    print("AGENTE DE VALIDAÇÃO DE DOCUMENTOS")
    print("="*50)
    print("O agente irá guiá-lo através do processo de validação.")
    print("Digite 'sair' para encerrar.\n")
    
    # Loop principal de conversa
    while True:
        user_input = input("Você: ")
        
        if user_input.lower() in ['sair', 'exit', 'quit']:
            break
        
        print("Agente: ", end="")
        response = agent.chat(user_input)
        print(response)
        print()

if __name__ == "__main__":
    main()