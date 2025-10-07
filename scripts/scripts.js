// scripts.js - VERSÃO COMPLETA E REFATORADA

// Garante que o script só execute após o DOM estar completamente carregado
document.addEventListener("DOMContentLoaded", () => {
    // --- 1. SELEÇÃO DE ELEMENTOS DO DOM ---
    // Seleciona todos os formulários
    const transcribeForm = document.getElementById("transcribe-form");
    const audioForm = document.getElementById("audio-form");
    const videoForm = document.getElementById("video-form");
    const nuvemForm = document.getElementById("nuvem-form");

    // Seleciona todas as divs de resultado
    const resultTranscription = document.getElementById("result-transcription");
    const resultAudio = document.getElementById("result-audio");
    const resultVideo = document.getElementById("result-video");
    const nuvemResultContainer = document.getElementById("nuvem-result");

    // Elementos de feedback e controle
    const timerDiv = document.getElementById("timer");
    const copyButton = document.getElementById("copy-button"); // Este botão precisa existir no HTML

    // Variáveis para o timer
    let secondsElapsed = 0;
    let timerInterval;

    // --- 2. FUNÇÕES AUXILIARES ---

    /**
     * Inicia o timer para mostrar o tempo decorrido.
     */
    function startTimer() {
        clearInterval(timerInterval); // Garante que nenhum timer antigo esteja rodando
        secondsElapsed = 0;
        timerDiv.textContent = "⏳ Iniciando contagem...";
        timerDiv.style.display = 'block'; // Mostra o timer
        timerInterval = setInterval(() => {
            secondsElapsed++;
            timerDiv.textContent = `⏱️ Tempo decorrido: ${secondsElapsed} segundos`;
        }, 1000);
    }

    /**
     * Para o timer e o esconde.
     */
    function stopTimer() {
        clearInterval(timerInterval);
        timerDiv.textContent = "";
        timerDiv.style.display = 'none'; // Esconde o timer
    }

    /**
     * Limpa o conteúdo de todas as áreas de resultado e esconde o botão de copiar.
     */
    function clearAllResults() {
        resultTranscription.innerHTML = "";
        resultAudio.innerHTML = "";
        resultVideo.innerHTML = "";
        nuvemResultContainer.innerHTML = "";
        stopTimer(); // Também para e esconde o timer
        if (copyButton) {
            copyButton.style.display = "none";
        }
    }

    /**
     * Copia o texto fornecido para a área de transferência.
     * @param {string} textContent O texto a ser copiado.
     */
    function copiartexto(textContent) {
        navigator.clipboard.writeText(textContent)
            .then(() => {
                alert("Texto copiado para a área de transferência!");
            })
            .catch((err) => {
                console.error("Erro ao copiar texto: ", err);
                alert("Falha ao copiar texto. Por favor, copie manualmente.");
            });
    }

    // --- 3. EVENT LISTENERS PARA OS FORMULÁRIOS ---

    // Configura o botão de copiar (se ele existir no HTML)
    if (copyButton) {
        copyButton.onclick = () => copiartexto(resultTranscription.textContent);
    }

    /**
     * Listener para o formulário de Transcrição (transcribe-form).
     */
    transcribeForm.addEventListener("submit", async (e) => {
        e.preventDefault(); // Impede o envio padrão do formulário
        clearAllResults(); // Limpa resultados anteriores

        const localfile = document.getElementById("localfile").files[0];
        const url = document.getElementById("url-input").value;
        const model = document.getElementById("model").value;
        const language = document.getElementById("language").value;
        const chunk_length_choice = parseInt(document.getElementById("chunk_length").value);

        // Validação básica de entrada
        if (!localfile && !url) {
            resultTranscription.textContent = "❌ Por favor, forneça um arquivo de áudio ou uma URL do YouTube.";
            return;
        }

        startTimer();
        resultTranscription.textContent = "⏳ Conectando ao servidor para transcrição...";

        try {
            const socket = new WebSocket(`ws://${location.host}/ws/transcribe`);

            socket.onopen = () => {
                console.log("WebSocket de transcrição aberto.");
                // Envia os dados iniciais ou começa o upload do arquivo
                if (localfile) {
                    // Validações adicionais para arquivo local
                    const validTypes = ["audio/mpeg", "audio/wav", "audio/ogg"];
                    const MAX_SIZE = 1000 * 1024 * 1024; // 1GB
                    
                    if (!validTypes.includes(localfile.type)) {
                        socket.close(1000, "Formato não suportado"); // Código 1000 para fechamento normal
                        resultTranscription.textContent = "❌ Formato de arquivo não suportado. Use MP3, WAV ou OGG.";
                        stopTimer();
                        return;
                    }
                    if (localfile.size > MAX_SIZE) {
                        socket.close(1000, "Arquivo muito grande");
                        resultTranscription.textContent = "❌ Arquivo muito grande (máximo 1GB)";
                        stopTimer();
                        return;
                    }

                    socket.send(JSON.stringify({ model, language, chunk_length_choice, filename: localfile.name }));
                    resultTranscription.textContent = "⏳ Enviando arquivo para transcrição...";

                    const chunkSize = 2 * 1024 * 1024; // 2MB
                    let offset = 0;
                    
                    function readAndSendChunk() {
                        const reader = new FileReader();
                        const slice = localfile.slice(offset, offset + chunkSize);
                        reader.onload = (e) => {
                            if (e.target.error) {
                                resultTranscription.textContent = `❌ Erro ao ler arquivo: ${e.target.error}`;
                                socket.close();
                                return;
                            }
                            socket.send(e.target.result);
                            offset += chunkSize;
                            if (offset < localfile.size) {
                                readAndSendChunk();
                            } else {
                                socket.send("FILE_END"); // Sinaliza o fim do arquivo
                                resultTranscription.textContent = "✅ Arquivo enviado. Iniciando processamento...";
                            }
                        };
                        reader.readAsArrayBuffer(slice);
                    }
                    readAndSendChunk();

                } else if (url) {
                    socket.send(JSON.stringify({ url, model, language, chunk_length_choice }));
                }
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.error) {
                    resultTranscription.textContent = `❌ Erro: ${data.error}`;
                    stopTimer();
                } else {
                    // Atualiza a mensagem e a transcrição parcial
                    resultTranscription.textContent = `${data.message || ''}\n\n${data.transcription || ''}`;
                    
                    // Se a transcrição estiver completa (progresso 100)
                    if (data.progress === 100) {
                        stopTimer();
                        if (data.download_url) {
                            resultTranscription.innerHTML += `<br><br><a href="${data.download_url}" download class="download-link">📥 Baixar Transcrição</a>`;
                        }
                        if (copyButton) {
                            copyButton.style.display = "inline-block"; // Mostra o botão de copiar
                        }
                    }
                }
            };

            socket.onerror = (errorEvent) => {
                console.error("WebSocket de transcrição com erro:", errorEvent);
                resultTranscription.textContent = "❌ Erro de conexão com o servidor de transcrição.";
                stopTimer();
            };

            socket.onclose = (closeEvent) => {
                console.log(`WebSocket de transcrição fechado. Código: ${closeEvent.code}, Razão: ${closeEvent.reason}`);
                // stopTimer() já é chamado quando data.progress === 100 ou em caso de erro
                // Se a conexão fechar por outro motivo, o timer será parado aqui.
                if (closeEvent.code !== 1000 && closeEvent.code !== 1005) { // 1000=Normal, 1005=No Status Rcvd
                    resultTranscription.textContent = `❌ Conexão de transcrição fechada inesperadamente. Razão: ${closeEvent.reason || 'Desconhecida'}`;
                }
            };

        } catch (error) {
            console.error("Erro ao iniciar WebSocket de transcrição:", error);
            resultTranscription.textContent = `❌ Erro interno ao iniciar a transcrição: ${error.message}`;
            stopTimer();
        }
    });

    /**
     * Listener para os formulários de Áudio e Vídeo (audio-form, video-form).
     */
    [audioForm, videoForm].forEach((form) => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAllResults(); // Limpa resultados anteriores

            const isAudio = form.id.includes("audio");
            const inputId = isAudio ? "url-input-audio" : "url-input-video";
            const url = document.getElementById(inputId).value;
            const resultDiv = isAudio ? resultAudio : resultVideo;
            
            if (!url) {
                resultDiv.textContent = "❌ Por favor, insira uma URL do YouTube.";
                return;
            }

            resultDiv.textContent = `⏳ Gerando ${isAudio ? "áudio" : "vídeo"}...`;

            try {
                const socket = new WebSocket(`ws://${location.host}/ws/${isAudio ? "audio" : "video"}`);

                socket.onopen = () => {
                    console.log(`WebSocket de ${isAudio ? "áudio" : "vídeo"} aberto.`);
                    socket.send(JSON.stringify({ url }));
                };

                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.error) {
                        resultDiv.textContent = `❌ Erro:\n${data.error}`;
                    } else if (data.download_url) {
                        resultDiv.textContent = `${isAudio ? "Áudio" : "Vídeo"} gerado com sucesso`;
                        resultDiv.innerHTML += `<br><br><a href="${data.download_url}" download class="download-link">📥 Baixar</a>`;
                    }
                };

                socket.onerror = (errorEvent) => {
                    console.error(`WebSocket de ${isAudio ? "áudio" : "vídeo"} com erro:`, errorEvent);
                    resultDiv.textContent = `❌ Erro de conexão com o servidor para ${isAudio ? "áudio" : "vídeo"}.`;
                };
                
                socket.onclose = (closeEvent) => {
                    console.log(`WebSocket de ${isAudio ? "áudio" : "vídeo"} fechado. Código: ${closeEvent.code}, Razão: ${closeEvent.reason}`);
                    if (closeEvent.code !== 1000 && closeEvent.code !== 1005 && resultDiv.textContent.includes("⏳")) { 
                        resultDiv.textContent = `❌ Conexão de ${isAudio ? "áudio" : "vídeo"} fechada inesperadamente. Razão: ${closeEvent.reason || 'Desconhecida'}`;
                    }
                };

            } catch (error) {
                console.error(`Erro ao iniciar WebSocket de ${isAudio ? "áudio" : "vídeo"}:`, error);
                resultDiv.textContent = `❌ Erro interno ao processar ${isAudio ? "áudio" : "vídeo"}: ${error.message}`;
            }
        });
    });

    /**
     * Listener para o formulário da Nuvem de Palavras (nuvem-form).
     */
    nuvemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAllResults(); // Limpa resultados anteriores

        const fileInput = document.getElementById("file-input");
        const file = fileInput.files[0];

        if (!file) {
            nuvemResultContainer.textContent = "❌ Por favor, selecione um arquivo .txt para gerar a nuvem.";
            return;
        }

        nuvemResultContainer.textContent = "⏳ Gerando nuvem de palavras...";
        
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/upload/", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) { // Verifica se a requisição foi bem-sucedida (status 2xx)
                const errorData = await response.json().catch(() => ({ message: "Erro desconhecido" }));
                throw new Error(`Erro do servidor (${response.status}): ${errorData.message || response.statusText}`);
            }

            const data = await response.json();
            if (data.image_path) {
                nuvemResultContainer.innerHTML = `<img src="${data.image_path}" alt="Nuvem de Palavras" class="word-cloud-image">`;
            } else {
                nuvemResultContainer.textContent = `❌ Erro ao gerar nuvem: ${data.message || 'Caminho da imagem não retornado.'}`;
            }
        } catch (error) {
            console.error("Erro na geração da nuvem de palavras:", error);
            nuvemResultContainer.textContent = `❌ Erro de comunicação com o servidor para a nuvem de palavras: ${error.message}`;
        }
    });
}); // Fim do DOMContentLoaded