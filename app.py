# app.py
import os
import time
import csv
from googlesearch import search
from tqdm import tqdm
from flask import Flask, request, jsonify

# --- CONFIGURAÇÕES ---
# A lista de sites agora serve apenas para a API informar quais estão disponíveis
SITES_BUSCA = ["linkedin.com/jobs", "indeed.com", "glassdoor.com.br", "gupy.io", "vagas.com.br", "infojobs.com.br", "https://riovagas.com.br"] 
PAUSA_SEGUNDOS = 2.5

# A função de busca permanece quase a mesma, mas sem a barra de progresso (tqdm)
# pois ela não faz sentido em uma API.
def buscar_vagas_api(cargo, localizacao, sites_para_buscar, num_resultados):
    sites_formatados = " OR ".join([f"site:{site}" for site in sites_para_buscar])
    consulta = f'"{cargo}" vagas {sites_formatados} "{localizacao}"'
    print(f"INFO: Recebida requisição de busca. Consulta: {consulta}")

    resultados = []
    try:
        # A função search não é mais envolvida pelo tqdm
        for url in search(consulta, num_results=num_resultados):
            resultados.append(url)
            time.sleep(PAUSA_SEGUNDOS)
    except Exception as e:
        print(f"[ERRO] Ocorreu um erro durante a busca: {e}")
        return None 
    
    # Remove duplicatas e ordena
    resultados_unicos = sorted(list(set(resultados)))
    return resultados_unicos

# --- CRIAÇÃO DA API ---
app = Flask(__name__)

# Endpoint para o bot Baileys chamar
@app.route('/buscar_vagas', methods=['POST'])
def handle_busca():
    # 1. Pega os dados enviados pelo bot Baileys (em formato JSON)
    dados = request.json
    
    # Validação básica dos dados recebidos
    if not all(k in dados for k in ['cargo', 'localizacao', 'sites', 'quantidade']):
        return jsonify({"erro": "Dados incompletos. 'cargo', 'localizacao', 'sites' e 'quantidade' são obrigatórios."}), 400

    cargo = dados['cargo']
    localizacao = dados['localizacao']
    sites = dados['sites'] # Espera-se uma lista de sites
    quantidade = dados['quantidade']
    
    # 2. Chama a nossa função de busca
    resultados = buscar_vagas_api(cargo, localizacao, sites, quantidade)
    
    # 3. Retorna os resultados em formato JSON para o bot Baileys
    if resultados is not None:
        print(f"INFO: Busca concluída. {len(resultados)} vagas encontradas.")
        return jsonify(resultados)
    else:
        return jsonify({"erro": "A busca falhou no servidor."}), 500

if __name__ == '__main__':
    # Roda o servidor da API. Ele ficará esperando por requisições.
    # O endereço 0.0.0.0 permite que ele seja acessado por outros na mesma rede.
    app.run(host='0.0.0.0', port=5000, debug=True)