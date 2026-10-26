document.addEventListener('DOMContentLoaded', () => {
  const $ = (id) => document.getElementById(id);
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = (path) => `${wsProtocol}//${location.host}${path}`;
  const toast = $('toast');
  let timerInterval = null;
  let secondsElapsed = 0;

  const showToast = (message, type='') => {
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    clearTimeout(showToast.t);
    showToast.t = setTimeout(() => toast.className = 'toast', 2600);
  };

  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('[data-view]').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      $(btn.dataset.target).classList.add('active');
      window.scrollTo({top:0, behavior:'smooth'});
    });
  });

  const model = $('model'), language = $('language'), chunk = $('chunk_length');
  const syncMetrics = () => {
    $('metric-model').textContent = model.options[model.selectedIndex].text.split('·')[0].trim();
    $('metric-language').textContent = language.options[language.selectedIndex].text;
    $('metric-chunk').textContent = `${chunk.value}s`;
  };
  [model, language, chunk].forEach(el => el.addEventListener('change', syncMetrics)); syncMetrics();

  $('localfile').addEventListener('change', (e) => {
    const file = e.target.files[0];
    $('file-label').textContent = file ? `${file.name} · ${(file.size/1024/1024).toFixed(1)} MB` : 'MP3, WAV, OGG, MP4 ou MOV · até 1 GB';
  });

  const setProgress = (value=0, message='') => {
    $('transcription-progress').style.width = `${Math.max(0, Math.min(100, value))}%`;
    if (message) $('transcription-status').textContent = message;
  };
  const startTimer = () => {
    clearInterval(timerInterval); secondsElapsed = 0; $('timer').textContent = '00:00';
    timerInterval = setInterval(() => { secondsElapsed++; const m=String(Math.floor(secondsElapsed/60)).padStart(2,'0'); const s=String(secondsElapsed%60).padStart(2,'0'); $('timer').textContent=`${m}:${s}`; },1000);
  };
  const stopTimer = () => clearInterval(timerInterval);

  $('copy-button').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('result-transcription').textContent); showToast('Transcrição copiada.', 'success'); }
    catch { showToast('Não foi possível copiar automaticamente.', 'error'); }
  });

  $('transcribe-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const localfile = $('localfile').files[0];
    const url = $('url-input').value.trim();
    if (!localfile && !url) { showToast('Envie um arquivo ou informe uma URL.', 'error'); return; }

    const submit = e.currentTarget.querySelector('button[type=submit]');
    submit.disabled = true; $('copy-button').style.display='none'; $('result-transcription').textContent='Preparando transcrição…'; setProgress(2,'Conectando ao motor de transcrição…'); startTimer();
    const socket = new WebSocket(wsUrl('/ws/transcribe'));

    socket.onopen = () => {
      const payload = {model:model.value, language:language.value, chunk_length_choice:parseInt(chunk.value)};
      if (localfile) {
        const validTypes = ['audio/mpeg','audio/wav','audio/ogg','video/mp4','video/quicktime'];
        if (!validTypes.includes(localfile.type)) { showToast('Formato não suportado.', 'error'); socket.close(1000); submit.disabled=false; stopTimer(); return; }
        if (localfile.size > 1000*1024*1024) { showToast('Arquivo acima de 1 GB.', 'error'); socket.close(1000); submit.disabled=false; stopTimer(); return; }
        socket.send(JSON.stringify({...payload, filename:localfile.name}));
        const chunkSize=2*1024*1024; let offset=0;
        const sendNext=()=>{ const reader=new FileReader(); const slice=localfile.slice(offset,offset+chunkSize); reader.onload=(ev)=>{ socket.send(ev.target.result); offset+=chunkSize; const uploadPct=Math.min(18,Math.round((offset/localfile.size)*18)); setProgress(uploadPct,`Enviando arquivo… ${Math.min(100,Math.round(offset/localfile.size*100))}%`); offset<localfile.size ? sendNext() : (socket.send('FILE_END'),setProgress(20,'Upload concluído. Processando áudio…')); }; reader.readAsArrayBuffer(slice); }; sendNext();
      } else socket.send(JSON.stringify({...payload,url}));
    };

    socket.onmessage = (event) => {
      const data=JSON.parse(event.data);
      if (data.error) { $('result-transcription').textContent=`Erro\n\n${data.error}`; setProgress(0,'A transcrição falhou.'); showToast('Erro durante a transcrição.', 'error'); stopTimer(); submit.disabled=false; return; }
      const pct = typeof data.progress==='number' ? data.progress : 20;
      setProgress(pct, data.message || 'Processando…');
      if (data.transcription) $('result-transcription').textContent=data.transcription;
      if (data.progress===100) { stopTimer(); submit.disabled=false; $('copy-button').style.display='inline-flex'; if(data.download_url){ const a=document.createElement('a'); a.href=data.download_url; a.download=''; a.className='download-link'; a.textContent='Baixar transcrição'; $('result-transcription').append('\n\n'); $('result-transcription').after(a); } showToast('Transcrição concluída.', 'success'); }
    };
    socket.onerror=()=>{ setProgress(0,'Erro de conexão com o servidor.'); showToast('Falha na conexão WebSocket.', 'error'); stopTimer(); submit.disabled=false; };
    socket.onclose=()=>{ if(submit.disabled){ submit.disabled=false; stopTimer(); } };
  });

  const setupMediaForm=(formId,inputId,resultId,path,label)=>{
    $(formId).addEventListener('submit',(e)=>{e.preventDefault(); const url=$(inputId).value.trim(); if(!url){showToast('Informe uma URL.','error');return;} const button=e.currentTarget.querySelector('button[type=submit]'); const result=$(resultId); button.disabled=true; result.textContent=`Preparando ${label}…`; const socket=new WebSocket(wsUrl(path)); socket.onopen=()=>socket.send(JSON.stringify({url})); socket.onmessage=(ev)=>{const data=JSON.parse(ev.data); if(data.error){result.textContent=`Erro: ${data.error}`;button.disabled=false;showToast(`Falha ao gerar ${label}.`,'error');} else if(data.download_url){result.innerHTML=`<strong>${label[0].toUpperCase()+label.slice(1)} pronto.</strong><br><a class="download-link" href="${data.download_url}" download>Baixar arquivo</a>`;button.disabled=false;showToast(`${label[0].toUpperCase()+label.slice(1)} gerado.`,'success');}}; socket.onerror=()=>{result.textContent='Erro de conexão com o servidor.';button.disabled=false;}; socket.onclose=()=>button.disabled=false; });
  };
  setupMediaForm('audio-form','url-input-audio','result-audio','/ws/audio','áudio');
  setupMediaForm('video-form','url-input-video','result-video','/ws/video','vídeo');

  $('nuvem-form').addEventListener('submit', async (e)=>{
    e.preventDefault(); const file=$('file-input').files[0]; if(!file){showToast('Selecione um arquivo .txt.','error');return;} const button=e.currentTarget.querySelector('button[type=submit]'); const result=$('nuvem-result'); button.disabled=true; result.textContent='Gerando nuvem…'; const fd=new FormData(); fd.append('file',file);
    try{const response=await fetch('/upload/',{method:'POST',body:fd}); if(!response.ok) throw new Error(`HTTP ${response.status}`); const data=await response.json(); if(!data.image_path) throw new Error(data.message||'Imagem não retornada'); result.innerHTML=`<img src="${data.image_path}" alt="Nuvem de palavras" />`;showToast('Nuvem gerada.','success');}catch(err){result.textContent=`Erro: ${err.message}`;showToast('Falha ao gerar a nuvem.','error');}finally{button.disabled=false;}
  });
});
