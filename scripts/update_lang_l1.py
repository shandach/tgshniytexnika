import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # show_branches
    content = re.sub(
        r'(@router\.message\(F\.text\.in_\(get_text_variants\("btn_l1_branches"\)\), IsReviewerL1\(\)\)\n@router\.callback_query\(F\.data == "l1_branches", IsReviewerL1\(\)\)\nasync def show_branches\(event)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"✅ Нет новых заявок ни в одном филиале\."', r'_("l1_branches_empty", lang)', content)
    content = re.sub(r'get_reviewer_l1_menu_kb\("branch"\)', r'get_reviewer_l1_menu_kb("branch", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ К очереди"', r'InlineKeyboardButton(text=_("btn_back_queue", lang)', content)

    # show_branch_requests
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_branch_"\), IsReviewerL1\(\)\)\nasync def show_branch_requests\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"✅ Все заявки этого филиала обработаны!"', r'_("l1_branch_done", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ К филиалам"', r'InlineKeyboardButton(text=_("btn_back_branches", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="🔍 Разобрать по одной"', r'InlineKeyboardButton(text=_("btn_l1_detail", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="✅ Одобрить всё"', r'InlineKeyboardButton(text=_("btn_approve_all", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="❌ Отклонить всё"', r'InlineKeyboardButton(text=_("btn_reject_all", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ Назад к филиалам"', r'InlineKeyboardButton(text=_("btn_back_branches", lang)', content)

    # _show_compact_card signature and body
    content = re.sub(
        r'(async def _show_compact_card\(callback: CallbackQuery, sorted_reqs, idx: int, session: AsyncSession, back_cb: str = "l1_back_queue")(\):)',
        r'\1, lang: str = "uz"\2',
        content
    )
    content = re.sub(r'"✅ Все заявки просмотрены!"', r'_("l1_all_viewed", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ Назад"', r'InlineKeyboardButton(text=_("btn_nav_prev", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="✅ Одобрить"', r'InlineKeyboardButton(text=_("btn_approve", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="❌ Отказать"', r'InlineKeyboardButton(text=_("btn_reject", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="▶ Следующая"', r'InlineKeyboardButton(text=_("btn_nav_next", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ К списку"', r'InlineKeyboardButton(text=_("btn_back_list", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="◀ К филиалу"', r'InlineKeyboardButton(text=_("btn_back_branch", lang)', content)

    # Calls to _show_compact_card need lang
    # I will regex replace `_show_compact_card(callback, sorted_reqs, 0, session)` with `_show_compact_card(callback, sorted_reqs, 0, session, lang=lang)`
    # Or just `_show_compact_card(callback, sorted_reqs, 0, session)` -> `_show_compact_card(callback, sorted_reqs, 0, session, lang=lang)`
    content = re.sub(r'_show_compact_card\(([^)]+?)(, session)(, back_cb)?\)', r'_show_compact_card(\1\2\3, lang=lang)', content)

    # navigate_card
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_nav_"\), IsReviewerL1\(\)\)\nasync def navigate_card\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"✅ Все заявки обработаны!"', r'_("l1_all_done", lang)', content)

    # show_branch_detail
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_br_detail_"\), IsReviewerL1\(\)\)\nasync def show_branch_detail\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )

    # show_detail
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_detail_"\), IsReviewerL1\(\)\)\nasync def show_detail\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"Заявка уже обработана"', r'_("alert_already_processed", lang)', content)

    # approve_request
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_approve_"\), IsReviewerL1\(\)\)\nasync def approve_request\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"✅ Одобрено!"', r'_("alert_approved", lang)', content)
    content = re.sub(r'InlineKeyboardButton\(text="📋 К очереди"', r'InlineKeyboardButton(text=_("btn_back_queue", lang)', content)

    # reject_request
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_reject_"\), IsReviewerL1\(\)\)\nasync def reject_request\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"📋 Новая техника \(не нужна замена\)"', r'_("btn_reject_reason_new", lang)', content)
    content = re.sub(r'"❌ Не соответствует критериям"', r'_("btn_reject_reason_crit", lang)', content)
    content = re.sub(r'"Выберите причину отказа:"', r'_("l1_choose_rj_reason", lang)', content)

    # reject_with_reason
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_rj_reason_"\), IsReviewerL1\(\)\)\nasync def reject_with_reason\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'"❌ Отклонена"', r'_("alert_rejected", lang)', content)

    # confirm_approve_all
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_confirm_approve_all_"\), IsReviewerL1\(\)\)\nasync def confirm_approve_all\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'text=f"✅ Да, одобрить все \{count\}"', r'text=_("btn_yes_approve", lang, count=count)', content)
    content = re.sub(r'text="❌ Нет, отмена"', r'text=_("btn_no_cancel", lang)', content)
    content = re.sub(r'f"⚠️ \*Вы уверены\?\*\\n\\nОдобрить все \*\{count\}\* заявок по филиалу \*\{branch_name\}\*\?"', r'_("l1_confirm_approve", lang, count=count, branch=branch_name)', content)

    # confirm_reject_all
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_confirm_reject_all_"\), IsReviewerL1\(\)\)\nasync def confirm_reject_all\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    content = re.sub(r'text=f"❌ Да, отклонить все \{count\}"', r'text=_("btn_yes_reject", lang, count=count)', content)
    content = re.sub(r'text="◀ Нет, отмена"', r'text=_("btn_no_cancel_arr", lang)', content)
    content = re.sub(r'f"⚠️ \*Вы уверены\?\*\\n\\nОтклонить все \*\{count\}\* заявок по филиалу \*\{branch_name\}\*\?"', r'_("l1_confirm_reject", lang, count=count, branch=branch_name)', content)

    # approve_all_branch
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_approve_all_"\), IsReviewerL1\(\)\)\nasync def approve_all_branch\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    # reject_all_branch
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("l1_reject_all_"\), IsReviewerL1\(\)\)\nasync def reject_all_branch\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )
    
    # start_review
    content = re.sub(
        r'(@router\.callback_query\(F\.data == "l1_start", IsReviewerL1\(\)\)\nasync def start_review\(callback: CallbackQuery)(, session: AsyncSession\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )

    with open(filepath, "w") as f:
        f.write(content)

update_file("app/bot/handlers/reviewer_l1.py")
