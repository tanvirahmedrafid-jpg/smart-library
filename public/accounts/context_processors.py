def user_profile_context(request):
    if not request.user.is_authenticated:
        return {
            'member_profile': None,
            'is_admin_user': False,
            'is_librarian_or_admin': False,
            'is_student_user': False
        }
    
    profile = getattr(request.user, 'member_profile', None)
    is_admin = request.user.is_superuser or bool(profile and profile.is_admin)
    is_lib = is_admin or request.user.is_staff or bool(profile and profile.is_librarian)
    is_stu = (profile and profile.is_student) or (not is_lib and not is_admin)

    return {
        'member_profile': profile,
        'is_admin_user': is_admin,
        'is_librarian_or_admin': is_lib,
        'is_student_user': is_stu,
    }
