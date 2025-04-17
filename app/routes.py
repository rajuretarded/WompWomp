# app/routes.py
from flask import Blueprint, request, jsonify, current_app, send_file
import os
from datetime import datetime

# Import all necessary service functions
from .services import (
    add_dream_service,
    get_dreams_service,
    get_dream_by_id_service,
    update_dream_service,
    delete_dream_service,
    search_dreams_service,
    get_symbol_details_service,
    calculate_dream_dna_service,
    generate_reflection_service,
    get_emotion_timeline_data_service,
    dreamify_text_service,
    get_recommendations_service,
    export_journal_csv_service
    # add_symbol_meaning_service # Add if implemented
)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# === Helpers ===
def _get_journal_path():
    return os.path.join(current_app.config['DATA_DIRECTORY'], 'dream_journal.csv')

def _get_symbol_guide_path():
    return os.path.join(current_app.config['DATA_DIRECTORY'], 'symbol_guide.csv')

# === Status ===
@api_bp.route('/status', methods=['GET'])
def api_status():
    return jsonify({"status": "OK", "message": "Dream Decoder API is running"})

# === Dreams CRUD & Search ===
@api_bp.route('/dreams', methods=['POST'])
def handle_add_dream():
    data = request.get_json();
    if not data: return jsonify({"error": "Invalid JSON"}), 400
    uid, txt, date = data.get('user_id'), data.get('dream_text'), data.get('dream_date')
    if not all([uid, txt, date]): return jsonify({"error": "Missing fields"}), 400
    new_id = add_dream_service(uid, txt, date, _get_journal_path())
    if new_id: return jsonify({"message": "Dream added", "dream_id": new_id}), 201
    else: return jsonify({"error": "Failed to add dream"}), 500

@api_bp.route('/dreams', methods=['GET'])
def handle_get_dreams_or_search():
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "Missing user_id param"}), 400
    # Check for search/filter parameters
    params = {k: v for k, v in request.args.items() if k != 'user_id' and v}
    if params: # Use search if other params exist
        dreams = search_dreams_service(user_id, _get_journal_path(), **params)
    else: # Get all otherwise
        dreams = get_dreams_service(user_id, _get_journal_path())
    if dreams is None: return jsonify({"error": "Failed to retrieve dreams"}), 500
    return jsonify(dreams), 200

@api_bp.route('/dreams/<string:dream_id>', methods=['GET'])
def handle_get_dream_by_id(dream_id):
    dream = get_dream_by_id_service(dream_id, _get_journal_path())
    if dream: return jsonify(dream), 200
    else: return jsonify({"error": "Dream not found"}), 404

@api_bp.route('/dreams/<string:dream_id>', methods=['PUT'])
def handle_update_dream(dream_id):
    data = request.get_json();
    if not data: return jsonify({"error": "Invalid JSON"}), 400
    txt, date = data.get('dream_text'), data.get('dream_date')
    if txt is None and date is None: return jsonify({"error": "No update fields"}), 400
    success = update_dream_service(dream_id, _get_journal_path(), new_text=txt, new_date_str=date)
    if success:
        updated = get_dream_by_id_service(dream_id, _get_journal_path())
        return jsonify(updated or {"message": "Update ok, retrieval failed"}), 200
    else:
        if get_dream_by_id_service(dream_id, _get_journal_path()) is None: return jsonify({"error": "Dream not found"}), 404
        else: return jsonify({"error": "Update failed"}), 500

@api_bp.route('/dreams/<string:dream_id>', methods=['DELETE'])
def handle_delete_dream(dream_id):
    success = delete_dream_service(dream_id, _get_journal_path())
    if success: return jsonify({"message": f"Dream '{dream_id}' deleted"}), 200
    else:
        if get_dream_by_id_service(dream_id, _get_journal_path()) is None: return jsonify({"error": "Dream not found"}), 404
        else: return jsonify({"error": "Delete failed"}), 500

# === Symbol Guide ===
@api_bp.route('/symbols/<string:symbol_name>', methods=['GET'])
def handle_get_symbol(symbol_name):
    user_id = request.args.get('user_id') # Optional user context
    details = get_symbol_details_service(symbol_name, _get_symbol_guide_path(), user_id, _get_journal_path() if user_id else None)
    if details: return jsonify(details), 200
    else: return jsonify({"error": f"Symbol '{symbol_name}' not found"}), 404

# === Analysis & Features ===
@api_bp.route('/dreams/<string:dream_id>/dna', methods=['GET'])
def handle_get_dream_dna(dream_id):
    dna = calculate_dream_dna_service(dream_id, _get_journal_path())
    if dna: return jsonify(dna), 200
    else:
        if get_dream_by_id_service(dream_id, _get_journal_path()) is None: return jsonify({"error": "Dream not found"}), 404
        else: return jsonify({"error": "Could not calculate DNA"}), 500

@api_bp.route('/reflections', methods=['GET'])
def handle_get_reflections():
    user_id = request.args.get('user_id')
    days = request.args.get('days', 30, type=int) # Default 30 days
    if not user_id: return jsonify({"error": "Missing user_id param"}), 400
    reflections = generate_reflection_service(user_id, _get_journal_path(), days)
    if reflections is None: return jsonify({"error": "Failed to generate"}), 500
    return jsonify({"reflections": reflections}), 200

@api_bp.route('/timeline', methods=['GET'])
def handle_get_timeline():
    user_id = request.args.get('user_id')
    start, end = request.args.get('start_date'), request.args.get('end_date')
    if not user_id: return jsonify({"error": "Missing user_id param"}), 400
    timeline = get_emotion_timeline_data_service(user_id, _get_journal_path(), start, end)
    if timeline is None: return jsonify({"error": "Failed to get timeline"}), 500
    return jsonify(timeline), 200

@api_bp.route('/dreams/<string:dream_id>/dreamify', methods=['POST'])
def handle_dreamify(dream_id):
    style = request.args.get('style', 'poem')
    dream = get_dream_by_id_service(dream_id, _get_journal_path())
    if not dream: return jsonify({"error": "Dream not found"}), 404
    result = dreamify_text_service(dream.get('dream_text',''), style)
    return jsonify({"dream_id": dream_id, "style": style, "result": result}), 200

@api_bp.route('/dreams/<string:dream_id>/recommendations', methods=['GET'])
def handle_get_recommendations(dream_id):
    recs = get_recommendations_service(dream_id, _get_journal_path())
    if recs and recs[0] == "Dream not found.": return jsonify({"error": "Dream not found"}), 404
    return jsonify({"dream_id": dream_id, "recommendations": recs}), 200

# === Utility ===
@api_bp.route('/export', methods=['GET'])
def handle_export():
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "Missing user_id param"}), 400
    export_dir = os.path.join(current_app.config['DATA_DIRECTORY'], 'temp_exports')
    fname = f"{user_id}_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    output_path = os.path.join(export_dir, fname)
    success = export_journal_csv_service(user_id, _get_journal_path(), output_path)
    if success:
        try: return send_file(output_path, as_attachment=True, download_name=f"{user_id}_journal.csv")
        except Exception as e: return jsonify({"error": f"Export created but failed to send: {e}"}), 500
    else: return jsonify({"error": "Failed to export journal (maybe no dreams?)"}), 500
