# app.py (Versão com o scraper funcional do RioVagas RESTAURADO)

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from urllib.parse import quote
import time
import unicodedata

# Imports do SeleniumBase, usados pela Catho e RioVagas
from seleniumbase import SB
from selenium.common.exceptions import TimeoutException

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

ESTADOS_BRASIL = {
    'acre': 'ac', 'alagoas': 'al', 'amapa': 'ap', 'amazonas': 'am', 'bahia': 'ba', 'ceara': 'ce',
    'distrito federal': 'df', 'espirito santo': 'es', 'goias': 'go', 'maranhao': 'ma',
    'mato grosso': 'mt', 'mato grosso do sul': 'ms', 'minas gerais': 'mg', 'para': 'pa',
    'paraiba': 'pb', 'parana': 'pr', 'pernambuco': 'pe', 'piaui': 'pi', 'rio de janeiro': 'rj',
    'rio grande do norte': 'rn', 'rio grande do sul': 'rs', 'rondonia': 'ro', 'roraima': 'rr',
    'santa catarina': 'sc', 'sao paulo': 'sp', 'sergipe': 'se', 'tocantins': 'to',
    'rj': 'rj', 'sp': 'sp', 'mg': 'mg' 
}

def get_sigla_estado(local_str):
    local_normalizado = ''.join(c for c in unicodedata.normalize('NFD', local_str.lower()) if unicodedata.category(c) != 'Mn')
    for nome, sigla in ESTADOS_BRASIL.items():
        if nome in local_normalizado:
            return sigla
    for sigla in ESTADOS_BRASIL.values():
        if f" {sigla} " in f" {local_normalizado} " or local_normalizado == sigla:
             return sigla
    return None

def iniciar_driver_sb():
    print("INFO: Iniciando driver com SeleniumBase (modo UC)...")
    driver = SB(uc=True, headless=True, agent=HEADERS["User-Agent"])
    return driver

# --- FUNÇÕES DE SCRAPING ---

def scrape_indeed(cargo, localizacao):
    print(f"\n--- [AVISO] O scraper para o Indeed está desativado. ---")
    return []

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
    print(f"\n--- [INFO] Iniciando busca na Catho com SeleniumBase: '{cargo}' em '{localizacao}' ---")
    resultados = []
    
    sigla_estado = get_sigla_estado(localizacao)
    cargo_slug = cargo.lower().replace(' ', '-')

    if not sigla_estado:
        print(f"[AVISO] Não foi possível determinar a sigla do estado para '{localizacao}'. Buscando na Catho sem filtro de local.")
        url = f"https://www.catho.com.br/vagas/{quote(cargo_slug)}/"
    else:
        print(f"DEBUG: Sigla do estado encontrada: '{sigla_estado}'")
        url = f"https://www.catho.com.br/vagas/{quote(cargo_slug)}/{sigla_estado}/"

    try:
        with SB(uc=True, headless=True, agent=HEADERS["User-Agent"]) as sb:
            print(f"DEBUG: Acessando URL: {url}")
            sb.open(url)

            # Espera pela lista de resultados (o <ul>) carregar
            seletor_lista = "ul.search-result-custom_jobList__lVIvI"
            print(f"DEBUG: Esperando pela lista de vagas: '{seletor_lista}'")
            sb.wait_for_element(seletor_lista, timeout=15)
            print("DEBUG: Página de resultados da Catho carregada.")

            html_final = sb.get_page_source()
            sopa = BeautifulSoup(html_final, 'lxml')
            
            # Usa o seletor do card principal que você encontrou
            cartoes_vaga = sopa.select("li.search-result-custom_jobItem__OGz3a")
            print(f"DEBUG: Encontrados {len(cartoes_vaga)} cards de vaga na página.")

            for vaga in cartoes_vaga[:15]:
                # Usa os seletores precisos que você identificou
                titulo_tag = vaga.select_one('h2.Title-module__title___3S2cv a')
                empresa_tag = vaga.select_one('p.sc-ejfMa-d.fJfzcm')
                salario_tag = vaga.select_one('div.custom-styled_salaryText__oSvPo') # Corrigido para div
                
                # Tratamento robusto para evitar erros se um elemento não for encontrado
                titulo = titulo_tag.text.strip() if titulo_tag else 'N/A'
                link = titulo_tag['href'] if titulo_tag and titulo_tag.has_attr('href') else 'N/A'
                empresa = empresa_tag.text.strip() if empresa_tag else 'Confidencial'
                salario = salario_tag.text.strip() if salario_tag else 'Não informado'
                
                resultado_formatado = f"*{titulo}*\n🏢 Empresa: {empresa}\n💰 Salário: {salario}\n🔗 Link: {link}"
                resultados.append(resultado_formatado)

    except TimeoutException:
        print(f"[ERRO] O tempo de espera para encontrar os resultados na Catho esgotou. A busca pode não ter retornado vagas para os critérios.")
    except Exception as e:
        print(f"[ERRO] Falha no scraper da Catho com SeleniumBase: {e}")

    print(f"--- [INFO] Finalizada busca na Catho. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))

# --- FUNÇÃO DO RIOVAGAS RESTAURADA PARA A VERSÃO FUNCIONAL COM SELENIUMBASE ---
def scrape_riovagas(cargo, localizacao):
    print(f"\n--- [INFO] Iniciando busca no RioVagas com SeleniumBase: '{cargo}' ---")
    resultados = []
    try:
        with SB(uc=True, headless=True, agent=HEADERS["User-Agent"]) as sb:
            cargo_slug = cargo.lower().replace(' ', '-')
            url = f"https://riovagas.com.br/tag/{quote(cargo_slug)}/"
            print(f"DEBUG: Acessando URL: {url}")
            sb.open(url)

            seletor_direto = 'div.vce-main-content h2.entry-title a'
            print(f"DEBUG: Procurando pelos links de vaga com o seletor: '{seletor_direto}'")
            
            tags_de_link = sb.find_elements(seletor_direto)
            print(f"DEBUG: Encontrados {len(tags_de_link)} links de vaga.")

            for link_tag in tags_de_link[:15]:
                titulo = link_tag.text.strip()
                link = link_tag.get_attribute('href')
                
                try:
                    card_pai = link_tag.find_element("xpath", "./ancestor::article")
                    data_tag = card_pai.find_element("css selector", 'span.meta-item.date time')
                    data_publicacao = data_tag.text.strip()
                except Exception:
                    data_publicacao = "N/A"
                
                resultado_formatado = f"*{titulo}*\n📅 Publicado em: {data_publicacao}\n🔗 Link: {link}"
                resultados.append(resultado_formatado)
                
    except Exception as e:
        print(f"[ERRO] Falha no scraper do RioVagas com SeleniumBase: {e}")
        
    print(f"--- [INFO] Finalizada busca no RioVagas. {len(resultados)} vagas processadas. ---")
    return list(set(resultados))


# --- API FLASK ---
app = Flask(__name__)

@app.route('/buscar_vagas', methods=['POST'])
def handle_busca():
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