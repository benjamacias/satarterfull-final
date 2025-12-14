from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea un usuario admin inicial y asegura el grupo 'admin'"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        admin_group, _ = Group.objects.get_or_create(name="admin")

        admin_email = "admin@example.com"
        admin_password = "Admin123!"

        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={"is_staff": True, "is_superuser": True},
        )

        if created:
            admin_user.set_password(admin_password)
            self.stdout.write(self.style.SUCCESS(f"Usuario admin creado: {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Usuario admin ya existía: {admin_email}"))

        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_user.groups.add(admin_group)
        self.stdout.write(self.style.SUCCESS("Grupo 'admin' listo y usuario asignado"))
        self.stdout.write(self.style.SUCCESS(f"Credenciales: {admin_email} / {admin_password}"))
