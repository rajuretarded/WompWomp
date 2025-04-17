# app/__init__.py
import os
import spacy
import nltk
from flask import Flask
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- Global variables for NLP models (Load once) ---
nlp = None
analyzer = None
common_dream_symbols_set = set() # Initialize empty

def load_nlp_models():
    """Loads NLP models and data. Called once during app creation."""
    global nlp, analyzer, common_dream_symbols_set
    if nlp and analyzer and common_dream_symbols_set: return # Avoid reloading
    print("Loading NLP models...")
    try: nlp = spacy.load('en_core_web_sm'); print("-> spaCy loaded.")
    except OSError: print("Error: spaCy model not found."); nlp = None
    try: nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError: print("VADER lexicon not found. Downloading..."); nltk.download('vader_lexicon', quiet=True)
    try: analyzer = SentimentIntensityAnalyzer(); print("-> VADER initialized.")
    except Exception as e: print(f"Error initializing VADER: {e}"); analyzer = None
    common_dream_symbols = ["teeth","falling","flying","chased","water","ocean","river","lake","snake","spider","dog","cat","baby","death","house","home","school","exam","test","naked","lost","trapped","car","vehicle","road","journey","money","food","monster","friend","family","stranger","celebrity","fire","blood","door","window","key","box","mirror","phone","computer","tree","forest","mountain","sky","sun","moon","stars","book","library","supermarket","cereal","cloud","bicycle","pit","dust","hands"]
    common_dream_symbols_set = set(s.lower() for s in common_dream_symbols)
    print(f"-> Defined {len(common_dream_symbols_set)} symbols.")
    print("NLP loading complete.")

def create_app(config_object=None):
    """Application factory function."""
    app = Flask(__name__)
    project_root = os.path.dirname(os.path.dirname(__file__))
    default_data_dir = os.path.join(project_root, 'data')
    app.config['DATA_DIRECTORY'] = os.environ.get('DATA_DIRECTORY', default_data_dir)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-change-me')
    print(f"Data directory: {app.config['DATA_DIRECTORY']}")
    try: os.makedirs(app.config['DATA_DIRECTORY'], exist_ok=True)
    except OSError as e: print(f"Error creating data directory: {e}")

    load_nlp_models() # Load NLP

    # --- Initialize Services ---
    from .services import initialize_journal_service, initialize_symbol_guide_service # Import initializers
    journal_file = os.path.join(app.config['DATA_DIRECTORY'], 'dream_journal.csv')
    symbol_guide_file = os.path.join(app.config['DATA_DIRECTORY'], 'symbol_guide.csv') # Define path
    initialize_journal_service(journal_file)
    initialize_symbol_guide_service(symbol_guide_file) # Initialize symbol guide

    # --- Register Blueprints ---
    from .routes import api_bp
    app.register_blueprint(api_bp)

    print("Flask app created, NLP loaded, services initialized, API blueprint registered.")
    return app