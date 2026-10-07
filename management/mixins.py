import re
from functools import reduce
from operator import or_

from django.db.models import Q


class SearchMixin:
    """Busca por texto (?q=) em ListViews, no estilo do search_fields do admin.

    Cada palavra digitada precisa aparecer em pelo menos um dos campos
    (icontains). Campos guardados só com dígitos (CNPJ, CEP, telefone) ficam em
    digit_search_fields e são comparados com a palavra sem pontuação, então
    "11.222.333" encontra o CNPJ "11222333000181".
    """

    search_fields = []
    digit_search_fields = []

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        for term in self.get_search_query().split():
            conditions = [Q(**{f"{field}__icontains": term}) for field in self.search_fields]
            digits = re.sub(r"\D", "", term)
            if digits:
                conditions += [
                    Q(**{f"{field}__icontains": digits}) for field in self.digit_search_fields
                ]
            queryset = queryset.filter(reduce(or_, conditions))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.get_search_query()
        return context
