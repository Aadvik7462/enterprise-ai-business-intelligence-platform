from flask import Blueprint, jsonify, request, session
from services.workspace_service import get_saved_dashboard, get_workspace, save_dashboard

workspace_detail_bp = Blueprint('workspace_detail', __name__)

def _owner_id():
    user = session.get('user')
    if user is None:
        return None
    if isinstance(user, dict):
        return str(user.get('id') or user.get('email') or user.get('username') or user.get('name') or '').strip() or None
    return str(user).strip() or None

@workspace_detail_bp.route('/api/dashboards/<int:dashboard_id>/duplicate', methods=['POST'])
def duplicate_dashboard_route(dashboard_id):
    owner_id = _owner_id()
    if owner_id is None:
        return jsonify({'success': False, 'message': 'Your session has expired. Please log in again.'}), 401

    source = get_saved_dashboard(dashboard_id=dashboard_id, owner_id=owner_id)
    if source is None:
        return jsonify({'success': False, 'message': 'Saved dashboard not found.'}), 404

    data = request.get_json(silent=True) or {}
    try:
        workspace_id = int(data.get('workspace_id', source['workspace_id']))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'workspace_id must be a valid number.'}), 400

    if get_workspace(workspace_id=workspace_id, owner_id=owner_id) is None:
        return jsonify({'success': False, 'message': 'Target workspace not found.'}), 404

    name = str(data.get('name') or f"{source['name']} Copy").strip()

    try:
        dashboard = save_dashboard(
            workspace_id=workspace_id,
            owner_id=owner_id,
            name=name,
            filename=source['filename'],
            dashboard_type=source['dashboard_type'],
            description=source.get('description', ''),
            dashboard_state=source.get('dashboard_state', {}),
            thumbnail=source.get('thumbnail', '')
        )
        return jsonify({'success': True, 'message': 'Dashboard duplicated successfully.', 'dashboard': dashboard}), 201
    except Exception as error:
        return jsonify({'success': False, 'message': f'Dashboard duplication failed: {error}'}), 500
