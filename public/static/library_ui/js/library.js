document.addEventListener('DOMContentLoaded', () => {
  // ========================================================
  // 0. Dark Mode Theme Toggle & State Management
  // ========================================================
  const themeToggleBtn = document.getElementById('themeToggleBtn');

  function updateThemeUI(theme) {
    if (!themeToggleBtn) return;
    const isDark = theme === 'dark';
    const label = themeToggleBtn.querySelector('.theme-label');
    const iconLight = themeToggleBtn.querySelector('.theme-icon-light');
    const iconDark = themeToggleBtn.querySelector('.theme-icon-dark');

    if (label) label.textContent = isDark ? 'Light' : 'Dark';
    if (iconLight) iconLight.style.display = isDark ? 'inline' : 'none';
    if (iconDark) iconDark.style.display = isDark ? 'none' : 'inline';
    themeToggleBtn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
  }

  // Initial UI sync
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  updateThemeUI(currentTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const active = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const targetTheme = active === 'dark' ? 'light' : 'dark';

      document.documentElement.setAttribute('data-theme', targetTheme);
      if (targetTheme === 'dark') {
        document.documentElement.classList.add('theme-dark');
      } else {
        document.documentElement.classList.remove('theme-dark');
      }

      try {
        localStorage.setItem('slibro_theme', targetTheme);
      } catch (e) {}

      updateThemeUI(targetTheme);
    });
  }

  // ========================================================
  // 1. Mobile Menu Toggle
  // ========================================================
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const mainNav = document.querySelector('[data-menu]');
  if (menuToggle && mainNav) {
    menuToggle.addEventListener('click', () => {
      mainNav.classList.toggle('open');
      const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
      menuToggle.setAttribute('aria-expanded', !expanded);
    });
  }

  // ========================================================
  // 2. Password Visibility Toggle
  // ========================================================
  const passwordToggles = document.querySelectorAll('[data-password-toggle]');
  passwordToggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
      const wrap = toggle.closest('.password-wrap');
      const input = wrap ? wrap.querySelector('input') : null;
      if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        toggle.textContent = isPassword ? 'Hide' : 'Show';
      }
    });
  });

  // ========================================================
  // 3. Helper: Get CSRF token
  // ========================================================
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie('csrftoken');

  // ========================================================
  // 4. Smart Predictive Live Search (AJAX)
  // ========================================================
  const searchInputs = document.querySelectorAll(
    '.mockup-search-pill input, .mockup-hero-search-form input, .hero-search input, #q, .toolbar-search input'
  );
  searchInputs.forEach(input => {
    const parent = input.closest('form') || input.parentElement;
    parent.style.position = 'relative';

    const dropdown = document.createElement('div');
    dropdown.className = 'search-results-dropdown';
    parent.appendChild(dropdown);

    let debounceTimer;
    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 2) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
        return;
      }

      debounceTimer = setTimeout(() => {
        fetch(`/ai/search-suggest/?q=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(data => {
            if (data.results && data.results.length > 0) {
              dropdown.innerHTML = data.results.map(b => `
                <a href="${b.url}" class="search-dropdown-item">
                  <div>
                    <strong>${b.title}</strong>
                    <small>by ${b.author} · ${b.category}</small>
                  </div>
                  <span class="status-pill ${b.available ? 'pill-active' : 'pill-overdue'}">
                    ${b.available ? `${b.available_count} Available` : 'On Loan'}
                  </span>
                </a>
              `).join('');
              dropdown.style.display = 'block';
            } else {
              dropdown.innerHTML = '<div style="padding:12px;font-size:11px;color:#64748B;text-align:center;">No matching titles found</div>';
              dropdown.style.display = 'block';
            }
          })
          .catch(() => {
            dropdown.style.display = 'none';
          });
      }, 250);
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!parent.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    });
  });

  // ========================================================
  // 5. Floating Smart AI Assistant (LibroAI)
  // ========================================================
  const aiFabBtn = document.getElementById('aiFabBtn');
  const aiCloseBtn = document.getElementById('aiCloseBtn');
  const aiChatWindow = document.getElementById('aiChatWindow');
  const aiChatBody = document.getElementById('aiChatBody');
  const aiChatInput = document.getElementById('aiChatInput');
  const aiSendBtn = document.getElementById('aiSendBtn');

  if (aiFabBtn && aiChatWindow) {
    aiFabBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = aiChatWindow.classList.toggle('open');
      aiChatWindow.classList.toggle('active', isOpen);
      if (isOpen) {
        setTimeout(() => aiChatInput && aiChatInput.focus(), 150);
      }
    });

    if (aiCloseBtn) {
      aiCloseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        aiChatWindow.classList.remove('open');
        aiChatWindow.classList.remove('active');
      });
    }

    // Close when clicking outside chat window
    document.addEventListener('click', (e) => {
      if (aiChatWindow.classList.contains('open') || aiChatWindow.classList.contains('active')) {
        if (!aiChatWindow.contains(e.target) && !aiFabBtn.contains(e.target)) {
          aiChatWindow.classList.remove('open');
          aiChatWindow.classList.remove('active');
        }
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && (aiChatWindow.classList.contains('open') || aiChatWindow.classList.contains('active'))) {
        aiChatWindow.classList.remove('open');
        aiChatWindow.classList.remove('active');
      }
    });

    function appendMessage(text, sender, books, chips, aiLabel) {
      const msgDiv = document.createElement('div');
      msgDiv.className = `ai-msg ai-msg-${sender}`;

      let inner = '';
      if (sender === 'bot' && aiLabel) {
        inner += `<div class="ai-generated-badge"><span>✦</span> ${aiLabel}</div>`;
      }

      // Safe formatting for linebreaks and bold tags
      const safeText = (text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

      inner += `<div class="ai-msg-content">${safeText}</div>`;

      if (books && books.length > 0) {
        inner += `<div class="ai-book-list">` + books.map(b => `
          <div class="ai-book-row">
            <strong><a href="${b.url}">${b.title}</a></strong>
            <small>by ${b.author} · <span class="status-pill ${b.available ? 'pill-active' : 'pill-overdue'}">${b.available ? (b.available_count + ' Available') : 'On Loan'}</span></small>
          </div>
        `).join('') + `</div>`;
      }

      if (chips && chips.length > 0) {
        inner += `<div class="ai-chip-group">` + chips.map(c => `
          <button type="button" class="ai-chip" data-chip="${c}">${c}</button>
        `).join('') + `</div>`;
      }

      msgDiv.innerHTML = inner;
      aiChatBody.appendChild(msgDiv);
      aiChatBody.scrollTop = aiChatBody.scrollHeight;

      // Bind dynamic chip clicks
      msgDiv.querySelectorAll('.ai-chip').forEach(btn => {
        btn.addEventListener('click', () => {
          sendQuery(btn.getAttribute('data-chip'));
        });
      });
    }

    function sendQuery(text) {
      text = text ? text.trim() : '';
      if (!text) return;

      appendMessage(text, 'user');
      if (aiChatInput) aiChatInput.value = '';

      // Typing indicator
      const typingDiv = document.createElement('div');
      typingDiv.className = 'ai-msg ai-msg-bot';
      typingDiv.id = 'aiTyping';
      typingDiv.innerHTML = '<em>LibroAI is thinking...</em>';
      aiChatBody.appendChild(typingDiv);
      aiChatBody.scrollTop = aiChatBody.scrollHeight;

      fetch('/ai/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken || ''
        },
        body: JSON.stringify({ message: text })
      })
      .then(res => res.json())
      .then(data => {
        const typingEl = document.getElementById('aiTyping');
        if (typingEl) typingEl.remove();

        appendMessage(data.reply, 'bot', data.books, data.quick_chips, data.ai_label);
      })
      .catch(err => {
        const typingEl = document.getElementById('aiTyping');
        if (typingEl) typingEl.remove();
        appendMessage("Sorry, I encountered an issue connecting to the library AI service. Normal catalogue search remains available.", 'bot');
      });
    }

    if (aiSendBtn && aiChatInput) {
      aiSendBtn.addEventListener('click', () => sendQuery(aiChatInput.value));
      aiChatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendQuery(aiChatInput.value);
        }
      });
    }

    // Attach click events to initial chips
    aiChatBody.querySelectorAll('.ai-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        sendQuery(btn.getAttribute('data-chip'));
      });
    });
  }
});
