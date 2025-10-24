def inject_settings_factory(users, is_logged_in):
    def inject_settings():
        from flask import session
        try:
            if is_logged_in(session):
                uid = session['user_id']
                try:
                    if hasattr(users, 'ensure_user_settings_row'):
                        users.ensure_user_settings_row(uid)
                    if hasattr(users, 'hydrate_user_settings_from_legacy'):
                        users.hydrate_user_settings_from_legacy(uid)
                except Exception:
                    pass
                settings_data = users.get_user_settings(uid)
                return {'settings': settings_data}
        except Exception:
            pass
        return {'settings': None}
    return inject_settings
