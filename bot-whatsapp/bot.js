// bot.js (versão com Menu Dinâmico e Inteligente)
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const pino = require('pino');
const axios = require('axios');
const qrcode = require('qrcode-terminal');

// --- CONFIGURAÇÃO CENTRAL ---
// NOVO: Para adicionar/remover sites, mexa apenas aqui!
const SITES_CONFIG = [
    { name: 'LinkedIn', site: 'linkedin.com/jobs' },
    { name: 'Gupy', site: 'gupy.io' },
    { name: 'Glassdoor', site: 'glassdoor.com.br' },
    { name: 'VAGAS', site: 'vagas.com.br' },
    { name: 'Indeed', site: 'https://br.indeed.com' },
    { name: 'Infojobs', site: 'https://www.infojobs.com.br' },
    { name: 'RioVagas', site: 'https://riovagas.com.br' },
    { name: 'Catho', site: 'https://www.catho.com.br' }
];
// -------------------------

const API_PYTHON_URL = 'http://127.0.0.1:5000/buscar_vagas';
const PALAVRA_CHAVE = '!vagas';
const userState = {};

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    const sock = makeWASocket({
        logger: pino({ level: 'warn' }),
        auth: state,
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log('QR Code recebido! Escaneie com o seu WhatsApp:');
            qrcode.generate(qr, { small: true });
        }
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error instanceof Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('Conexão fechada, motivo: ', lastDisconnect.error, '. Reconectando: ', shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === 'open') {
            console.log('Conexão aberta e bot online!');
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];
        if (!msg.message || msg.key.fromMe) return;

        const userJid = msg.key.remoteJid;
        const messageText = (msg.message.conversation || msg.message.extendedTextMessage?.text || '').trim();
        const currentUserState = userState[userJid];

        if (!currentUserState && messageText.toLowerCase() === PALAVRA_CHAVE) {
            userState[userJid] = { step: 'escolher_sites' };

            // ALTERADO: O menu é gerado dinamicamente a partir da SITES_CONFIG
            let menuText = `Olá! 👋 Bem-vindo ao buscador de vagas.\nEscolha uma das opções abaixo digitando o número correspondente:\n\n`;
            
            SITES_CONFIG.forEach((item, index) => {
                menuText += `*${index + 1}.* ${item.name}\n`;
            });

            const todosOptionNumber = SITES_CONFIG.length + 1;
            menuText += `*${todosOptionNumber}.* TODOS os sites acima`;

            await sock.sendMessage(userJid, { text: menuText });
            return;
        }
        
        if (currentUserState) {
            switch (currentUserState.step) {
                case 'escolher_sites':
                    const choiceNumber = parseInt(messageText);
                    const totalOptions = SITES_CONFIG.length + 1;
                    let choiceName = '';
                    let sitesToSearch = [];

                    // ALTERADO: A lógica de escolha é dinâmica
                    if (!isNaN(choiceNumber) && choiceNumber > 0 && choiceNumber <= totalOptions) {
                        // Verifica se a opção "TODOS" foi escolhida
                        if (choiceNumber === totalOptions) {
                            choiceName = 'TODOS os sites';
                            // Pega todos os sites da configuração
                            sitesToSearch = SITES_CONFIG.map(item => item.site);
                        } else {
                            // Pega uma opção individual
                            const selectedConfig = SITES_CONFIG[choiceNumber - 1];
                            choiceName = selectedConfig.name;
                            sitesToSearch = [selectedConfig.site];
                        }
                        
                        currentUserState.sites = sitesToSearch;
                        currentUserState.step = 'pedir_cargo';
                        await sock.sendMessage(userJid, { text: `Ótimo! Você escolheu *${choiceName}*. \nAgora, digite o *cargo* que você deseja buscar.` });

                    } else {
                        // A mensagem de erro também é dinâmica
                        await sock.sendMessage(userJid, { text: `Opção inválida. Por favor, digite um número de *1* a *${totalOptions}*.` });
                    }
                    break;

                case 'pedir_cargo':
                    currentUserState.cargo = messageText;
                    currentUserState.step = 'pedir_local';
                    await sock.sendMessage(userJid, { text: 'Perfeito. E qual a *localização*? (Ex: São Paulo, Remoto)' });
                    break;

                case 'pedir_local':
                    currentUserState.localizacao = messageText;
                    await sock.sendMessage(userJid, { text: 'Aguarde um momento, estou buscando as melhores vagas para você... 👨‍💻' });
                    
                    try {
                        const response = await axios.post(API_PYTHON_URL, {
                            cargo: currentUserState.cargo,
                            localizacao: currentUserState.localizacao,
                            sites: currentUserState.sites,
                            quantidade: 20
                        });

                        const vagas = response.data;
                        if (vagas && vagas.length > 0) {
                            let respostaFinal = `Encontrei ${vagas.length} vaga(s) para *${currentUserState.cargo}*:\n\n`;
                            vagas.forEach((vaga, index) => {
                                respostaFinal += `${index + 1}. ${vaga}\n\n`;
                            });
                            await sock.sendMessage(userJid, { text: respostaFinal });
                        } else {
                            await sock.sendMessage(userJid, { text: 'Desculpe, não encontrei nenhuma vaga com esses critérios.' });
                        }
                    } catch (error) {
                        console.error("Erro ao chamar a API Python:", error);
                        await sock.sendMessage(userJid, { text: 'Ocorreu um erro interno ao buscar as vagas. Tente novamente mais tarde.' });
                    }
                    
                    delete userState[userJid];
                    break;
            }
        }
    });
}

connectToWhatsApp().catch(err => console.log("Erro inesperado: " + err));