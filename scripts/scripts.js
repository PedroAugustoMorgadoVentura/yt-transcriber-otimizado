 document.getElementById("transcribe-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const localfile = document.getElementById("localfile").files[0];
      const url = document.getElementById("url-input").value;
      const model = document.getElementById("model").value;
      const language = document.getElementById("language").value;
      const resultDiv = document.getElementById("result");
      const timerDiv = document.getElementById("timer");
      let secondsElapsed = 0;
      let timerInterval;

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
        const socket = new WebSocket(`ws://${location.host}/ws/local-transcribe`);
        socket.onopen = () => {
          socket.send(JSON.stringify({ model, language }));
          const reader = new FileReader();
          reader.onload = () => {
            socket.send(reader.result);
          };
          reader.readAsArrayBuffer(localfile);
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
        const socket = new WebSocket(`ws://${location.host}/ws/transcribe`);
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
      }
    });

    ["audio-form", "video-form"].forEach((formId) => {
      document.getElementById(formId).addEventListener("submit", async (e) => {
        e.preventDefault();
        const inputId = formId.includes("audio") ? "url-input-audio" : "url-input-video";
        const url = document.getElementById(inputId).value;
        const resultDiv = document.getElementById("result");
        resultDiv.textContent = `⏳ Gerando ${formId.includes("audio") ? "áudio" : "vídeo"}...`;
        const socket = new WebSocket(`ws://${location.host}/ws/${formId.includes("audio") ? "audio" : "video"}`);

        socket.onopen = () => {
          socket.send(JSON.stringify({ url }));
        };
        socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.error) {
            resultDiv.textContent = `❌ Erro:\n${data.error}`;
          } else if (data.download_url) {
            resultDiv.textContent = `${formId.includes("audio") ? "Áudio" : "Vídeo"} gerado com sucesso`;
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