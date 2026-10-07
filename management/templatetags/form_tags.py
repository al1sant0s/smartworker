from django import template

register = template.Library()


@register.filter
def bootstrap(field):
    """Renderiza o widget do campo com as classes de formulário do Bootstrap."""
    widget_type = field.widget_type
    if widget_type in ("checkbox", "radioselect", "checkboxselectmultiple"):
        css = "form-check-input"
    elif widget_type in ("select", "selectmultiple"):
        css = "form-select"
    else:
        css = "form-control"
    if field.errors:
        css += " is-invalid"
    existing = field.field.widget.attrs.get("class", "")
    return field.as_widget(attrs={"class": f"{existing} {css}".strip()})
