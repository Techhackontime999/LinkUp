import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')
sys.path.insert(0, r'C:\Users\ADMIN\Downloads\Project\LinkUp\linkup')
import django
django.setup()

from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from users.forms import ProfileUpdateForm
from users.models import User, Profile
from django.forms import FileField
from io import BytesIO
from PIL import Image

img = Image.new('RGB', (100, 100), color='red')
buf = BytesIO()
img.save(buf, 'JPEG')
buf.seek(0)

test_file = InMemoryUploadedFile(
    buf, 'avatar', 'test.jpg', 'image/jpeg', buf.getbuffer().nbytes, None
)
print('File type:', type(test_file).__name__)
print('Is UploadedFile:', isinstance(test_file, UploadedFile))

user = User.objects.first()
profile = user.profile
print('Profile avatar:', repr(profile.avatar))
print('Avatar type:', type(profile.avatar).__name__)

original_clean = FileField.clean
def debug_clean(self, data, initial=None):
    print('=== FileField.clean ===')
    dtype = type(data).__name__ if data is not None else None
    itype = type(initial).__name__ if initial is not None else None
    print('  data type:', dtype)
    print('  initial type:', itype)
    if data is not None:
        print('  isinstance UploadedFile:', isinstance(data, UploadedFile))
    result = original_clean(self, data, initial)
    rtype = type(result).__name__ if result is not None else None
    print('  result type:', rtype)
    if result is not None:
        print('  isinstance UploadedFile:', isinstance(result, UploadedFile))
    return result

FileField.clean = debug_clean

form = ProfileUpdateForm(
    data={'headline': '', 'bio': '', 'location': ''},
    files={'avatar': test_file},
    instance=profile
)
print('\n=== Calling is_valid() ===')
print('Result:', form.is_valid())
if form.errors:
    for field, errors in form.errors.items():
        for e in errors:
            print('  %s: %s' % (field, e))
