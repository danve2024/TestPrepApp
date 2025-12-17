def inject_settings_factory(users, is_logged_in, calculate_score_func=None):
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
                
                # Update session with latest scores for header display
                try:
                    progress_data = users.get_user_progress(uid)
                    if progress_data:
                        # Use calculated score if function provided, otherwise use stored
                        if calculate_score_func:
                            try:
                                score_data = calculate_score_func(uid)
                                ebrw_score = score_data['score']
                                math_score = 800  # Always 800 for now
                                total_score = ebrw_score + math_score
                                
                                # Update session
                                session['total_score'] = total_score
                                session['ebrw_score'] = ebrw_score
                                session['math_score'] = math_score
                            except Exception:
                                # Fallback to stored progress data
                                session['total_score'] = progress_data.get('total_score', 1600)
                                session['ebrw_score'] = progress_data.get('ebrw_score', 800)
                                session['math_score'] = progress_data.get('math_score', 800)
                        else:
                            # Use stored progress data
                            session['total_score'] = progress_data.get('total_score', 1600)
                            session['ebrw_score'] = progress_data.get('ebrw_score', 800)
                            session['math_score'] = progress_data.get('math_score', 800)
                except Exception as e:
                    # Set defaults on error
                    session['total_score'] = session.get('total_score', 1600)
                    session['ebrw_score'] = session.get('ebrw_score', 800)
                    session['math_score'] = session.get('math_score', 800)
                
                return {'settings': settings_data}
        except Exception:
            pass
        return {'settings': None}
    return inject_settings
