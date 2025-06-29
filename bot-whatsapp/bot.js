// bot.js (versão com fluxo inteligente para RioVagas)
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const pino = require('pino');
const axios = require('axios');
const qrcode = require('qrcode-terminal');

const SITES_CONFIG = [
    { name: 'Indeed', id: 'Indeed' },
    { name: 'LinkedIn', id: 'LinkedIn' },
    { name: 'InfoJobs', id: 'InfoJobs' },
    { name: 'Catho', id: 'Catho' },
    { name: 'RioVagas', id: 'RioVagas' }
];

const API_PYTHON_URL = 'http://127.0.0.1:5000/buscar_vagas';
const PALAVRA_CHAVE = '!vagas';
const userState = {};

// NOVO: Função refatorada para executar a busca e enviar a resposta
async function executarBusca(sock, userJid, currentUserState) {
    await sock.sendMessage(userJid, { text: 'Aguarde um momento, estou consultando as fontes de vagas... 👨‍💻' });
    
    try {
        const response = await axios.post(API_PYTHON_URL, {
            cargo: currentUserState.cargo,
            localizacao: currentUserState.localizacao,
            sites: currentUserState.sites
        });

        const vagas = response.data;
        if (vagas && vagas.length > 0) {
            let respostaFinal = `Encontrei ${vagas.length} vaga(s) para *${currentUserState.cargo}*:\n\n`;
            vagas.forEach((vaga) => {
                respostaFinal += `${vaga}\n\n---\n\n`; 
            });
            // Remove as últimas 5 quebras de linha e traços para um final limpo
            respostaFinal = respostaFinal.slice(0, -5);
            await sock.sendMessage(userJid, { text: respostaFinal });
        } else {
            await sock.sendMessage(userJid, { text: 'Desculpe, não encontrei nenhuma vaga com esses critérios nos sites selecionados.' });
        }
    } catch (error) {
        console.error("Erro ao chamar a API Python:", error.response ? error.response.data : error.message);
        await sock.sendMessage(userJid, { text: 'Ocorreu um erro interno ao buscar as vagas. Tente novamente mais tarde.' });
    } finally {
        // Limpa o estado do usuário após a busca
        delete userState[userJid];
    }
}


async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    const sock = makeWASocket({ logger: pino({ level: 'warn' }), auth: state });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log('QR Code recebido! Escaneie com o seu WhatsApp:');
            qrcode.generate(qr, { small: true });
        }
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error instanceof Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
            if (shouldReconnect) connectToWhatsApp();
        } else if (connection === 'open') {
            console.log('Conexão aberta e bot online! JID:', sock.user.id);
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];
        if (!msg.message || msg.key.fromMe) return;

        const userJid = msg.key.remoteJid;
        const messageText = (msg.message.conversation || msg.message.extendedTextMessage?.text || '').trim();
        const currentUserState = userState[userJid];

        const isGroup = userJid.endsWith('@g.us');
        const commandReceived = messageText.toLowerCase().includes(PALAVRA_CHAVE);
        const mentionedJid = msg.message.extendedTextMessage?.contextInfo?.mentionedJid || [];
        const botId = sock.user.id.split(':')[0] + '@s.whatsapp.net';
        const isBotMentioned = mentionedJid.includes(botId);
        
        let shouldStartFlow = false;
        if (isGroup) {
            if (commandReceived && isBotMentioned) shouldStartFlow = true;
        } else {
            if (commandReceived) shouldStartFlow = true;
        }

        if (!currentUserState && shouldStartFlow) {
            userState[userJid] = { step: 'escolher_sites' };
            let menuText = `Olá! 👋 Fui chamado para buscar vagas.\nEscolha um ou mais sites (separados por vírgula) ou 'todos':\n\n`;
            SITES_CONFIG.forEach((item, index) => {
                menuText += `*${index + 1}.* ${item.name}\n`;
            });
            menuText += `*${SITES_CONFIG.length + 1}.* TODOS os sites acima`;
            await sock.sendMessage(userJid, { text: menuText });
            return;
        }
        
        if (currentUserState) {
            if (messageText.toLowerCase() === '!cancelar') {
                delete userState[userJid];
                await sock.sendMessage(userJid, { text: 'Sua busca foi cancelada.' });
                return;
            }

            switch (currentUserState.step) {
                case 'escolher_sites':
                    const choices = messageText.toLowerCase().split(',').map(c => c.trim());
                    let sitesToSearch = [];

                    if (choices.includes('todos') || choices.includes((SITES_CONFIG.length + 1).toString())) {
                        sitesToSearch = SITES_CONFIG.map(s => s.id);
                    } else {
                        choices.forEach(choice => {
                            const choiceIndex = parseInt(choice) - 1;
                            if (!isNaN(choiceIndex) && choiceIndex >= 0 && choiceIndex < SITES_CONFIG.length) {
                                sitesToSearch.push(SITES_CONFIG[choiceIndex].id);
                            }
                        });
                    }

                    if (sitesToSearch.length > 0) {
                        currentUserState.sites = [...new Set(sitesToSearch)];
                        
                        // --- LÓGICA CONDICIONAL INTELIGENTE ---
                        const isOnlyRioVagas = currentUserState.sites.length === 1 && currentUserState.sites[0] === 'RioVagas';

                        if (isOnlyRioVagas) {
                            // Se for SÓ RioVagas, pula a pergunta de local
                            currentUserState.step = 'pedir_cargo_para_riovagas'; // Um passo especial
                            await sock.sendMessage(userJid, { text: `Ótimo! Buscarei no RioVagas. Qual o *cargo* que você deseja?` });
                        } else {
                            // Para qualquer outra combinação, segue o fluxo normal
                            currentUserState.step = 'pedir_cargo';
                            await sock.sendMessage(userJid, { text: `Ótimo! Buscarei em: *${currentUserState.sites.join(', ')}*. \nAgora, digite o *cargo* que você deseja.` });
                        }
                    } else {
                        await sock.sendMessage(userJid, { text: `Opção inválida. Por favor, digite os números dos sites (ex: 1, 3) ou 'todos'.` });
                    }
                    break;
                
                // Fluxo normal que pede localização
                case 'pedir_cargo':
                    currentUserState.cargo = messageText;
                    currentUserState.step = 'pedir_local';
                    await sock.sendMessage(userJid, { text: 'Perfeito. E qual a *localização*? (Ex: São Paulo, Brasil)' });
                    break;
                
                // NOVO: Fluxo especial para RioVagas que não pede localização
                case 'pedir_cargo_para_riovagas':
                    currentUserState.cargo = messageText;
                    // Define uma localização padrão, pois o backend espera o campo, mesmo que o ignore
                    currentUserState.localizacao = "Rio de Janeiro";
                    // Pula direto para a execução da busca
                    await executarBusca(sock, userJid, currentUserState);
                    break;

                case 'pedir_local':
                    currentUserState.localizacao = messageText;
                    // Chama a função de busca
                    await executarBusca(sock, userJid, currentUserState);
                    break;
            }
        }
    });
}

connectToWhatsApp().catch(err => console.log("Erro inesperado: " + err));