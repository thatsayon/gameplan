from django.contrib.auth import get_user_model

User = get_user_model()

def generate_unique_username(email):
    base_username = email.split("@")[0]
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username