import getpass
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an ordinary local analyst; never change an existing account."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="analyst")

    def handle(self, *args, **options):
        name = options["username"]
        if get_user_model().objects.filter(username=name).exists():
            self.stdout.write(f"Account {name} already exists; unchanged.")
            return
        password = os.environ.get("TRACEREVIEW_ANALYST_PASSWORD")
        if not password:
            password = getpass.getpass(f"New password for {name}: ")
            if password != getpass.getpass("Repeat password: "):
                raise CommandError("Passwords do not match.")
        user = get_user_model()(username=name, is_staff=False, is_superuser=False)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        user.set_password(password)
        user.save()
        self.stdout.write(f"Created local analyst {name}.")
