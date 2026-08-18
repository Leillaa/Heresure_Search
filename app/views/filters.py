"""
[EN]
Jinja filters — presentation-only formatting of model fields. Registered on the
app in create_app(), used from the templates.

[RU]
Jinja-фильтры — чисто презентационное форматирование полей модели.
Регистрируются на приложении в create_app(), используются из шаблонов.
"""


def to_tel_href(phone: str) -> str:
    """Builds a tel: link from a phone number so that tapping it on mobile
    offers to place a call.

    Готовит tel: ссылку из телефона, чтобы на мобильном по тапу
    предлагалось позвонить."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        digits = "1" + digits  # prepend the US country code / добавляем код страны США
    return f"tel:+{digits}"
