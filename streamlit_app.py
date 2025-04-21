import streamlit as st
import pandas as pd
from facebook_ad_scraper import FacebookAdScraper
from datetime import datetime
import time
import base64
import json
from io import StringIO
import csv
import hashlib
import os
import uuid
from pathlib import Path

# Configure Streamlit page
st.set_page_config(
    page_title="Facebook Ad Scraper",
    page_icon="🔍",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .url-input {
        margin-bottom: 10px;
    }
    .results-container {
        margin-top: 20px;
    }
    .auth-form {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
    }
    .stAlert {
        margin-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state variables
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'scraper' not in st.session_state:
    st.session_state.scraper = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'url_patterns' not in st.session_state:
    st.session_state.url_patterns = [""]
if 'last_search_time' not in st.session_state:
    st.session_state.last_search_time = None

# Create necessary directories
USERS_DIR = Path("users")
USERS_DIR.mkdir(exist_ok=True)

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    """Load users from the users directory."""
    users = {}
    for user_file in USERS_DIR.glob("*.json"):
        with open(user_file, "r") as f:
            user_data = json.load(f)
            users[user_data["username"]] = user_data
    return users

def save_user(username: str, password_hash: str):
    """Save a new user to the users directory."""
    user_id = str(uuid.uuid4())
    user_data = {
        "username": username,
        "password_hash": password_hash,
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    with open(USERS_DIR / f"{username}.json", "w") as f:
        json.dump(user_data, f)
    return user_id

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user."""
    users = load_users()
    if username in users:
        if users[username]["password_hash"] == hash_password(password):
            st.session_state.user_id = users[username]["user_id"]
            st.session_state.authenticated = True
            return True
    return False

def register_user(username: str, password: str) -> bool:
    """Register a new user."""
    users = load_users()
    if username in users:
        return False
    
    password_hash = hash_password(password)
    user_id = save_user(username, password_hash)
    st.session_state.user_id = user_id
    st.session_state.authenticated = True
    return True

def logout_user():
    """Log out the current user."""
    cleanup_scraper()  # Clean up user's scraper instance
    st.session_state.user_id = None
    st.session_state.authenticated = False
    st.session_state.scraper = None
    st.session_state.results = None
    st.session_state.url_patterns = [""]
    st.session_state.last_search_time = None

def initialize_scraper():
    """Initialize or reinitialize the scraper."""
    if st.session_state.scraper:
        st.session_state.scraper.close()
    st.session_state.scraper = FacebookAdScraper(quiet_mode=True)

def cleanup_scraper():
    """Clean up the scraper when the session ends."""
    if st.session_state.scraper:
        st.session_state.scraper.close()
        st.session_state.scraper = None

def add_url_pattern():
    """Add a new URL pattern input field."""
    st.session_state.url_patterns.append("")

def remove_url_pattern(index):
    """Remove a URL pattern input field."""
    if len(st.session_state.url_patterns) > 1:
        st.session_state.url_patterns.pop(index)

def create_download_link(df, filename, file_format):
    """Create a download link for the results."""
    if file_format == 'csv':
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'data:text/csv;base64,{b64}'
        ext = 'csv'
    else:  # JSON
        json_str = df.to_json(orient='records', indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'data:application/json;base64,{b64}'
        ext = 'json'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    download_filename = f'{filename}_{timestamp}.{ext}'
    return f'<a href="{href}" download="{download_filename}">Download {ext.upper()}</a>'

def show_auth_page():
    """Show the authentication page."""
    st.title("Facebook Ad Scraper")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if authenticate_user(username, password):
                    st.success("Successfully logged in!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            st.subheader("Register")
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif register_user(new_username, new_password):
                    st.success("Registration successful! You can now use the app.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Username already exists")

def show_main_app():
    """Show the main application."""
    st.title("Facebook Ad Scraper")
    st.markdown("Search and analyze Facebook ads with custom URL matching")

    # Add logout button in sidebar
    with st.sidebar:
        st.header("Settings")
        if st.button("Logout"):
            logout_user()
            st.rerun()
            
        watch_words_input = st.text_area(
            "Watch Words (one per line)",
            value="swimsuit\nunderwear\nlingerie\ndating\nlabiaplasty\nmassage\nbreast",
            help="Enter words to flag in ad content"
        )
        watch_words = watch_words_input.split('\n') if watch_words_input is not None else []
        
        if st.button("Reset Scraper"):
            initialize_scraper()
            st.success("Scraper reset successfully!")

    # Main search form
    with st.form("search_form"):
        search_term = st.text_input("Search Term", help="Enter the term to search for in Facebook Ads")
        
        st.subheader("URL Patterns to Match")
        
        # URL pattern inputs
        url_patterns_container = st.container()
        with url_patterns_container:
            for i, pattern in enumerate(st.session_state.url_patterns):
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.session_state.url_patterns[i] = st.text_input(
                        f"URL Pattern {i+1}",
                        value=pattern,
                        key=f"url_{i}",
                        help="Enter URL pattern to match (e.g., https://example.com)"
                    )
                with col2:
                    remove_clicked = st.form_submit_button(f"Remove Pattern {i+1}")
                    if remove_clicked:
                        remove_url_pattern(i)
        
        add_clicked = st.form_submit_button("Add URL Pattern")
        if add_clicked:
            add_url_pattern()
        
        submitted = st.form_submit_button("Search Ads")

    # Handle search submission
    if submitted and search_term:
        try:
            # Initialize scraper if needed
            if not st.session_state.scraper:
                initialize_scraper()
            
            # Update watch words
            st.session_state.scraper.set_watch_words(watch_words)
            
            # Show progress
            with st.spinner("Searching for ads... This may take a few minutes."):
                # Filter out empty URL patterns
                url_patterns = [p for p in st.session_state.url_patterns if p.strip()]
                
                # Perform search
                results = st.session_state.scraper.search_ads(search_term, url_patterns)
                
                if results:
                    # Convert results to DataFrame
                    df_data = []
                    flagged_data = []
                    
                    for ad in results:
                        ad_info = {
                            'Ad Text': ad.get('ad_text', ''),
                            'Library ID': ad.get('library_id', ''),
                            'Library Link': f"https://www.facebook.com/ads/library/?id={ad.get('library_id', '')}" if ad.get('library_id') else '',
                            'Ad Page URL': ad.get('ad_page_url', ''),
                            'Original URL': ad.get('original_urls', [''])[0] if ad.get('original_urls') else '',
                            'Final URL': ad.get('urls', [''])[0] if ad.get('urls') else '',
                            'Image URL': ad.get('image_url', '')
                        }
                        
                        if 'matched_words' in ad:
                            ad_info['Matched Words'] = ', '.join(ad['matched_words'])
                            flagged_data.append(ad_info)
                        else:
                            df_data.append(ad_info)
                    
                    # Store results in session state
                    st.session_state.results = {
                        'regular': pd.DataFrame(df_data),
                        'flagged': pd.DataFrame(flagged_data)
                    }
                    
                    # Display results
                    st.success(f"Found {len(df_data)} matching ads and {len(flagged_data)} flagged ads")
                    
                    # Display regular results
                    if not df_data:
                        st.info("No matching ads found")
                    else:
                        st.subheader("Matching Ads")
                        st.dataframe(
                            st.session_state.results['regular']
                            .style.format({
                                'Library Link': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Ad Page URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Original URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Final URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Image URL': lambda x: f'<a href="{x}" target="_blank">View Image</a>' if x else ''
                            })
                            .set_properties(**{
                                'text-align': 'left',
                                'white-space': 'pre-wrap'
                            }),
                            use_container_width=True
                        )
                    
                    # Display flagged results
                    if flagged_data:
                        st.subheader("Flagged Ads")
                        st.dataframe(
                            st.session_state.results['flagged']
                            .style.format({
                                'Library Link': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Ad Page URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Original URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Final URL': lambda x: f'<a href="{x}" target="_blank">{x}</a>',
                                'Image URL': lambda x: f'<a href="{x}" target="_blank">View Image</a>' if x else ''
                            })
                            .set_properties(**{
                                'text-align': 'left',
                                'white-space': 'pre-wrap'
                            }),
                            use_container_width=True
                        )
                    
                    # Download buttons
                    if df_data or flagged_data:
                        st.subheader("Download Results")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(
                                create_download_link(
                                    pd.concat([st.session_state.results['regular'], st.session_state.results['flagged']]),
                                    f'facebook_ad_matches_{st.session_state.user_id}',
                                    'csv'
                                ),
                                unsafe_allow_html=True
                            )
                        
                        with col2:
                            st.markdown(
                                create_download_link(
                                    pd.concat([st.session_state.results['regular'], st.session_state.results['flagged']]),
                                    f'facebook_ad_matches_{st.session_state.user_id}',
                                    'json'
                                ),
                                unsafe_allow_html=True
                            )
                else:
                    st.warning("No ads found matching your search criteria")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("""
                Please check:
                1. You have a stable internet connection
                2. You can access Facebook in your browser
                3. You're logged into Facebook
                4. The Facebook Ad Library is accessible in your region
            """)
            cleanup_scraper()

def main():
    """Main application flow."""
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        show_main_app()

if __name__ == "__main__":
    try:
        main()
    finally:
        # Cleanup when the script ends
        if not st.session_state.authenticated:
            cleanup_scraper() 