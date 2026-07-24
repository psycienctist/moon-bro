def render_bottom_nav():
    """Fixed bottom nav with 3 tabs + logo home button."""
    views = [
        ("🌙", "LunaTick", "home"),
        ("🌐", "Community", "community"),
        ("📓", "Journal", "journal"),
        ("⚙️", "Settings", "settings"),
    ]

    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)  # Spacer

    cols = st.columns(4)
    for i, (icon, label, view) in enumerate(views):
        with cols[i]:
            active = st.session_state.current_view == view
            btn_label = f"**{icon}**<br><span style='font-size:0.65rem;'>{label}</span>" if active else f"{icon}<br><span style='font-size:0.65rem; color:#6b7280'>{label}</span>"
            if st.button(btn_label, key=f"nav_{view}", use_container_width=True):
                st.session_state.current_view = view
                st.rerun()
```

---

Step 2: Replace It With This Fixed Version

Replace the entire render_bottom_nav() function with this:

```python
def render_bottom_nav():
    """Fixed bottom nav with 3 tabs + logo home button."""
    # --- FIXED: Force the nav to appear at the bottom ---
    st.markdown("""
    <style>
    .fixed-bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(10, 10, 15, 0.95);
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        padding: 10px 12px 14px 12px;
        z-index: 9999;
        display: flex;
        justify-content: space-around;
        align-items: center;
    }
    .fixed-bottom-nav button {
        background: transparent !important;
        border: none !important;
        color: #6b7280 !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        text-align: center;
        padding: 4px 8px;
        border-radius: 8px;
        transition: all 0.2s ease;
        flex: 1;
    }
    .fixed-bottom-nav button:hover {
        color: #a78bfa !important;
        background: rgba(124, 58, 237, 0.1) !important;
    }
    .fixed-bottom-nav button.active {
        color: #a78bfa !important;
        background: rgba(124, 58, 237, 0.15) !important;
    }
    /* Push content up so it doesn't hide behind the nav */
    .main-content {
        padding-bottom: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Display the nav ---
    views = [
        ("🌙", "LunaTick", "home"),
        ("🌐", "Community", "community"),
        ("📓", "Journal", "journal"),
        ("⚙️", "Settings", "settings"),
    ]

    nav_html = '<div class="fixed-bottom-nav">'
    for icon, label, view in views:
        active_class = 'active' if st.session_state.current_view == view else ''
        nav_html += f'''
        <button class="{active_class}" onclick="
            var key = 'nav_{view}';
            var btn = document.querySelector('[data-testid=\\"button\\"][data-key=\\"{key}\\"');
            if (btn) btn.click();
        ">
            <div style="font-size:1.4rem; line-height:1.2;">{icon}</div>
            <div style="font-size:0.6rem; margin-top:2px;">{label}</div>
        </button>
        '''
    nav_html += '</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

    # --- Hidden buttons (the real logic) ---
    for icon, label, view in views:
        if st.button(f"{icon} {label}", key=f"nav_{view}", use_container_width=True):
            st.session_state.current_view = view
            st.rerun()
```

---

Step 3: Make Sure the Nav Is Called Correctly

At the bottom of app.py, you should have:

```python
if __name__ == "__main__":
    main()
```

Do NOT add an extra render_bottom_nav() call here. The main() function already calls it.

---

Step 4: Add the Main Content Wrapper

In the main() function, find where the content is rendered and wrap it like this:

```python
def main():
    if not st.session_state.onboarded:
        render_onboarding()
        render_footer()
        return

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    # ... existing content rendering ...
    st.markdown('</div>', unsafe_allow_html=True)

    render_footer()
    render_bottom_nav()