from DadosAbertosBrasil import ibge
import os
from datetime import datetime
import pandas as pd

class IBGEKnowledgeBase:
    def __init__(self, output_dir="base_conhecimento_ibge"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def salvar_texto(self, filename, content):
        """Salva conteúdo em arquivo txt"""
        filepath = os.path.join(self.output_dir, f"{filename}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Salvo: {filepath}")
    
    def formatar_localidades(self):
        """Gera base sobre localidades brasileiras"""
        print("Extraindo dados de localidades...")
        
        # Estados
        estados = ibge.localidades(nivel="estados")
        content = "=== LOCALIDADES BRASILEIRAS ===\n\n"
        content += "ESTADOS DO BRASIL:\n\n"
        
        for _, row in estados.iterrows():
            content += f"Estado: {row['nome']} ({row['sigla']})\n"
            content += f"Código IBGE: {row['id']}\n"
            content += f"Região: {row['regiao_nome']} ({row['regiao_sigla']})\n\n"
        
        # Municípios por estado (amostra)
        content += "\nMUNICÍPIOS PRINCIPAIS:\n\n"
        
        for _, estado in estados.head(5).iterrows():  # Top 5 estados
            try:
                municipios = ibge.localidades(
                    nivel="estados", 
                    divisoes="municipios", 
                    localidade=str(estado['id'])  # Converter para string
                )
                content += f"Municípios de {estado['nome']}:\n"
                
                for _, mun in municipios.head(10).iterrows():  # Top 10 municípios
                    content += f"  - {mun['nome']} (Código: {mun['id']})\n"
                content += "\n"
            except Exception as e:
                content += f"Erro ao carregar municípios de {estado['nome']}: {e}\n\n"
        
        self.salvar_texto("01_localidades", content)
    
    def formatar_populacao(self):
        """Gera base sobre dados populacionais"""
        print("Extraindo dados populacionais...")
        
        content = "=== DADOS POPULACIONAIS DO BRASIL ===\n\n"
        
        # População estimada por UF (tabela 6579)
        try:
            meta = ibge.Metadados(6579)
            pop_data = ibge.sidra(
                tabela=6579,
                periodos='last',
                localidades={3: 'all'}
            )
            
            content += f"POPULAÇÃO ESTIMADA {pop_data['Ano'].iloc[0]}:\n\n"
            
            for _, row in pop_data.iterrows():
                uf = row['Unidade da Federação']
                pop = int(row['Valor'])
                content += f"{uf}: {pop:,} habitantes\n"
            
            content += f"\nTotal Brasil: {pop_data['Valor'].sum():,} habitantes\n\n"
            
        except Exception as e:
            content += f"Erro ao carregar dados populacionais: {e}\n\n"
        
        # Projeções populacionais
        try:
            proj = ibge.populacao()
            content += "PROJEÇÕES POPULACIONAIS:\n"
            if isinstance(proj, dict):
                content += f"População projetada: {proj.get('projecao', {}).get('populacao', 'N/A'):,}\n"
        except:
            pass
        
        self.salvar_texto("02_populacao", content)
    
    def formatar_nomes(self):
        """Gera base sobre estatísticas de nomes"""
        print("Extraindo dados de nomes...")
        
        content = "=== ESTATÍSTICAS DE NOMES BRASILEIROS ===\n\n"
        
        # Ranking geral de nomes
        try:
            ranking = ibge.nomes_ranking()
            content += "NOMES MAIS POPULARES NO BRASIL:\n\n"
            
            for i, row in ranking.head(20).iterrows():
                content += f"{i+1}. {row['nome']}: {row['frequencia']:,} nascimentos\n"
            
            content += "\n"
            
            # Nomes por década
            ranking_90 = ibge.nomes_ranking(decada=1990)
            content += "NOMES MAIS POPULARES NA DÉCADA DE 1990:\n\n"
            
            for i, row in ranking_90.head(10).iterrows():
                content += f"{i+1}. {row['nome']}: {row['frequencia']:,} nascimentos\n"
            
        except Exception as e:
            content += f"Erro ao carregar dados de nomes: {e}\n"
        
        self.salvar_texto("03_nomes", content)
    
    def formatar_territorios(self):
        """Gera base sobre dados territoriais"""
        print("Extraindo dados territoriais...")
        
        content = "=== DADOS TERRITORIAIS ===\n\n"
        
        # Área por UF
        try:
            area_data = ibge.sidra(
                tabela=1301,
                variaveis=[615],  # Área total
                localidades={3: 'all'}
            )
            
            content += "ÁREA TERRITORIAL POR ESTADO:\n\n"
            
            for _, row in area_data.iterrows():
                uf = row['Unidade da Federação']
                area = float(row['Valor'])
                content += f"{uf}: {area:,.1f} km²\n"
            
            content += f"\nTotal Brasil: {area_data['Valor'].astype(float).sum():,.1f} km²\n\n"
            
        except Exception as e:
            content += f"Erro ao carregar dados territoriais: {e}\n"
        
        self.salvar_texto("04_territorio", content)
    
    def formatar_metadata(self):
        """Gera metadados sobre as fontes"""
        content = f"=== METADADOS DA BASE DE CONHECIMENTO ===\n\n"
        content += f"Data de geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Fonte: Instituto Brasileiro de Geografia e Estatística (IBGE)\n"
        content += f"Biblioteca: DadosAbertosBrasil\n"
        content += f"APIs utilizadas:\n"
        content += f"  - SIDRA (Sistema IBGE de Recuperação Automática)\n"
        content += f"  - Localidades\n"
        content += f"  - Nomes 2.0\n"
        content += f"  - Projeções Populacionais\n\n"
        content += f"Estrutura dos arquivos:\n"
        content += f"  01_localidades.txt - Estados, regiões e municípios\n"
        content += f"  02_populacao.txt - Dados demográficos\n"
        content += f"  03_nomes.txt - Estatísticas de nomes\n"
        content += f"  04_territorio.txt - Dados geográficos\n"
        
        self.salvar_texto("00_metadata", content)
    
    def gerar_base_completa(self):
        """Gera toda a base de conhecimento"""
        print("=== GERANDO BASE DE CONHECIMENTO IBGE ===\n")
        
        self.formatar_metadata()
        self.formatar_localidades()
        self.formatar_populacao()
        self.formatar_nomes()
        self.formatar_territorios()
        
        print(f"\n✅ Base gerada em: {self.output_dir}/")
        print("Arquivos prontos para uso em sistema RAG!")

# Uso
if __name__ == "__main__":
    generator = IBGEKnowledgeBase()
    generator.gerar_base_completa()