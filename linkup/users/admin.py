from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, Experience, Education

admin.site.register(User, UserAdmin)
admin.site.register(Profile)
admin.site.register(Experience)
admin.site.register(Education)
