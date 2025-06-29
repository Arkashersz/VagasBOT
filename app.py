# app.py (Versão final com SeleniumBase para o RioVagas)

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from urllib.parse import quote
import time

# NOVO: Importa o Driver do SeleniumBase
from seleniumbase import Driver

# Headers para os scrapers que usam 'requests'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

# --- FUNÇÃO DE INICIALIZAÇÃO PARA SELENIUMBASE ---
def iniciar_driver_sb():
    """Inicializa e retorna uma instância do Driver do SeleniumBase em modo indetectável."""
    print("INFO: Iniciando driver com SeleniumBase (modo UC)...")
    # uc=True ativa o modo anti-detecção. headless=True roda sem interface gráfica.
    driver = Driver(uc=True, headless=True, agent=HEADERS["User-Agent"])
    return driver

# --- FUNÇÕES DE SCRAPING ---

# ... (as funções para Indeed, LinkedIn, InfoJobs e Catho permanecem as mesmas, usando requests) ...
def scrape_indeed(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca no Indeed: '{cargo}' em '{localizacao}' ---")
    resultados = []
    try:
        url = f"https://br.indeed.com/jobs?q={quote(cargo)}&l={quote(localizacao)}"
        resposta = requests.get(url, headers=HEADERS, timeout=10)
        resposta.raise_for_status()
        sopa = BeautifulSoup(resposta.text, 'lxml')
        cartoes_vaga = sopa.select('div.job_seen_beacon')
        for vaga in cartoes_vaga:
            titulo_tag = vaga.select_one('h2.jobTitle span, h2.jobTitle a span')
            titulo = titulo_tag.get('title', 'N/A') if titulo_tag else "N/A"
            link_tag = vaga.select_one('h2.jobTitle a')
            link = "https://br.indeed.com" + link_tag['href'] if link_tag and link_tag.has_attr('href') else "N/A"
            empresa_tag = vaga.select_one('span[data-testid="company-name"]')
            empresa = empresa_tag.text.strip() if empresa_tag else "N/A"
            local_tag = vaga.select_one('div[data-testid="text-location"]')
            local = local_tag.text.strip() if local_tag else "N/A"
            resultado_formatado = f"*{titulo}*\n🏢 Empresa: {empresa}\n📍 Local: {local}\n🔗 Link: {link}"
            resultados.append(resultado_formatado)
    except Exception as e:
        print(f"[ERRO] Falha no scraper do Indeed: {e}")
    print(f"--- [INFO] Finalizada busca no Indeed. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))

def scrape_linkedin(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca no LinkedIn: '{cargo}' em '{localizacao}' ---")
    resultados = []
    try:
        url = f"https://www.linkedin.com/jobs/search?keywords={quote(cargo)}&location={quote(localizacao)}"
        resposta = requests.get(url, headers=HEADERS, timeout=10)
        resposta.raise_for_status()
        sopa = BeautifulSoup(resposta.text, 'lxml')
        cartoes_vaga = sopa.select('div.base-search-card')
        for vaga in cartoes_vaga:
            titulo_tag = vaga.select_one('h3.base-search-card__title')
            titulo = titulo_tag.text.strip() if titulo_tag else "N/A"
            link_tag = vaga.select_one('a.base-card__full-link')
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else "N/A"
            empresa_tag = vaga.select_one('h4.base-search-card__subtitle')
            empresa = empresa_tag.text.strip() if empresa_tag else "Não informado"
            local_tag = vaga.select_one('span.job-search-card__location')
            local = local_tag.text.strip() if local_tag else "Não informado"
            resultado_formatado = f"*{titulo}*\n🏢 Empresa: {empresa}\n📍 Local: {local}\n🔗 Link: {link}"
            resultados.append(resultado_formatado)
    except Exception as e:
        print(f"[ERRO] Falha no scraper do LinkedIn: {e}")
    print(f"--- [INFO] Finalizada busca no LinkedIn. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))

def scrape_infojobs(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca no InfoJobs: '{cargo}' (Localização fixa: Rio de Janeiro) ---")
    resultados = []
    codigo_rio = '5208622'
    url_busca = f"https://www.infojobs.com.br/empregos.aspx?palabra={quote(cargo)}&poblacion={codigo_rio}"
    try:
        resposta = requests.get(url_busca, headers=HEADERS, timeout=10)
        resposta.raise_for_status()
        sopa = BeautifulSoup(resposta.text, 'lxml')
        cartoes_vaga = sopa.select('div.js_vacancyLoad[data-id]')
        for vaga in cartoes_vaga:
            titulo_tag = vaga.select_one('h2.h3')
            empresa_tag = vaga.select_one('div.text-body a')
            local_tag = vaga.select_one('div.small.text-medium')
            titulo = titulo_tag.text.strip() if titulo_tag else "N/A"
            link = vaga.get('data-href', "N/A")
            empresa = empresa_tag.text.strip() if empresa_tag else "Confidencial"
            local = local_tag.contents[0].strip() if local_tag and local_tag.contents else "N/A"
            if link.startswith('/'):
                link = "https://www.infojobs.com.br" + link
            resultado_formatado = f"*{titulo}*\n🏢 Empresa: {empresa}\n📍 Local: {local}\n🔗 Link: {link}"
            resultados.append(resultado_formatado)
    except Exception as e:
        print(f"[ERRO] Falha ao buscar vagas no InfoJobs: {e}")
    print(f"--- [INFO] Finalizada busca no InfoJobs. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))

def scrape_catho(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca na Catho: '{cargo}' em '{localizacao}' ---")
    # ... (lógica da Catho permanece a mesma) ...
    resultados = []
    try:
        cargo_formatado = cargo.lower().replace(' ', '-')
        url = f"https://www.catho.com.br/vagas/{cargo_formatado}/?pais_id=1"
        resposta = requests.get(url, headers=HEADERS, timeout=15)
        resposta.raise_for_status()
        sopa = BeautifulSoup(resposta.text, 'lxml')
        cartoes_vaga = sopa.find_all('article', class_='CardVaga')
        for vaga in cartoes_vaga:
            titulo_tag = vaga.select_one('h2.sc-iGPElx a')
            titulo = titulo_tag.text.strip() if titulo_tag else 'N/A'
            empresa_tag = vaga.select_one('p.sc-gsnTZi')
            empresa = empresa_tag.text.strip() if empresa_tag else 'Confidencial'
            link = titulo_tag['href'] if titulo_tag and titulo_tag.has_attr('href') else 'N/A'
            resultado_formatado = f"*{titulo}*\n🏢 Empresa: {empresa}\n🔗 Link: {link}"
            resultados.append(resultado_formatado)
    except Exception as e:
        print(f"[ERRO] Falha no scraper da Catho: {e}")
    print(f"--- [INFO] Finalizada busca na Catho. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))

# --- SCRAPER REESCRITO COM SELENIUMBASE PARA MÁXIMA ROBUSTEZ ---
def scrape_riovagas(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca no RioVagas com SeleniumBase: '{cargo}' ---")
    driver = None
    resultados = []
    try:
        # Etapa 1: Iniciar o driver "invisível"
        driver = iniciar_driver_sb()
        
        # Etapa 2: Navegar para a URL
        cargo_slug = cargo.lower().replace(' ', '-')
        url = f"https://riovagas.com.br/tag/{quote(cargo_slug)}/"
        driver.open(url) # Comando do SeleniumBase para abrir a URL

        # Etapa 3: Extrair os dados usando a combinação SeleniumBase + BeautifulSoup
        seletor_direto = 'div.vce-main-content h2.entry-title a'
        
        print(f"DEBUG: Procurando pelos links de vaga com o seletor: '{seletor_direto}'")
        # get_elements é um método do SeleniumBase que já espera os elementos aparecerem
        tags_de_link = driver.find_elements(seletor_direto)
        print(f"DEBUG: Encontrados {len(tags_de_link)} links de vaga.")

        for link_tag in tags_de_link[:15]:
            titulo = link_tag.text.strip()
            link = link_tag.get_attribute('href')
            
            resultado_formatado = f"*{titulo}*\n🔗 Link: {link}"
            resultados.append(resultado_formatado)
            
    except Exception as e:
        print(f"[ERRO] Falha no scraper do RioVagas com SeleniumBase: {e}")
    finally:
        # Garante que o navegador sempre feche, mesmo em caso de erro
        if driver:
            print("INFO: Finalizando driver do SeleniumBase.")
            driver.quit()
        
    print(f"--- [INFO] Finalizada busca no RioVagas. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))


# --- API FLASK ---
app = Flask(__name__)

@app.route('/buscar_vagas', methods=['POST'])
def handle_busca():
    # ... (A lógica da API não muda) ...
    dados = request.json
    if not all(k in dados for k in ['cargo', 'localizacao', 'sites']):
        return jsonify({"erro": "Dados incompletos"}), 400
    cargo = dados['cargo']
    localizacao = dados['localizacao']
    sites_selecionados = dados['sites']
    todos_resultados = []
    print(f"\n\n=======================================================")
    print(f"INFO: NOVA REQUISIÇÃO: '{cargo}' em '{localizacao}'")
    print(f"INFO: Sites selecionados: {sites_selecionados}")
    print(f"=======================================================")
    mapa_scrapers = {
        'Indeed': scrape_indeed,
        'LinkedIn': scrape_linkedin,
        'InfoJobs': scrape_infojobs,
        'Catho': scrape_catho,
        'RioVagas': scrape_riovagas,
    }
    for site_nome in sites_selecionados:
        if site_nome in mapa_scrapers:
            resultados_site = mapa_scrapers[site_nome](cargo, localizacao)
            if resultados_site:
                todos_resultados.extend(resultados_site)
        else:
            print(f"WARN: Nenhum scraper definido para o site: {site_nome}")
    if todos_resultados:
        todos_resultados = list(set(todos_resultados))
        print(f"=======================================================")
        print(f"INFO: BUSCA GERAL CONCLUÍDA. Total de {len(todos_resultados)} vagas únicas encontradas.")
        print(f"=======================================================\n\n")
        return jsonify(todos_resultados)
    else:
        print(f"=======================================================")
        print(f"INFO: BUSCA GERAL CONCLUÍDA. Nenhuma vaga encontrada.")
        print(f"=======================================================\n\n")
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)