'use strict';
(() => {
  const start = document.querySelector('#iniciar-camera');
  const stop = document.querySelector('#parar-camera');
  const status = document.querySelector('#camera-status');
  const cameras = document.querySelector('#selecionar-camera');
  let scanner, running = false, busy = false, captured = false;
  async function stopCamera() {
    if (!running || busy) return;
    busy = true; stop.disabled = true;
    try {
      await scanner.stop(); running = false;
      status.textContent = captured ? 'Série capturada. Clique em Nova leitura para escanear outro ativo.' : 'Câmera desligada.';
      start.textContent = 'Nova leitura';
    } catch {
      status.textContent = 'Não foi possível desligar a câmera. Tente novamente ou feche esta página.';
    } finally {
      busy = false; start.disabled = running; stop.disabled = !running; cameras.disabled = running;
    }
  }
  start.addEventListener('click', async () => {
    if (running || busy) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      status.textContent = 'A câmera exige localhost ou HTTPS. Abra o endereço local do sistema.'; return;
    }
    busy = true; captured = false; start.disabled = true; cameras.disabled = true;
    status.textContent = 'Abrindo câmera. Permita o acesso quando solicitado.';
    try {
      if (typeof Html5Qrcode === 'undefined') throw new Error('ScannerLibraryMissing');
      const devices = await Html5Qrcode.getCameras();
      if (!devices.length) throw new Error('NotFoundError');
      const previous = cameras.value;
      cameras.replaceChildren();
      devices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.id; option.textContent = device.label || `Câmera ${index + 1}`;
        cameras.append(option);
      });
      cameras.value = devices.some(device => device.id === previous) ? previous : (devices.find(device => /back|rear|traseira|environment/i.test(device.label)) || devices[0]).id;
      scanner ||= new Html5Qrcode('reader', false);
      await scanner.start(cameras.value, {fps:10}, (text) => {
        if (!running || captured) return;
        const serial = text.trim();
        if (!serial || serial.length > 100 || /[\x00-\x1f]/.test(serial)) {
          status.textContent = 'Enquadre o código que contém apenas o número de série.'; return;
        }
        captured = true;
        document.querySelector('#serie-consulta').value = serial;
        void stopCamera();
        void consultarSerie(serial);
      }, () => {});
      running = true; stop.disabled = false;
      status.textContent = 'Câmera ativa. Enquadre o código de barras ou QR da série.';
    } catch (error) {
      const detail = `${error?.name || ''} ${error?.message || ''} ${String(error)}`;
      status.textContent = /ScannerLibraryMissing/.test(detail) ? 'A biblioteca da câmera não carregou. Reinicie o sistema pelo iniciar.bat e recarregue a página.'
        : /NotAllowed|Permission|denied/i.test(detail) ? 'Permissão de câmera negada. Clique no ícone de permissões ao lado do endereço e permita a câmera. Se necessário, abra este endereço no Chrome ou Edge.'
        : /NotFound|DevicesNotFound/i.test(detail) ? 'Nenhuma câmera encontrada. Conecte uma webcam e tente novamente.'
        : 'Não foi possível abrir a câmera. Confira se outra aplicação está usando a webcam.';
    } finally { busy = false; start.disabled = running; cameras.disabled = running; }
  });
  stop.addEventListener('click', () => { captured = false; void stopCamera(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) void stopCamera(); });
})();
