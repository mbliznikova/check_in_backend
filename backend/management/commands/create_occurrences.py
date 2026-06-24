from django.core.management.base import BaseCommand
from backend.tasks import create_class_occurrences


class Command(BaseCommand):
    help = "Create class occurrences for the upcoming week"

    def handle(self, *args, **kwargs):
        create_class_occurrences()
        self.stdout.write("Done")
