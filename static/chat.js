// chat.js - Pigeon Messenger

let ws = null;
let currentUser = null;
let currentChat = null;
let friendRequests = [];
let contacts = [];
let profiles = JSON.parse(localStorage.getItem('pigeon_profiles') || '{}');
let selectedMessageId = null;
let replyToMessage = null; // Для ответа на сообщение

const statusEl = document.getElementById('global-status');
const soundSend = document.getElementById('sound-send');
const soundReceive = document.getElementById('sound-receive');

// ========== ТЕМА ==========
function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-theme');
    document.getElementById('theme-toggle').textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('pigeon_theme', isDark ? 'dark' : 'light');
}

if (localStorage.getItem('pigeon_theme') === 'dark') {
    document.body.classList.add('dark-theme');
    document.getElementById('theme-toggle').textContent = '☀️';
}

// ========== ЭКРАНЫ ==========
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
    if (tab === 'login') {
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.getElementById('login-form').classList.add('active');
    } else {
        document.querySelectorAll('.tab')[1].classList.add('active');
        document.getElementById('register-form').classList.add('active');
    }
}

function switchSidebarTab(tab) {
    document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
    if (tab === 'chats') {
        document.querySelectorAll('.sidebar-tab')[0].classList.add('active');
        document.getElementById('chats-list').style.display = 'block';
        document.getElementById('requests-list').style.display = 'none';
    } else {
        document.querySelectorAll('.sidebar-tab')[1].classList.add('active');
        document.getElementById('chats-list').style.display = 'none';
        document.getElementById('requests-list').style.display = 'block';
        renderFriendRequests();
    }
}

// ========== ПРОФИЛЬ ==========
function openProfile() {
    document.getElementById('profile-login').value = currentUser || '';
    document.getElementById('profile-firstname').value = profiles[currentUser]?.firstName || '';
    document.getElementById('profile-lastname').value = profiles[currentUser]?.lastName || '';
    document.getElementById('profile-nickname').value = profiles[currentUser]?.nickname || '';
    showScreen('profile-screen');
}

function closeProfile() {
    showScreen('chat-screen');
}

function saveProfile() {
    const firstName = document.getElementById('profile-firstname').value.trim();
    const lastName = document.getElementById('profile-lastname').value.trim();
    const nickname = document.getElementById('profile-nickname').value.trim();
    
    profiles[currentUser] = { firstName, lastName, nickname };
    localStorage.setItem('pigeon_profiles', JSON.stringify(profiles));
    
    alert('Профиль сохранён!');
    closeProfile();
}

// ========== КОНТЕКСТНОЕ МЕНЮ ==========
function showContextMenu(event, text, messageId) {
    // Удаляем старое меню
    const oldMenu = document.querySelector('.context-menu');
    if (oldMenu) oldMenu.remove();

    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.top = event.clientY + 'px';
    menu.style.left = event.clientX + 'px';

    menu.innerHTML = `
        <div class="context-menu-item" onclick="copyMessage('${encodeURIComponent(text)}'); closeContextMenu();">
            📋 Копировать
        </div>
        <div class="context-menu-item" onclick="startReply('${messageId}'); closeContextMenu();">
            ↩️ Ответить
        </div>
    `;

    document.body.appendChild(menu);

    // Закрыть при клике вне меню
    setTimeout(() => {
        document.addEventListener('click', closeContextMenu, { once: true });
    }, 100);
}

function closeContextMenu() {
    const menu = document.querySelector('.context-menu');
    if (menu) menu.remove();
}

// ========== КОПИРОВАТЬ ==========
function copyMessage(encodedText) {
    const text = decodeURIComponent(encodedText);
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Скопировано!');
        });
    } else {
        // Для старых браузеров
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('Скопировано!');
        } catch (e) {
            showToast('Ошибка копирования');
        }
        document.body.removeChild(textarea);
    }
}

// ========== ОТВЕТИТЬ ==========
function startReply(messageId) {
    const messageElement = document.getElementById(`msg-${messageId}`);
    if (!messageElement) return;
    
    const text = messageElement.querySelector('.message-bubble').innerText.split('\n').slice(1).join(' ');
    replyToMessage = { id: messageId, text: text.substring(0, 50) };
    
    // Показываем панель ответа
    showReplyBar(text.substring(0, 50));
}

function showReplyBar(text) {
    const existingBar = document.querySelector('.reply-bar');
    if (existingBar) existingBar.remove();

    const chatArea = document.querySelector('.chat-area');
    const messageInput = document.querySelector('.message-input');
    
    const replyBar = document.createElement('div');
    replyBar.className = 'reply-bar';
    replyBar.innerHTML = `
        <span>↩️ ${text}...</span>
        <button onclick="cancelReply()">✖️</button>
    `;
    
    chatArea.insertBefore(replyBar, messageInput);
}

function cancelReply() {
    replyToMessage = null;
    const replyBar = document.querySelector('.reply-bar');
    if (replyBar) replyBar.remove();
}

// ========== ТОСТ (мини-уведомление) ==========
function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #333;
        color: white;
        padding: 12px 24px;
        border-radius: 24px;
        font-size: 14px;
        z-index: 9999;
        opacity: 0;
        transition: opacity 0.3s;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => { toast.style.opacity = '1'; }, 10);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// ========== ЗВУКИ ==========
function playSound(type) {
    const sound = type === 'send' ? soundSend : soundReceive;
    if (sound) {
        sound.currentTime = 0;
        sound.play().catch(() => {}); // Игнорируем ошибку если браузер блокирует
    }
}

// ========== WEBSOCKET ==========
function connectWebSocket(username) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    
    // Авто-определение адреса (локально или на Render)
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
ws = new WebSocket(`${protocol}//${host}/ws/${username}`);
    
    ws.onopen = () => {
        statusEl.textContent = '🟢 Онлайн';
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.status === 'sent' && data.id) {
            updateMessageStatus(data.id, 'sent');
        }
        
        if (data.type === 'friend_request') {
            friendRequests.push(data.from);
            updateRequestsBadge();
            renderFriendRequests();
        }
        
        if (data.type === 'friend_accepted') {
            contacts.push(data.from);
            renderContacts();
        }
        
        if (data.from && data.text) {
            playSound('receive');
            if (currentChat === data.from) {
                addMessageToChat(data.from, data.text, false, 'read', data.id, data.replyTo);
                ws.send(JSON.stringify({ type: 'read', target: data.from, messageId: data.id }));
            }
        }
        
        if (data.type === 'read' && data.messageId) {
            updateMessageStatus(data.messageId, 'read');
        }
        
        if (data.type === 'reaction') {
            addReactionToMessage(data.messageId, data.reaction);
        }
    };
    
    ws.onclose = () => { statusEl.textContent = '🔴 Офлайн'; };
    ws.onerror = () => { statusEl.textContent = '⚠️ Ошибка'; };
}

// ========== СТАТУСЫ ==========
function updateMessageStatus(msgId, status) {
    const msgElement = document.getElementById(`msg-${msgId}`);
    if (!msgElement) return;
    const statusSpan = msgElement.querySelector('.message-status');
    if (statusSpan) {
        if (status === 'pending') statusSpan.textContent = '🕒';
        else if (status === 'sent') statusSpan.textContent = '✓';
        else if (status === 'read') statusSpan.textContent = '✓✓';
    }
}

// ========== СООБЩЕНИЯ ==========
function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text || !currentChat || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    playSound('send');
    
    const msgId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    ws.send(JSON.stringify({
        id: msgId,
        target: currentChat,
        text: text,
        timestamp: new Date().toISOString(),
        replyTo: replyToMessage?.id || null
    }));
    
    addMessageToChat(currentUser, text, true, 'pending', msgId, replyToMessage?.text);
    input.value = '';
    cancelReply();
}

function addMessageToChat(sender, text, own, status = 'read', msgId = null, replyText = null) {
    const container = document.getElementById('messages-container');
    const emptyMsg = container.querySelector('.empty-chat-message');
    if (emptyMsg) emptyMsg.remove();

    const id = msgId || Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${own ? 'own' : ''}`;
    messageDiv.id = `msg-${id}`;

    let statusIcon = '';
    if (own) {
        if (status === 'pending') statusIcon = '🕒';
        else if (status === 'sent') statusIcon = '✓';
        else if (status === 'read') statusIcon = '✓✓';
    }

    messageDiv.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e, text, id);
    });

    const replyHTML = replyText
        ? `<div class="message-reply-preview">↩️ ${replyText}</div>`
        : '';

    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${replyHTML}
            <b>${sender}</b>
            ${text}
            <div class="message-meta">
                <span>${new Date().toLocaleTimeString().slice(0, 5)}</span>
                ${own ? `<span class="message-status">${statusIcon}</span>` : ''}
            </div>
            <div class="message-reactions" id="reactions-${id}"></div>
        </div>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    return id;
}

// ========== РЕАКЦИИ ==========
function showReactionPicker(messageId) {
    selectedMessageId = messageId;
    const picker = document.getElementById('reaction-picker');
    picker.style.display = 'flex';
    
    const msgElement = document.getElementById(`msg-${messageId}`);
    const rect = msgElement.getBoundingClientRect();
    picker.style.top = (rect.top - 60) + 'px';
    picker.style.left = (rect.left + rect.width / 2) + 'px';
    
    setTimeout(() => { picker.style.display = 'none'; }, 3000);
}

function addReaction(emoji) {
    if (!selectedMessageId || !currentChat) return;
    
    ws.send(JSON.stringify({
        type: 'reaction',
        target: currentChat,
        messageId: selectedMessageId,
        reaction: emoji
    }));
    
    addReactionToMessage(selectedMessageId, emoji);
    document.getElementById('reaction-picker').style.display = 'none';
}

function addReactionToMessage(messageId, emoji) {
    const reactionsDiv = document.getElementById(`reactions-${messageId}`);
    if (!reactionsDiv) return;
    
    const existing = Array.from(reactionsDiv.children).find(b => b.textContent.startsWith(emoji));
    if (existing) {
        const count = parseInt(existing.dataset.count || '1') + 1;
        existing.dataset.count = count;
        existing.textContent = `${emoji} ${count}`;
    } else {
        const badge = document.createElement('span');
        badge.className = 'reaction-badge';
        badge.dataset.count = '1';
        badge.textContent = emoji;
        badge.onclick = () => addReaction(emoji);
        reactionsDiv.appendChild(badge);
    }
}

// ========== АВТОРИЗАЦИЯ ==========
async function login() {
    const username = document.getElementById('login-username').value.trim();
    if (!username) { alert('Введите логин'); return; }
    
    currentUser = username;
    document.getElementById('current-username').textContent = username;
    connectWebSocket(username);
    
    // 🔄 АНИМАЦИЯ: логин улетает вниз, чат выезжает сверху
    const loginScreen = document.getElementById('login-screen');
    const chatScreen = document.getElementById('chat-screen');
    
    // Сначала убираем active у логина и добавляем класс анимации
    loginScreen.classList.add('fly-down');
    
    // Через 400ms (когда анимация закончится) — переключаем экраны
    setTimeout(() => {
        loginScreen.classList.remove('active', 'fly-down');
        
        // Показываем чат с анимацией
        chatScreen.classList.add('active', 'fly-up');
        
        // Разблокируем ввод
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-button').disabled = false;
        renderContacts();
        
        // Убираем класс анимации после завершения
        setTimeout(() => {
            chatScreen.classList.remove('fly-up');
        }, 500);
    }, 400);

}

async function register() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const password2 = document.getElementById('reg-password2').value;
    
    if (!username) { alert('Введите логин'); return; }
    if (password !== password2) { alert('Пароли не совпадают'); return; }
    if (password.length < 4) { alert('Пароль минимум 4 символа'); return; }
    
    alert(`Регистрация успешна! Теперь войдите как ${username}`);
    switchTab('login');
    document.getElementById('login-username').value = username;
}

// ========== КОНТАКТЫ И ЗАЯВКИ ==========
function addContact() {
    const input = document.getElementById('search-input');
    const username = input.value.trim();
    if (!username) { alert('Введите логин'); return; }
    if (username === currentUser) { alert('Нельзя добавить себя'); return; }
    
    ws.send(JSON.stringify({ type: 'friend_request', target: username }));
    input.value = '';
    alert(`Заявка отправлена пользователю ${username}`);
}

function renderContacts() {
    const container = document.getElementById('chats-list');
    container.innerHTML = '';
    contacts.forEach(contact => {
        const div = document.createElement('div');
        div.className = 'contact-item';
        div.innerHTML = `<span class="status-dot online"></span><span>${contact}</span>`;
        div.onclick = () => openChat(contact);
        container.appendChild(div);
    });
}

function renderFriendRequests() {
    const container = document.getElementById('requests-list');
    container.innerHTML = '';
    friendRequests.forEach(from => {
        const div = document.createElement('div');
        div.className = 'contact-item';
        div.innerHTML = `
            <span>🕊️ ${from}</span>
            <div class="request-actions">
                <button onclick="acceptRequest('${from}')">✅</button>
                <button onclick="declineRequest('${from}')">❌</button>
            </div>
        `;
        container.appendChild(div);
    });
    updateRequestsBadge();
}

function updateRequestsBadge() {
    const badge = document.getElementById('requests-badge');
    const count = friendRequests.length;
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline';
    } else {
        badge.style.display = 'none';
    }
}

function acceptRequest(from) {
    ws.send(JSON.stringify({ type: 'accept_friend', target: from }));
    friendRequests = friendRequests.filter(r => r !== from);
    contacts.push(from);
    renderFriendRequests();
    renderContacts();
}

function declineRequest(from) {
    friendRequests = friendRequests.filter(r => r !== from);
    renderFriendRequests();
}

function openChat(username) {
    currentChat = username;
    const displayName = profiles[username]?.firstName || username;
    document.getElementById('chat-title').textContent = displayName;
    document.getElementById('chat-status').textContent = 'онлайн';
    document.getElementById('messages-container').innerHTML = `
        <div class="empty-chat-message">
            <div class="empty-icon">🕊️</div>
            <h3>Чат с ${displayName}</h3>
            <p>Отправьте первое сообщение!</p>
        </div>
    `;
    document.getElementById('message-input').disabled = false;
    document.getElementById('send-button').disabled = false;
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'chat_opened', target: username }));
    }
}

function logout() {
    if (ws) ws.close();
    currentUser = null;
    currentChat = null;
    showScreen('login-screen');
}

// ========== ENTER ==========
document.addEventListener('DOMContentLoaded', () => {
    const msgInput = document.getElementById('message-input');
    if (msgInput) {
        msgInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});
