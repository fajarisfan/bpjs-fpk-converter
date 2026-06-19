# ── LOGIN ────────────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

# ── LOGIN PAGE WITH THEME TOGGLE ──────────────────────────
if not st.session_state.logged_in:
    # Tampilkan toggle tema di pojok kanan atas
    col_empty, col_theme = st.columns([6, 1])
    with col_theme:
        icon = "☀️" if st.session_state.dark_mode else "🌙"
        if st.button(icon, help="Ganti tema", key="login_theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    inject_css(st.session_state.dark_mode)

    st.markdown("""
    <div class="login-wrapper">
        <div class="login-card">
            <div class="icon">🔐</div>
            <h2>FPK Converter</h2>
            <p class="sub">Masukkan PIN untuk melanjutkan</p>
            <div class="input-wrap" id="pin_container"></div>
            <div class="footer-text">v1.0 · privasi terlindungi</div>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Tunggu hingga input Streamlit muncul
            function findAndMovePinInput() {
                const container = document.getElementById('pin_container');
                if (!container) return;
                const inputs = document.querySelectorAll('input[type="password"]');
                for (let inp of inputs) {
                    if (inp.closest('.stTextInput')) {
                        container.innerHTML = '';
                        container.appendChild(inp);
                        inp.style.width = '100%';
                        inp.style.color = 'transparent';  // tetap tidak terlihat
                        inp.style.caretColor = '#ff6b35';
                        inp.placeholder = '• • • •';
                        inp.autocomplete = 'off';
                        inp.spellcheck = false;
                        inp.style.fontSize = '1.2rem';
                        inp.style.letterSpacing = '4px';
                        inp.style.textAlign = 'center';
                        // Fokus otomatis
                        setTimeout(() => inp.focus(), 100);
                        break;
                    }
                }
            }

            // Jalankan saat DOM siap dan setelah Streamlit merender ulang
            findAndMovePinInput();

            // Observer untuk menangani perubahan DOM (Streamlit rerender)
            const observer = new MutationObserver(function() {
                findAndMovePinInput();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        });
    </script>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin_input = st.text_input("", type="password", placeholder="", key="pin_login", label_visibility="collapsed", autocomplete="off")
        if st.button("Masuk", key="btn_masuk", use_container_width=True):
            ok, msg = check_pin(pin_input)
            if ok:
                st.session_state.logged_in = True
                st.session_state.login_time = now_wib().isoformat()
                st.rerun()
            else:
                st.error(msg)
    st.stop()
