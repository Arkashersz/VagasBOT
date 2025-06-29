import os
import time
import csv
from googlesearch import search
from tqdm import tqdm

# --- CONFIGURAÇÕES GLOBAIS ---
# Lista de sites que será apresentada ao usuário.
SITES_BUSCA = ["linkedin.com/jobs", "indeed.com", "glassdoor.com.br", "gupy.io", "vagas.com.br", "infojobs.com.br"] 
# Pausa entre as buscas para evitar bloqueios.
PAUSA_SEGUNDOS = 2.5

def buscar_vagas(cargo, localizacao, sites_para_buscar, num_resultados):
    """
    Realiza a busca no Google com base nos parâmetros personalizados pelo usuário.
    """
    sites_formatados = " OR ".join([f"site:{site}" for site in sites_para_buscar])
    consulta = f'"{cargo}" vagas {sites_formatados} "{localizacao}"'
    
    print(f"\nBuscando ~{num_resultados} vaga(s) para: '{cargo}' em '{localizacao}'...")
    print(f"Consulta gerada: {consulta}")

    resultados = []
    try:
        # Itera sobre os resultados da busca com uma barra de progresso
        for url in tqdm(search(consulta, num_results=num_resultados), desc="Buscando vagas", total=num_resultados, ncols=100, unit="vagas"):
            resultados.append(url)
            time.sleep(PAUSA_SEGUNDOS)
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro durante a busca: {e}")
        print("Isso pode ser um bloqueio temporário do Google ou um problema de conexão.")
        return None  # Retorna None para indicar que a busca falhou

    return resultados

def salvar_relatorio_csv(cargo, localizacao, resultados):
    """
    Salva a lista de URLs de vagas em um arquivo CSV estruturado.
    """
    nome_arquivo = f"vagas_{cargo.replace(' ', '_')}_{localizacao.replace(' ', '_')}.csv"
    
    try:
        with open(nome_arquivo, "w", newline="", encoding="utf-8") as arquivo_csv:
            writer = csv.writer(arquivo_csv)
            writer.writerow(["Cargo Buscado", "Localização", "Link da Vaga"])
            for url in resultados:
                writer.writerow([cargo, localizacao, url])
                
        print(f"\nRelatório com {len(resultados)} vagas únicas salvo em: {os.path.abspath(nome_arquivo)}")
    except IOError as e:
        print(f"\n[ERRO] Não foi possível salvar o arquivo: {e}")

def main():
    """
    Função principal que orquestra a interação com o usuário e a execução do script.
    """
    print("--- Buscador Automático de Vagas ---")
    
    # 1. ESCOLHA INTERATIVA DOS SITES
    print("\nSites disponíveis para busca:")
    for i, site in enumerate(SITES_BUSCA):
        print(f"  {i+1}. {site}")
    print(f"  {len(SITES_BUSCA)+1}. TODOS os sites listados")

    sites_escolhidos = []
    while not sites_escolhidos:
        try:
            escolha_site = int(input(f"\nEscolha o número do site (1 a {len(SITES_BUSCA)+1}): "))
            if 1 <= escolha_site <= len(SITES_BUSCA):
                sites_escolhidos.append(SITES_BUSCA[escolha_site - 1])
            elif escolha_site == len(SITES_BUSCA) + 1:
                sites_escolhidos = SITES_BUSCA
            else:
                print(f"[ERRO] Por favor, digite um número entre 1 e {len(SITES_BUSCA)+1}.")
        except ValueError:
            print("[ERRO] Por favor, digite apenas o número correspondente.")

    # 2. ESCOLHA INTERATIVA DA QUANTIDADE DE RESULTADOS
    num_vagas_desejado = 0
    while not (1 <= num_vagas_desejado <= 30):
        try:
            num_vagas_desejado = int(input("Digite a quantidade de resultados desejada (1 a 30): "))
            if not (1 <= num_vagas_desejado <= 30):
                print("[ERRO] O número de resultados deve estar entre 1 e 30.")
        except ValueError:
            print("[ERRO] Por favor, digite um número válido.")

    cargo = input("Digite o cargo, palavra-chave ou empresa: ")
    localizacao = input("Digite a cidade, estado, região ou remoto: ")
    
    resultados_brutos = buscar_vagas(cargo, localizacao, sites_escolhidos, num_vagas_desejado)
    
    if resultados_brutos is not None:
        resultados_unicos = sorted(list(set(resultados_brutos)))
        
        if resultados_unicos:
            salvar_relatorio_csv(cargo, localizacao, resultados_unicos)
        else:
            print("\nNenhuma vaga encontrada para os termos informados.")
    else:
        print("\nNão foi possível gerar o relatório devido a um erro na busca.")

if __name__ == "__main__":
    main()