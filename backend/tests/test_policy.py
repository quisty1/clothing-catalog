from app.policy import decide_message


def message(**overrides):
    return {'text': None, 'caption': None, 'has_photo': False,
            'is_album': False, 'is_admin': False, **overrides}


def test_start_and_regular_user_cannot_create_products():
    assert decide_message(**message(text='/start')).kind == 'welcome'
    assert decide_message(**message(has_photo=True, caption='Пальто')).kind == 'welcome'
    assert decide_message(**message(text='/create_product')).kind == 'forbidden'


def test_admin_upload_is_self_contained_and_normalizes_title():
    action = decide_message(**message(is_admin=True, has_photo=True, caption='  Пальто  '))
    assert action.kind == 'create'
    assert action.title == 'Пальто'


def test_admin_command_prompts_for_single_photo_and_caption():
    for text in ['/create_product', 'Создать товар']:
        assert decide_message(**message(is_admin=True, text=text)).kind == 'instructions'


def test_rejects_missing_title_album_and_title_without_photo():
    for fields in [dict(has_photo=True), dict(has_photo=True, caption='  '),
                   dict(has_photo=True, caption='Платье', is_album=True),
                   dict(text='Платье', awaiting_photo=True)]:
        assert decide_message(**message(is_admin=True, **fields)).kind == 'invalid'


def test_title_length_boundary_and_start_command_with_payload():
    assert decide_message(**message(is_admin=True, has_photo=True, caption='я'*255)).kind == 'create'
    assert decide_message(**message(is_admin=True, has_photo=True, caption='я'*256)).kind == 'invalid'
    assert decide_message(**message(is_admin=True, text='/start referral')).kind == 'welcome'


def test_admin_regular_text_welcomes_until_create_flow_is_started():
    assert decide_message(**message(is_admin=True,text='Привет')).kind == 'welcome'
    assert decide_message(**message(is_admin=True,text='Пальто',awaiting_photo=True)).kind == 'invalid'
