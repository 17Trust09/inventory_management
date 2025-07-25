from .models import GlobalSettings

def get_qr_base_url():
    try:
        return GlobalSettings.objects.first().qr_base_url
    except:
        return 'http://127.0.0.1:8000'  # Fallback
