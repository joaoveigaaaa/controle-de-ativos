'use strict';
(() => {
  const button = document.querySelector('#ler-texto');
  const status = document.querySelector('#texto-status');
  const choices = document.querySelector('#series-reconhecidas');
  let busy = false;
  button.addEventListener('click', async () => {
    if (busy) return;
    const video = document.querySelector('#reader video');
    if (!video || !video.videoWidth || video.paused || !video.srcObject) {
      status.textContent = 'Primeiro clique em Iniciar câmera e aguarde a imagem aparecer.'; return;
    }
    busy = true; button.disabled = true; choices.replaceChildren();
    status.textContent = 'Lendo letras e números. Na primeira leitura, o reconhecimento pode levar alguns segundos...';
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), 60000);
    try {
      const canvas = document.createElement('canvas');
      const scale = Math.min(1, 2000 / Math.max(video.videoWidth, video.videoHeight));
      canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .95));
      if (!blob) throw new Error('Não foi possível capturar a imagem. Abra a câmera novamente.');
      const form = new FormData(); form.append('quadro', blob, 'camera.jpg');
      const response = await fetch('/api/scan-text', {method:'POST', body:form, signal:abort.signal});
      if (response.status === 404 || response.status === 405) throw new Error('Reinicie o sistema com python app.py ou iniciar.bat e abra o endereço exibido no terminal.');
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Falha na leitura da câmera.');
      if (!data.candidatos.length) {
        status.textContent = 'Nenhuma série reconhecida. Aproxime a câmera, melhore a iluminação e tente novamente.'; return;
      }
      status.textContent = 'Confira a série na etiqueta e clique no resultado correto para consultar. Você também pode corrigir o texto no campo Número de série.';
      for (const serial of data.candidatos) {
        const option = document.createElement('button'); option.type = 'button'; option.className = 'button'; option.textContent = serial;
        option.addEventListener('click', () => {
          document.querySelector('#serie-consulta').value = serial;
          document.querySelector('#parar-camera').click();
          void consultarSerie(serial);
        });
        choices.append(option);
      }
      const details = document.createElement('details'); const summary = document.createElement('summary'); const text = document.createElement('pre');
      summary.textContent = 'Texto reconhecido'; text.textContent = data.textos.join('\n');
      details.append(summary, text); choices.append(details);
    } catch(error) {
      status.textContent = error.name === 'AbortError' ? 'A leitura demorou demais. Tente novamente com a câmera mais próxima.' : error.message;
    } finally { clearTimeout(timeout); busy = false; button.disabled = false; }
  });
})();
