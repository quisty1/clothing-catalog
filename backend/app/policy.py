from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    kind: str
    title: str | None = None


def decide_message(*, text, caption, has_photo, is_album, is_admin, awaiting_photo=False):
    text = (text or '').strip()
    command = text.split(maxsplit=1)[0].split('@')[0] if text else ''
    if command == '/start':
        return Decision('welcome')
    if command == '/create_product' or text == 'Создать товар':
        return Decision('instructions' if is_admin else 'forbidden')
    if not is_admin:
        return Decision('welcome')
    if not has_photo and not is_album and not caption and not awaiting_photo:
        return Decision('welcome')
    title = (caption or '').strip()
    if is_album or not has_photo or not 1 <= len(title) <= 255:
        return Decision('invalid')
    return Decision('create', title)
