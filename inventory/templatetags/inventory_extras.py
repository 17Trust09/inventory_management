from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

register = template.Library()

@register.simple_tag(takes_context=True)
def borrowed_info(context, item):
    borrowed = item.borrowed_items.filter(returned=False)
    if not borrowed.exists():
        return "-"

    request = context['request']
    csrf_token = f"<input type='hidden' name='csrfmiddlewaretoken' value='{request.META.get('CSRF_COOKIE', '')}'>"
    today = timezone.now().date()

    result = ""

    for b in borrowed:
        url = reverse('return-item', args=[b.id])
        info = f"<strong>👤 {b.borrower}</strong> ({b.date_borrowed.date()})<br>"
        info += f"🔢 {b.quantity_borrowed} Stück"

        # Rückgabedatum farbig formatieren
        if b.return_date:
            if b.return_date < today:
                color = "red"
            elif b.return_date == today:
                color = "orange"
            else:
                color = "lightgreen"
            info += f"<br>🕓 Rückgabe bis: <span style='color:{color}; font-weight: bold;'>{b.return_date}</span>"

        info += (
            f"<form method='post' action='{url}' style='margin-top: 5px;'>"
            f"{csrf_token}"
            f"<button type='submit' class='btn btn-sm btn-warning mt-1'>🔁 Zurückgeben</button>"
            f"</form>"
            f"<hr style='margin: 6px 0;'>"
        )

        result += info

    return format_html(result)
