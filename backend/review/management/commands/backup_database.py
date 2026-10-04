from pathlib import Path
from contextlib import closing
import sqlite3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a consistent SQLite backup at a NEW path."

    def add_arguments(self, parser):
        parser.add_argument("destination")

    def handle(self, *args, **options):
        target = Path(options["destination"]).resolve()
        source = Path(settings.DATABASES["default"]["NAME"]).resolve()
        if target.exists() or target == source:
            raise CommandError("Choose a new destination; existing files are never overwritten.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin, closing(sqlite3.connect(target)) as backup:
            origin.backup(backup)
        self.stdout.write(f"Backup created: {target}")
