# app/services.py
import pandas as pd
import os
import uuid
from datetime import datetime, timedelta
import json
from collections import Counter
import random # For dreamify

# Import NLP models loaded in __init__.py
from . import nlp, analyzer, common_dream_symbols_set

# --- Helper Functions ---

def get_primary_emotion(emotion_str):
    """Parses the VADER JSON string and returns primary emotion category."""
    try:
        if not isinstance(emotion_str, str) or not emotion_str.strip().startswith('{'): return "Unknown"
        scores = json.loads(emotion_str)
        if scores:
            compound = scores.get('compound', 0)
            if compound >= 0.05: return "Positive"
            elif compound <= -0.05: return "Negative"
            else: return "Neutral"
        return "Unknown"
    except (json.JSONDecodeError, TypeError): return "Unknown"

def _calculate_dream_dna_logic(dream_entry_series):
    """Internal logic to calculate Dream DNA from a dream entry Series."""
    THEME_KEYWORDS = { # Define themes here or load from config
        'Conflict/Fear': ['fight', 'argument', 'chased', 'monster', 'nightmare', 'afraid', 'scary', 'spider', 'snake', 'falling', 'trapped', 'attack'],
        'Achievement/Control': ['flying', 'win', 'success', 'control', 'driving', 'leading', 'summit', 'pass', 'exam', 'test'],
        'Vulnerability/Insecurity': ['naked', 'lost', 'teeth', 'falling', 'fail', 'exam', 'test', 'forgot', 'late'],
        'Transition/Change': ['death', 'baby', 'journey', 'road', 'door', 'key', 'moving', 'travel'],
        'Self/Identity': ['mirror', 'house', 'home', 'room', 'clothes', 'face', 'body'],
        'Desire/Need': ['food', 'money', 'sex', 'love', 'hug', 'kiss', 'water', 'drink']
    }
    emotion_dna, theme_dna = [], []
    emotion_str = dream_entry_series.get('emotional_tone', '{}')
    try: # Emotion DNA
        emotion_scores = json.loads(emotion_str) if isinstance(emotion_str, str) and emotion_str.strip().startswith('{') else {}
        if emotion_scores and all(k in emotion_scores for k in ['pos', 'neg', 'neu']):
             valid = {k: round(v * 100, 1) for k, v in {'Positive': emotion_scores.get('pos',0), 'Negative': emotion_scores.get('neg',0), 'Neutral': emotion_scores.get('neu',0)}.items()}
             emotion_dna = [{'label': k, 'value': v} for k, v in valid.items() if v > 0]
             if not emotion_dna: emotion_dna = [{'label': 'Neutral', 'value': 100.0}]
        else: emotion_dna = [{'label': 'Unknown', 'value': 100.0}]
    except: emotion_dna = [{'label': 'Error', 'value': 100.0}]

    try: # Theme DNA
        dream_text = dream_entry_series.get('dream_text', '').lower()
        if dream_text:
            theme_counts, total_keywords = {t: 0 for t in THEME_KEYWORDS}, 0
            words = set(dream_text.split()) # Simple split fallback
            if nlp:
                try: words = set(tok.lemma_ for tok in nlp(dream_text))
                except: pass # Use split if spacy fails
            for theme, keywords in THEME_KEYWORDS.items():
                count = len(words.intersection(set(keywords)))
                if count > 0: theme_counts[theme], total_keywords = count, total_keywords + count
            if total_keywords > 0:
                theme_dna = [{'label': t, 'value': round((c/total_keywords)*100, 1)} for t, c in theme_counts.items() if c > 0]
                theme_dna.sort(key=lambda x: x['value'], reverse=True)
            else: theme_dna = [{'label': 'Uncategorized', 'value': 100.0}]
        else: theme_dna = [{'label': 'Uncategorized', 'value': 100.0}]
    except: theme_dna = [{'label': 'Error', 'value': 100.0}]

    return {'emotions': emotion_dna, 'themes': theme_dna}

# --- Internal CSV Helpers ---
def _load_journal_internal(journal_file_path):
    required_columns = ['dream_id', 'user_id', 'dream_text', 'dream_date', 'created_at', 'updated_at', 'detected_type', 'emotional_tone', 'extracted_symbols']
    if not os.path.exists(journal_file_path): return pd.DataFrame(columns=required_columns)
    try:
        df = pd.read_csv(journal_file_path).fillna('')
        for col in required_columns:
            if col not in df.columns: df[col] = ''
        for col in ['dream_id', 'user_id', 'dream_text', 'dream_date', 'detected_type', 'emotional_tone', 'extracted_symbols']:
            if col in df.columns: df[col] = df[col].astype(str)
        return df
    except pd.errors.EmptyDataError: return pd.DataFrame(columns=required_columns)
    except Exception as e: print(f"Error reading journal: {e}"); return pd.DataFrame(columns=required_columns)

def _save_journal_internal(df, journal_file_path):
    if df is None: return False
    try:
        for col in ['emotional_tone', 'extracted_symbols']:
            if col in df.columns: df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x))
        df.fillna('', inplace=True)
        os.makedirs(os.path.dirname(journal_file_path), exist_ok=True)
        df.to_csv(journal_file_path, index=False)
        return True
    except Exception as e: print(f"Error saving journal: {e}"); return False

def _load_symbol_guide_internal(symbol_guide_file_path):
     required_columns = ['symbol_name', 'traditional_meaning', 'psychological_meaning']
     if not os.path.exists(symbol_guide_file_path): return pd.DataFrame(columns=required_columns)
     try:
         df = pd.read_csv(symbol_guide_file_path).fillna('')
         for col in required_columns:
             if col not in df.columns: df[col] = ''
         df['symbol_name'] = df['symbol_name'].astype(str)
         return df
     except pd.errors.EmptyDataError: return pd.DataFrame(columns=required_columns)
     except Exception as e: print(f"Error reading symbol guide: {e}"); return pd.DataFrame(columns=required_columns)

def _save_symbol_guide_internal(df, symbol_guide_file_path):
     if df is None: return False
     try:
         df.fillna('', inplace=True)
         os.makedirs(os.path.dirname(symbol_guide_file_path), exist_ok=True)
         df.to_csv(symbol_guide_file_path, index=False)
         return True
     except Exception as e: print(f"Error saving symbol guide: {e}"); return False

# --- NLP Analysis Functions ---
def detect_dream_type_service(text):
    if not isinstance(text, str): return "Unknown"
    tl = text.lower()
    if any(k in tl for k in ["nightmare", "scary", "terrifying", "afraid", "disturbing"]): return "Nightmare"
    if any(k in tl for k in ["lucid", "aware i was dreaming", "control the dream"]): return "Lucid"
    return "Normal"

def detect_emotional_tone_service(text):
    if not isinstance(text, str) or not text or analyzer is None: return {}
    try: return {k: float(v) for k, v in analyzer.polarity_scores(text).items()}
    except Exception as e: print(f"VADER Error: {e}"); return {}

def extract_symbols_service(text):
    if not isinstance(text, str) or not text: return []
    found = set()
    words = set(text.lower().split()) # Fallback
    if nlp:
        try: words = set(tok.lemma_ for tok in nlp(text.lower()))
        except Exception as e: print(f"spaCy Error: {e}")
    found.update(words.intersection(common_dream_symbols_set))
    return sorted(list(found))

def analyze_dream_text_service(dream_text):
    if not dream_text: return {'type': 'Unknown', 'emotion': {}, 'symbols': []}
    typ = detect_dream_type_service(dream_text)
    emo = detect_emotional_tone_service(dream_text)
    sym = extract_symbols_service(dream_text)
    print(f"Analyzed: T={typ}, E={emo.get('compound', 'N/A')}, S={len(sym)}")
    return {'type': typ, 'emotion': emo, 'symbols': sym}

# --- Initialization Services ---
def initialize_journal_service(journal_file_path):
    required_columns = ['dream_id', 'user_id', 'dream_text', 'dream_date', 'created_at', 'updated_at', 'detected_type', 'emotional_tone', 'extracted_symbols']
    if not os.path.exists(journal_file_path):
        print(f"Creating journal file: {journal_file_path}")
        _save_journal_internal(pd.DataFrame(columns=required_columns), journal_file_path)
    else: # Check/update columns
        try:
            df = pd.read_csv(journal_file_path)
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                print(f"Adding missing journal columns: {missing}")
                for col in missing: df[col] = '{}' if col == 'emotional_tone' else ('[]' if col == 'extracted_symbols' else '')
                _save_journal_internal(df, journal_file_path)
        except Exception as e: print(f"Error checking journal columns: {e}")

def initialize_symbol_guide_service(symbol_guide_file_path):
     required_columns = ['symbol_name', 'traditional_meaning', 'psychological_meaning']
     if not os.path.exists(symbol_guide_file_path):
         print(f"Creating symbol guide file: {symbol_guide_file_path}")
         _save_symbol_guide_internal(pd.DataFrame(columns=required_columns), symbol_guide_file_path)
         # TODO: Add pre-population logic here if desired

# --- CRUD and Search Services ---
def add_dream_service(user_id, dream_text, dream_date_str, journal_file_path):
    df = _load_journal_internal(journal_file_path)
    try: datetime.strptime(dream_date_str, '%Y-%m-%d')
    except ValueError: return None
    if not dream_text or not user_id: return None
    new_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    analysis = analyze_dream_text_service(dream_text)
    entry = pd.DataFrame([{'dream_id': new_id, 'user_id': user_id, 'dream_text': dream_text, 'dream_date': dream_date_str, 'created_at': now, 'updated_at': now, 'detected_type': str(analysis['type']), 'emotional_tone': json.dumps(analysis['emotion']), 'extracted_symbols': json.dumps(analysis['symbols'])}])
    if df.empty: df = pd.DataFrame(columns=entry.columns) # Ensure columns match if empty
    df = pd.concat([df, entry], ignore_index=True)
    return new_id if _save_journal_internal(df, journal_file_path) else None

def get_dreams_service(user_id, journal_file_path):
    df = _load_journal_internal(journal_file_path)
    if df is None: return None
    user_dreams = df[df['user_id'].astype(str) == str(user_id)].copy()
    return user_dreams.to_dict('records')

def get_dream_by_id_service(dream_id, journal_file_path):
     df = _load_journal_internal(journal_file_path)
     if df is None: return None
     dream = df[df['dream_id'].astype(str) == str(dream_id)]
     return dream.iloc[0].to_dict() if not dream.empty else None

def update_dream_service(dream_id, journal_file_path, new_text=None, new_date_str=None):
    df = _load_journal_internal(journal_file_path)
    if df is None: return False
    idx = df.index[df['dream_id'].astype(str) == str(dream_id)].tolist()
    if not idx: return False
    idx = idx[0]; updated, reanalyze = False, False
    if new_text is not None and new_text != df.loc[idx, 'dream_text']: df.loc[idx, 'dream_text'], updated, reanalyze = new_text, True, True
    if new_date_str is not None:
        try:
            datetime.strptime(new_date_str, '%Y-%m-%d')
            if new_date_str != df.loc[idx, 'dream_date']: df.loc[idx, 'dream_date'], updated = new_date_str, True
        except ValueError: pass
    if updated:
        df.loc[idx, 'updated_at'] = datetime.now().isoformat()
        if reanalyze:
            analysis = analyze_dream_text_service(df.loc[idx, 'dream_text'])
            df.loc[idx, 'detected_type'], df.loc[idx, 'emotional_tone'], df.loc[idx, 'extracted_symbols'] = str(analysis['type']), json.dumps(analysis['emotion']), json.dumps(analysis['symbols'])
        return _save_journal_internal(df, journal_file_path)
    return True # No update needed

def delete_dream_service(dream_id, journal_file_path):
    df = _load_journal_internal(journal_file_path)
    if df is None: return False
    initial_len = len(df)
    df = df[df['dream_id'].astype(str) != str(dream_id)]
    if len(df) == initial_len: return False # Not found
    return _save_journal_internal(df, journal_file_path)

def search_dreams_service(user_id, journal_file_path, search_term=None, start_date_str=None, end_date_str=None, filter_emotion=None, filter_symbol=None):
    df = _load_journal_internal(journal_file_path)
    if df is None: return None
    res = df[df['user_id'].astype(str) == str(user_id)].copy()
    if res.empty: return []
    res['primary_emotion'] = res['emotional_tone'].apply(get_primary_emotion) if 'emotional_tone' in res.columns else 'Unknown'
    try: # Date filter
        res['dt'] = pd.to_datetime(res['dream_date'], errors='coerce')
        res.dropna(subset=['dt'], inplace=True)
        if start_date_str: res = res[res['dt'] >= pd.to_datetime(start_date_str)]
        if end_date_str: res = res[res['dt'] <= pd.to_datetime(end_date_str)]
        res.drop(columns=['dt'], inplace=True)
    except: pass
    if search_term: res = res[res['dream_text'].astype(str).str.contains(search_term, case=False, na=False)]
    if filter_emotion: res = res[res['primary_emotion'] == filter_emotion]
    if filter_symbol:
        fs = filter_symbol.lower()
        def check_sym(s):
            try: return fs in (json.loads(s) if isinstance(s, str) and s.startswith('[') else [])
            except: return False
        res = res[res['extracted_symbols'].apply(check_sym)]
    return res.to_dict('records')

# --- Analysis & Enhancement Services ---
def get_symbol_details_service(symbol_name, symbol_guide_file_path, user_id=None, journal_file_path=None):
     """Gets symbol details, optionally adds user frequency."""
     guide_df = _load_symbol_guide_internal(symbol_guide_file_path)
     if guide_df is None: return None
     details_row = guide_df[guide_df['symbol_name'].astype(str) == symbol_name.lower()]
     if details_row.empty: return None
     details = details_row.iloc[0].to_dict()
     details['personal_frequency'], details['co_occurring_symbols'] = 0, {}

     if user_id and journal_file_path: # Calculate user stats
         user_dreams = get_dreams_service(user_id, journal_file_path)
         if user_dreams:
             count = 0
             co_counter = Counter()
             for dream in user_dreams:
                 try:
                     symbols = json.loads(dream.get('extracted_symbols','[]')) if isinstance(dream.get('extracted_symbols'), str) and dream.get('extracted_symbols').startswith('[') else []
                     if symbol_name.lower() in symbols:
                         count += 1
                         co_counter.update(s for s in symbols if s != symbol_name.lower())
                 except: continue
             details['personal_frequency'] = count
             details['co_occurring_symbols'] = dict(co_counter.most_common(5))
     return details

def calculate_dream_dna_service(dream_id, journal_file_path):
     dream_dict = get_dream_by_id_service(dream_id, journal_file_path)
     if not dream_dict: return None
     return _calculate_dream_dna_logic(pd.Series(dream_dict)) # Use helper

def generate_reflection_service(user_id, journal_file_path, time_period_days=30):
    # Simplified logic from Colab Phase 4
    dreams = search_dreams_service(user_id, journal_file_path, start_date_str=(datetime.now() - timedelta(days=time_period_days)).strftime('%Y-%m-%d'))
    if dreams is None or not dreams: return ["No recent dreams found."]
    reflections = []
    types = Counter(d.get('detected_type') for d in dreams)
    emotions = Counter(d.get('primary_emotion') for d in dreams) # Assumes primary_emotion added by search
    symbols = Counter(s for d in dreams for s in (json.loads(d.get('extracted_symbols','[]')) if isinstance(d.get('extracted_symbols'), str) and d.get('extracted_symbols').startswith('[') else []))
    if types['Nightmare'] >= max(1, len(dreams)*0.2): reflections.append("Nightmares noted recently.")
    if emotions['Negative'] >= max(1, len(dreams)*0.3): reflections.append("Negative emotions seem common recently.")
    if symbols and symbols.most_common(1):
        mc_sym, freq = symbols.most_common(1)[0]
        if freq > 1 and freq >= len(dreams)*0.15: reflections.append(f"Symbol '{mc_sym}' recurring recently ({freq} times).")
    return reflections if reflections else ["No strong patterns detected."]

def get_emotion_timeline_data_service(user_id, journal_file_path, start_date_str=None, end_date_str=None):
    dreams = search_dreams_service(user_id, journal_file_path, start_date_str=start_date_str, end_date_str=end_date_str)
    if dreams is None: return None
    timeline = []
    for d in dreams:
        compound = 0.0
        try: compound = json.loads(d.get('emotional_tone','{}')).get('compound',0.0) if isinstance(d.get('emotional_tone'), str) and d.get('emotional_tone').startswith('{') else 0.0
        except: pass
        timeline.append({'date': d.get('dream_date'), 'emotion': d.get('primary_emotion', 'Unknown'), 'compound': round(compound, 3), 'dream_id': d.get('dream_id')})
    timeline.sort(key=lambda x: x['date'])
    return timeline

def dreamify_text_service(dream_text, style='poem'):
    if not dream_text: return "Empty dream..."
    analysis = analyze_dream_text_service(dream_text) # Re-analyze for symbols/emotion
    symbols = analysis.get('symbols', [])
    primary_emotion = get_primary_emotion(json.dumps(analysis.get('emotion', {})))
    feat = random.sample(symbols, k=min(len(symbols), 2))
    if style == 'poem':
        l1 = f"A dream of {primary_emotion.lower()} feeling,"
        l2 = f"Where '{feat[0] if feat else 'shadows'}' dance, secrets revealing."
        l3 = f"Perhaps '{feat[1] if len(feat)>1 else 'silence'}' adds to the stealing."
        return "\n".join([l1, l2, l3])
    elif style == 'noir':
        return f"The subconscious threw a {primary_emotion.lower()} curveball. Felt like '{feat[0] if feat else 'emptiness'}'. Woke up needing answers."
    return f"Original: {dream_text}"

def get_recommendations_service(dream_id, journal_file_path):
    dream = get_dream_by_id_service(dream_id, journal_file_path)
    if not dream: return ["Dream not found."]
    emotion = get_primary_emotion(dream.get('emotional_tone', '{}'))
    if emotion == "Negative": return ["Consider journaling.", "Try calming meditation."]
    if emotion == "Positive": return ["Reflect on the positive feelings.", "Embrace the energy."]
    return ["Reflect on symbols and events."]

def export_journal_csv_service(user_id, journal_file_path, output_filename):
    df = _load_journal_internal(journal_file_path)
    if df is None: return False
    user_dreams = df[df['user_id'].astype(str) == str(user_id)].copy()
    if user_dreams.empty: return False
    cols = [c for c in ['dream_id', 'user_id', 'dream_date', 'dream_text', 'detected_type', 'emotional_tone', 'extracted_symbols', 'created_at', 'updated_at'] if c in user_dreams.columns]
    try:
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        user_dreams[cols].to_csv(output_filename, index=False)
        return True
    except Exception as e: print(f"Error exporting CSV: {e}"); return False

