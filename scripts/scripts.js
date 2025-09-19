document
  .getElementById("transcribe-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();
    const localfile = document.getElementById("localfile").files[0];
    console.log("localfile", localfile);
    const url = document.getElementById("url-input").value;
    const model = document.getElementById("model").value;
    const language = document.getElementById("language").value;
    const resultDiv = document.getElementById("result");
    const timerDiv = document.getElementById("timer");
    const chunk_length_choice = parseInt(
      document.getElementById("chunk_length").value,
    );
    let secondsElapsed = 0;
    let timerInterval;
    const socket = new WebSocket(`ws://${location.host}/ws/transcribe`);

    function startTimer() {
      clearInterval(timerInterval);
      secondsElapsed = 0;
      timerDiv.textContent = "⏳ Iniciando contagem...";
      timerInterval = setInterval(() => {
        secondsElapsed++;
        timerDiv.textContent = `⏱️ Tempo decorrido: ${secondsElapsed} segundos`;
      }, 1000);
    }

    function stopTimer() {
      clearInterval(timerInterval);
    }

    resultDiv.textContent = "Iniciando transcrição...";
    startTimer();

    if (localfile) {
      // Validações adicionais
      const validTypes = ["audio/mpeg", "audio/wav", "audio/ogg"];
      if (!validTypes.includes(localfile.type)) {
        resultDiv.textContent =
          "❌ Formato não suportado. Use MP3, WAV ou OGG.";
        stopTimer();
        return;
      }

      const MAX_SIZE = 1000 * 1024 * 1024; // 1000MB
      if (localfile.size > MAX_SIZE) {
        resultDiv.textContent = "❌ Arquivo muito grande (máximo 100MB)";
        stopTimer();
        return;
      }

      try {
        socket.onopen = () => {
          socket.send(JSON.stringify({ model, language }));
          const chunkSize = 2 * 1024 * 1024; // 2MB
          let offset = 0;
          function readchunk() {
            const reader = new FileReader();
            const slice = localfile.slice(offset, offset + chunkSize);
            reader.onload = (e) => {
              if (e.target.error) {
                resultDiv.textContent = `❌ Erro ao ler arquivo: ${e.target.error}`;
                socket.close();
                stopTimer();
                return;
              }
              socket.send(e.target.result);
              offset += chunkSize;
              if (offset < localfile.size) {
                readchunk();
              } else {
                socket.send("FILE_END"); // Indica que o envio terminou
              }
            };
            reader.readAsArrayBuffer(slice);
          }
          readchunk();
        };
        socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.error) {
            resultDiv.textContent = `❌ Erro: ${data.error}`;
          } else {
            resultDiv.textContent = `${data.message}\n\n${data.transcription}`;
            if (data.download_url) {
              resultDiv.innerHTML += `<br><br><a href="${data.download_url}" download>📥 Baixar Transcrição</a>`;
            }
          }
        };
        socket.onerror = () => {
          resultDiv.textContent = "❌ Erro de conexão com o servidor.";
        };
        socket.onclose = () => {
          stopTimer();
        };
      } catch (error) {
        resultDiv.textContent = `❌ Erro: ${error.message}`;
        stopTimer();
      }
    } else if (url) {
      // Código existente para transcrição de URL
      socket.onopen = () => {
        socket.send(JSON.stringify({ url, model, language }));
      };
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) {
          resultDiv.textContent = `❌ Erro: ${data.error}`;
        } else {
          resultDiv.textContent = `${data.message}\n\n${data.transcription}`;
          if (data.download_url) {
            resultDiv.innerHTML += `<br><br><a href="${data.download_url}" download>📥 Baixar Transcrição</a>`;
          }
        }
      };
      socket.onerror = () => {
        resultDiv.textContent = "❌ Erro de conexão com o servidor.";
      };
      socket.onclose = () => {
        stopTimer();
      };
    } else {
      resultDiv.textContent =
        "❌ Por favor, forneça um arquivo de áudio ou uma URL do YouTube.";
      stopTimer();
    }

    function copiartexto(textContent) {
      navigator.clipboard
        .writeText(textContent)
        .then(() => {
          alert("Texto copiado para a área de transferência!");
        })
        .catch((err) => {
          console.error("Erro ao copiar texto: ", err);
        });
    }
  });
["audio-form", "video-form"].forEach((formId) => {
  document.getElementById(formId).addEventListener("submit", async (e) => {
    e.preventDefault();
    const inputId = formId.includes("audio")
      ? "url-input-audio"
      : "url-input-video";
    const url = document.getElementById(inputId).value;
    const resultDiv = document.getElementById("result");
    resultDiv.textContent = `⏳ Gerando ${
      formId.includes("audio") ? "áudio" : "vídeo"
    }...`;
    const socket = new WebSocket(
      `ws://${location.host}/ws/${formId.includes("audio") ? "audio" : "video"}`,
    );

    socket.onopen = () => {
      socket.send(JSON.stringify({ url }));
    };
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        resultDiv.textContent = `❌ Erro:\n${data.error}`;
      } else if (data.download_url) {
        resultDiv.textContent = `${
          formId.includes("audio") ? "Áudio" : "Vídeo"
        } gerado com sucesso`;
        resultDiv.innerHTML += `<br><br><a href="${data.download_url}" download>📥 Baixar</a>`;
      }
    };
    socket.onerror = () => {
      resultDiv.textContent = "❌ Erro de conexão com o servidor.";
    };
  });
});

document.getElementById("nuvem-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);
  const container = document.getElementById("nuvem-container");

  container.textContent = "⏳ Gerando nuvem...";
  const response = await fetch("/upload/", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  if (data.image_path) {
    container.innerHTML = `<img src="${data.image_path}" alt="Nuvem de Palavras">`;
  } else {
    container.textContent = "❌ Erro ao gerar nuvem.";
  }
});
