""" Utility funtions for enrollments app """


def get_active_curriculum(program_data):
    """
    Given a JSON dict containing data for a program from Course Discovery,
    extract the first active curriculum, or None if no such curriculum exists.
    """
    try:
        return next(
            c for c in program_data.get('curricula', [])
            if c.get('is_active')
        )
    except StopIteration:
        return None
