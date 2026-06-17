from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import AlunoProfile, ProfessorProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    model = User
    list_display = ('email', 'nome_completo', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'nome_completo')
    ordering = ('email',)

    fieldsets = (
        ('Acesso', {'fields': ('email', 'password')}),
        ('Perfil', {'fields': ('nome_completo', 'avatar', 'role')}),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Datas importantes',
            {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')},
        ),
    )
    add_fieldsets = (
        (
            'Nova conta',
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'nome_completo',
                    'role',
                    'password1',
                    'password2',
                ),
            },
        ),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')


@admin.register(ProfessorProfile)
class ProfessorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'seed_registration', 'updated_at')
    search_fields = (
        'user__email',
        'user__nome_completo',
        'seed_registration',
        'disciplines',
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AlunoProfile)
class AlunoProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school_registration', 'grade', 'updated_at')
    search_fields = (
        'user__email',
        'user__nome_completo',
        'school_registration',
        'grade',
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
