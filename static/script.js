const thread = document.getElementById('thread');
const composer = document.getElementById('composer');
const input = document.getElementById('messageInput');
const badge = document.getElementById('badge');
const badgeRole = document.getElementById('badgeRole');
const badgeId = document.getElementById('badgeId');
const sysModeText = document.getElementById('sysModeText');
const btnTutor = document.getElementById('btnTutor');
const btnInterviewer = document.getElementById('btnInterviewer');

let mode = 'tutor';

const MODE_META = {
  tutor: {
    role: 'TUTOR MODE',
    id: 'ID NO. 001-T',
    placeholder: "Type a question for your tutor…",
    sysText: "Tutor mode engaged — ask anything, I'll meet you where you are.",
    label: 'TUTOR',
  },
  interviewer: {
    role: 'INTERVIEWER MODE',
    id: 'ID NO. 001-I',
    placeholder: "Answer like you're in the room…",
    sysText: "Interviewer mode engaged — let's see what holds up under pressure.",
    label: 'INTERVIEWER',
  },
};

function setMode(newMode) {
  mode = newMode;
  const meta = MODE_META[mode];

  badge.dataset.mode = mode;
  badgeRole.textContent = meta.role;
  badgeId.textContent = meta.id;
  input.placeholder = meta.placeholder;
  document.body.dataset.mode = mode;

  btnTutor.classList.toggle('active', mode === 'tutor');
  btnInterviewer.classList.toggle('active', mode === 'interviewer');

  appendSystemLine(meta.sysText);
}

function appendSystemLine(text) {
  const line = document.createElement('div');
  line.className = 'sys-line';
  line.innerHTML = `<span class="sys-tag">MODE</span><span class="sys-text"></span>`;
  line.querySelector('.sys-text').textContent = text;
  thread.appendChild(line);
  scrollToBottom();
}

function appendUserMessage(text) {
  const el = document.createElement('div');
  el.className = 'msg user';
  el.textContent = text;
  thread.appendChild(el);
  scrollToBottom();
}

function appendAiMessage(text, memory, currentMode) {
  const el = document.createElement('div');
  el.className = `msg ai ${currentMode}`;
  el.dataset.role = MODE_META[currentMode].label;
  el.innerHTML = `<span class="reply-text"></span><span class="mem-note"></span>`;
  el.querySelector('.reply-text').textContent = text;
  el.querySelector('.mem-note').textContent = `memory used: ${memory}`;
  thread.appendChild(el);
  scrollToBottom();
}

function showThinking() {
  const el = document.createElement('div');
  el.className = 'thinking';
  el.id = 'thinkingIndicator';
  el.innerHTML = '<span></span><span></span><span></span>';
  thread.appendChild(el);
  scrollToBottom();
}

function hideThinking() {
  const el = document.getElementById('thinkingIndicator');
  if (el) el.remove();
}

function scrollToBottom() {
  thread.scrollTop = thread.scrollHeight;
}

async function sendMessage(text) {
  appendUserMessage(text);
  showThinking();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, mode }),
    });
    const data = await res.json();
    hideThinking();

    if (data.error) {
      appendSystemLine(`Error: ${data.error}`);
      return;
    }
    appendAiMessage(data.reply, data.memory, data.mode);
  } catch (err) {
    hideThinking();
    appendSystemLine('Connection error — is the Flask server running?');
  }
}

composer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  sendMessage(text);
});

btnTutor.addEventListener('click', () => setMode('tutor'));
btnInterviewer.addEventListener('click', () => setMode('interviewer'));


document.body.dataset.mode = mode;