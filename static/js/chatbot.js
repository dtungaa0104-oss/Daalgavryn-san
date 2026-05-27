/* ═══════════════════════════════════════════════════
   ОРХОНТУУЛ ЕБС — Чатбот v2
   ═══════════════════════════════════════════════════ */
(function() {
  'use strict';

  var chatHistory = [];
  var chatOpen = false;

  function init() {
    // Event listeners - inline onclick-г орлуулах
    var chatBtn = document.getElementById('chat-btn');
    var closeBtn = document.querySelector('.chat-close');
    var sendBtn  = document.getElementById('chat-send');
    var input    = document.getElementById('chat-input');

    if (chatBtn)  chatBtn.addEventListener('click', toggleChat);
    if (closeBtn) closeBtn.addEventListener('click', toggleChat);
    if (sendBtn)  sendBtn.addEventListener('click', sendChat);
    if (input) {
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendChat();
        }
      });
      input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
      });
    }

    // Quick buttons
    var quickBtns = document.querySelectorAll('.quick-btn');
    quickBtns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        quickSend(this.getAttribute('data-msg') || this.textContent);
      });
    });

    // 3 секундын дараа анхааруулга
    setTimeout(function() {
      if (!chatOpen) {
        var notif = document.getElementById('chat-notif');
        if (notif) notif.style.display = 'block';
      }
    }, 3000);
  }

  function toggleChat() {
    chatOpen = !chatOpen;
    var win  = document.getElementById('chat-window');
    var icon = document.getElementById('chat-icon');
    var notif = document.getElementById('chat-notif');
    if (!win) return;
    win.classList.toggle('open', chatOpen);
    if (icon)  icon.textContent = chatOpen ? '✕' : '💬';
    if (notif) notif.style.display = 'none';
    if (chatOpen) {
      var inp = document.getElementById('chat-input');
      if (inp) setTimeout(function() { inp.focus(); }, 100);
    }
  }

  function quickSend(text) {
    var qb  = document.getElementById('quick-btns');
    var inp = document.getElementById('chat-input');
    if (qb)  qb.style.display = 'none';
    if (inp) inp.value = text;
    sendChat();
  }

  async function sendChat() {
    var input   = document.getElementById('chat-input');
    var sendBtn = document.getElementById('chat-send');
    var text    = input ? input.value.trim() : '';
    if (!text) return;

    input.value = '';
    input.style.height = 'auto';
    if (sendBtn) sendBtn.disabled = true;
    var qb = document.getElementById('quick-btns');
    if (qb) qb.style.display = 'none';

    addMsg('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Typing indicator
    var msgs   = document.getElementById('chat-messages');
    var typing = document.createElement('div');
    typing.className = 'chat-msg bot';
    typing.id = 'typing-indicator';
    typing.innerHTML = '<div class="msg-avatar bot">🤖</div><div class="chat-typing"><span></span><span></span><span></span></div>';
    if (msgs) { msgs.appendChild(typing); scrollChat(); }

    try {
      var res = await fetch('/api/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ messages: chatHistory })
      });

      var t = document.getElementById('typing-indicator');
      if (t) t.remove();

      var data = await res.json();
      if (data.error) {
        addMsg('bot', '⚠️ ' + (data.error.includes('API') ? 'API тохируулаагүй байна.' : data.error));
      } else {
        var reply = data.reply || data.result || '';
        addMsg('bot', reply);
        chatHistory.push({ role: 'assistant', content: reply });
        if (chatHistory.length > 20) chatHistory = chatHistory.slice(-16);
      }
    } catch(e) {
      var t2 = document.getElementById('typing-indicator');
      if (t2) t2.remove();
      addMsg('bot', '❌ Холболтын алдаа. Дахин оролдоно уу.');
    }

    if (sendBtn) sendBtn.disabled = false;
  }

  function addMsg(role, text) {
    var msgs = document.getElementById('chat-messages');
    if (!msgs) return;
    var div  = document.createElement('div');
    div.className = 'chat-msg ' + role;
    var av   = role === 'bot'
      ? '<div class="msg-avatar bot">🤖</div>'
      : '<div class="msg-avatar user">👤</div>';
    var html = (text || '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
      .replace(/\n/g,'<br>');
    div.innerHTML = role === 'bot'
      ? av + '<div class="msg-bubble">' + html + '</div>'
      : '<div class="msg-bubble">' + html + '</div>' + av;
    msgs.appendChild(div);
    scrollChat();
  }

  function scrollChat() {
    var msgs = document.getElementById('chat-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  // Global functions (onclick attribute-аас дуудагдах)
  window.toggleChat = toggleChat;
  window.quickSend  = quickSend;
  window.sendChat   = sendChat;

  // DOM бэлэн болсны дараа init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
