from users.models import PasswordResetOTP
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
import os
import django
import sys

# ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


User = get_user_model()
api = APIClient()

u = User.objects.first()
print('first_user_email=', getattr(u, 'email', None))
if u:
    resp = api.post('/api/auth/password-reset/',
                    {'email': u.email}, format='json')
    print('resp_known:', resp.status_code, resp.content)
    print('otp_count_known=', PasswordResetOTP.objects.filter(
        user=u, used_at__isnull=True).count())

resp2 = api.post('/api/auth/password-reset/',
                 {'email': 'noone@example.com'}, format='json')
print('resp_unknown:', resp2.status_code, resp2.content)
