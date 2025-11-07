from django.core.management.base import BaseCommand
from billing.models import Client

class Command(BaseCommand):
    help = "Crea un cliente de ejemplo para pruebas"

    def handle(self, *args, **kwargs):
        obj, created = Client.objects.get_or_create(name="Cliente Demo", email="cliente@example.com")
        self.stdout.write(self.style.SUCCESS(f"Cliente Demo listo (id={obj.id})"))
