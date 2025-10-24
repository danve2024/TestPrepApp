from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session


def create_settings_blueprint(users, is_logged_in):
    bp = Blueprint('settings_bp', __name__)

    @bp.route('/settings', methods=['GET', 'POST'])
    def settings():
        if is_logged_in(session):
            user_id = session['user_id']
            username = users.get_username_by_user_id(user_id)

            if request.method == 'POST':
                try:
                    if hasattr(users, 'ensure_user_settings_row'):
                        users.ensure_user_settings_row(user_id)
                except Exception:
                    pass
                dark_mode = request.form.get('dark_mode') == 'on'
                sounds = request.form.get('sounds') == 'on'
                haptics = request.form.get('haptics') == 'on'
                friends = request.form.get('friends') == 'on'
                notifications = request.form.get('notifications') == 'on'
                emails = request.form.get('emails') == 'on'
                productivity_mode = request.form.get('productivity_mode') == 'on'
                week_start_day = request.form.get('week_start_day') or 'monday'
                date_format = request.form.get('date_format') or 'DD/MM/YYYY'
                try:
                    font_scale_pct = int(request.form.get('font_scale_pct') or 100)
                except Exception:
                    font_scale_pct = 100

                users.update_user_settings(user_id, 'DarkMode', dark_mode)
                users.update_user_settings(user_id, 'Sounds', sounds)
                users.update_user_settings(user_id, 'Haptics', haptics)
                users.update_user_settings(user_id, 'Friends', friends)
                users.update_user_settings(user_id, 'Notifications', notifications)
                users.update_user_settings(user_id, 'Emails', emails)
                users.update_user_settings(user_id, 'ProductivityMode', productivity_mode)
                users.update_user_settings(user_id, 'WeekStartDay', week_start_day)
                users.update_user_settings(user_id, 'DateFormat', date_format)
                users.update_user_settings(user_id, 'FontScalePct', font_scale_pct)

                if username and hasattr(users, 'update_user_settings_by_username'):
                    users.update_user_settings_by_username(username, {
                        'dark_mode': dark_mode,
                        'productivity_mode': productivity_mode,
                        'sounds': sounds,
                        'haptics': haptics,
                        'friends': friends,
                        'notifications': notifications,
                        'emails': emails,
                    })

                flash('Settings updated successfully!', 'success')
                return redirect(url_for('settings_bp.settings'))

            settings_data = users.get_user_settings(user_id)
            profile_data = users.get_user_profile(user_id)

            return render_template('settings.html', settings=settings_data, profile=profile_data)
        return redirect('/login')

    @bp.route('/api/settings', methods=['POST'])
    def api_update_settings():
        if not is_logged_in(session):
            return jsonify({'ok': False, 'error': 'unauthorized'}), 401
        payload = request.get_json(silent=True) or {}
        key = payload.get('key')
        value = payload.get('value')
        if not key:
            return jsonify({'ok': False, 'error': 'missing key'}), 400
        uid = session['user_id']
        username = users.get_username_by_user_id(uid)
        user_settings_colmap = {
            'dark_mode': 'DarkMode',
            'sounds': 'Sounds',
            'haptics': 'Haptics',
            'friends': 'Friends',
            'notifications': 'Notifications',
            'emails': 'Emails',
            'productivity_mode': 'ProductivityMode',
            'week_start_day': 'WeekStartDay',
            'date_format': 'DateFormat',
            'font_scale_pct': 'FontScalePct',
        }
        col = user_settings_colmap.get(key)
        if not col:
            return jsonify({'ok': False, 'error': 'invalid key'}), 400
        try:
            users.update_user_settings(uid, col, value)
            if username and hasattr(users, 'update_user_settings_by_username') and key in ['dark_mode', 'sounds', 'haptics', 'friends', 'notifications', 'emails', 'productivity_mode']:
                users.update_user_settings_by_username(username, {key: bool(value)})
            return jsonify({'ok': True})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    return bp
