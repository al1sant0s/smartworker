from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from checklist.models import CheckList


class Command(BaseCommand):
    help = "Cria um checklist pendente do mês para cada empreendimento ativo que ainda não tem um."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            help="Mês de referência no formato AAAA-MM (padrão: mês atual)",
        )

    def handle(self, *args, **options):
        if options["month"]:
            try:
                year, month = map(int, options["month"].split("-"))
                reference_month = date(year, month, 1)
            except ValueError:
                raise CommandError("Use o formato AAAA-MM, ex: 2026-10")
        else:
            reference_month = timezone.localdate().replace(day=1)

        created = CheckList.objects.create_for_month(reference_month)
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(created)} checklist(s) criado(s) para {reference_month:%m/%Y}."
            )
        )
