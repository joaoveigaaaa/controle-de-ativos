'use strict';
const form = document.querySelector('#form-consulta');
const input = document.querySelector('#serie');
const status = document.querySelector('#mensagem');
const sheet = document.querySelector('#ficha');
const state = document.querySelector('#situacao');
const panel = document.querySelector('#painel-ficha');
const cameraStatus = document.querySelector('#camera-status');
const startButton = document.querySelector('#iniciar-camera');
const stopButton = document.querySelector('#parar-camera');
let scanner;
let running = false;
let starting = false;
let stopping = false;
let accepted = false;
const labels = {ativo:'Ativo', numero_serie:'Número de série', serie:'Série', serial:'Número de série', categoria:'Categoria', status:'Status', matricula:'Matrícula', data_garantia:'Data de garantia', departamento:'Departamento', responsavel:'Responsável', sede:'Sede', empresa:'Sede', id:'ID'};
let version = 0;
let controller;
function message(text, kind = '') { status.textContent = text; status.className = `message ${kind}`; }
function empty(text) { const el = document.createElement('div'); el.className = 'empty'; el.textContent = text; sheet.replaceChildren(el); }
function show(record) {
  const list = document.createElement('dl');
  for (const [key, value] of Object.entries(record)) {
    const group = document.createElement('div');
    const label = document.createElement('dt');
    const content = document.createElement('dd');
    label.textContent = labels[key] || key.replaceAll('_', ' ');
    content.textContent = value == null || value === '' ? '—' : String(value);
    group.append(label, content); list.append(group);
  }
  sheet.replaceChildren(list);
}
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const serial = input.value.trim();
  if (!serial) { input.focus(); return; }
  const current = ++version;
  controller?.abort();
  const activeController = new AbortController();
  controller = activeController;
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; activeController.abort(); }, 15000);
  panel.setAttribute('aria-busy', 'true');
  state.textContent = 'Consultando';
  empty('Buscando os dados do ativo…');
  message(`Consultando série ${serial}…`);
  if (running) { accepted = true; void stopCamera(); }
  try {
    const response = await fetch(`/api/consulta?serie=${encodeURIComponent(serial)}`, {signal:activeController.signal, cache:'no-store'});
    const data = await response.json();
    if (current !== version) return;
    if (!response.ok) throw new Error(data.erro || 'Não foi possível consultar o ativo.');
    if (!data.registro) {
      state.textContent = 'Não encontrado'; empty('Nenhum ativo encontrado para esta série.');
      message(`Série ${serial} não encontrada. Confira o código e tente novamente.`);
    } else {
      show(data.registro); state.textContent = 'Ativo encontrado';
      message(`Série ${serial} encontrada. Pronto para a próxima leitura.`, 'success');
    }
  } catch (error) {
    if (current !== version) return;
    state.textContent = 'Consulta indisponível'; empty('A consulta não foi concluída.');
    message(timedOut ? 'A consulta demorou demais. Confira a conexão com a empresa e tente novamente.' : error instanceof TypeError ? 'Sem conexão com o sistema. Confira se o servidor está em execução.' : error.message, 'error');
  } finally {
    clearTimeout(timeout);
    if (current === version) panel.setAttribute('aria-busy', 'false');
  }
});
document.querySelector('#nova-leitura').addEventListener('click', async () => {
  version++; controller?.abort(); input.value = ''; input.focus();
  panel.setAttribute('aria-busy', 'false'); state.textContent = 'Aguardando leitura';
  empty('Os dados do equipamento aparecerão aqui.'); message('Pronto para escanear.');
  await startCamera();
});
async function stopCamera() {
  if (!running || stopping) return;
  stopping = true; stopButton.disabled = true;
  try {
    await scanner.stop(); running = false;
    cameraStatus.textContent = accepted ? 'Código capturado. Use Nova leitura para escanear outro ativo.' : 'Câmera desligada.';
  } catch {
    cameraStatus.textContent = 'Não foi possível parar a câmera. Tente novamente ou feche esta página.';
  } finally {
    stopping = false; startButton.disabled = running; stopButton.disabled = !running;
  }
}
async function startCamera() {
  if (running || starting || stopping) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraStatus.textContent = 'Câmera indisponível. Abra pelo endereço localhost neste computador ou por HTTPS.';
    return;
  }
  starting = true; accepted = false; startButton.disabled = true;
  cameraStatus.textContent = 'Abrindo câmera. Autorize o acesso quando o navegador solicitar.';
  try {
    scanner ||= new Html5Qrcode('reader', false);
    await scanner.start({facingMode:'environment'}, {fps:10, disableFlip:false}, (text) => {
      if (accepted || !running) return;
      const serial = text.trim();
      if (!serial || serial.length > 255 || /[\x00-\x1f]/.test(serial)) {
        cameraStatus.textContent = 'Este código não contém uma série válida. Enquadre o código do número de série.';
        return;
      }
      accepted = true;
      input.value = serial;
      form.requestSubmit();
    }, () => {});
    running = true; stopButton.disabled = false;
    cameraStatus.textContent = 'Câmera ativa. Enquadre o código de barras ou QR da série.';
  } catch (error) {
    const detail = String(error?.name || error);
    cameraStatus.textContent = /NotAllowed|Permission|denied/i.test(detail)
      ? 'Acesso à câmera não permitido. Autorize nas configurações do navegador e tente novamente.'
      : /NotFound|DevicesNotFound/i.test(detail)
      ? 'Nenhuma câmera encontrada. Conecte uma webcam e tente novamente.'
      : 'Não foi possível abrir a câmera. Verifique se outra aplicação está usando a webcam.';
  } finally {
    starting = false; startButton.disabled = running;
  }
}
startButton.addEventListener('click', startCamera);
stopButton.addEventListener('click', () => { accepted = false; void stopCamera(); });
document.addEventListener('visibilitychange', () => { if (document.hidden && running) void stopCamera(); });
