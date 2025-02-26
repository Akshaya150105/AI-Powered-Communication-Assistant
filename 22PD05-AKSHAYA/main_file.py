import streamlit as st
from PIL import Image
import base64
import os
if "page" in st.session_state:
    exec(open(st.session_state["page"]).read())
    st.stop()
def main():
    # Page configuration
    st.set_page_config(
        page_title="Communication Hub",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for styling
    st.markdown("""
    <style>
        /* Main container styling */
        .main {
            padding: 2rem;
        }
        
        /* Header styling */
        .title {
            font-size: 3.5rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 0.5rem;
            background: linear-gradient(45deg, #2b5876, #4e4376);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            font-size: 1.5rem;
            text-align: center;
            color: #555;
            margin-bottom: 3rem;
        }
        
        /* App card styling */
        .app-container {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 2rem;
        }
        
        .app-card {
            background-color: white;
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            width: 100%;
            max-width: 350px;
            height: 350px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .app-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
        }
        
        .app-icon {
            width: 120px;
            height: 120px;
            margin-bottom: 1.5rem;
            object-fit: contain;
        }
        
        .app-title {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        
        .app-description {
            font-size: 1rem;
            color: #666;
            margin-bottom: 1.5rem;
        }
        
        /* Button styling */
        .launch-btn {
            background: linear-gradient(45deg, #2b5876, #4e4376);
            color: white;
            border: none;
            padding: 0.8rem 2rem;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            margin-top: auto;
        }
        
        .launch-btn:hover {
            background: linear-gradient(45deg, #4e4376, #2b5876);
            transform: scale(1.05);
        }
        
        /* Footer styling */
        .footer {
            margin-top: 4rem;
            text-align: center;
            color: #888;
            font-size: 0.9rem;
        }
        
        /* Additional responsive styling */
        @media (max-width: 1200px) {
            .app-container {
                flex-direction: column;
                align-items: center;
            }
            
            .app-card {
                margin-bottom: 2rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main content
    st.markdown('<h1 class="title">Communication Hub</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Connect to your favorite messaging platforms</p>', unsafe_allow_html=True)
    
    # App cards container
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    
    # Gmail Card
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="app-card">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Gmail_icon_%282020%29.svg/2560px-Gmail_icon_%282020%29.svg.png" class="app-icon">
            <h2 class="app-title">Gmail</h2>
            <p class="app-description">Access your emails, compose new messages, and manage your inbox.</p>
            <div style="margin-top: auto;">
        """, unsafe_allow_html=True)
        
        if st.button("Launch Gmail", key="gmail_btn"):
            switch_to_app("pages\gmail_main.py")
            
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    # Slack Card
    with col2:
        st.markdown("""
        <div class="app-card">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Slack_icon_2019.svg/2048px-Slack_icon_2019.svg.png" class="app-icon">
            <h2 class="app-title">Slack</h2>
            <p class="app-description">Connect with your team, manage channels, and boost productivity.</p>
            <div style="margin-top: auto;">
        """, unsafe_allow_html=True)
        
        if st.button("Launch Slack", key="slack_btn"):
            switch_to_app("pages\main_slack.py")
            
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    # WhatsApp Card
    with col3:
        st.markdown("""
        <div class="app-card">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/767px-WhatsApp.svg.png" class="app-icon">
            <h2 class="app-title">WhatsApp</h2>
            <p class="app-description">Stay connected with friends and family with instant messaging.</p>
            <div style="margin-top: auto;">
        """, unsafe_allow_html=True)
        
        if st.button("Launch WhatsApp", key="whatsapp_btn"):
            switch_to_app("pages\whatsapp_main.py")
            
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>© 2025 Communication Hub | All platforms are integrated as separate applications</p>
    </div>
    """, unsafe_allow_html=True)

def switch_to_app(app_path):
    """Function to switch to the specified application"""
    try:
        # For Streamlit's navigation
        st.switch_page(app_path)
    except Exception as e:
        # Fallback for local development
        st.error(f"Error opening application: {str(e)}")
        st.info(f"Please make sure '{app_path}' exists in your Streamlit project's pages directory.")

if __name__ == "__main__":
    main()