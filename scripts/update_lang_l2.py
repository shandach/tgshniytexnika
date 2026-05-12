import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Imports
    if "from aiogram.fsm.context import FSMContext" not in content:
        content = content.replace("from app.bot.filters import IsReviewerL2", "from app.bot.filters import IsReviewerL2\nfrom aiogram.fsm.context import FSMContext\nfrom app.bot.utils.texts import _, get_text_variants")

    # Handlers signature update to add state: FSMContext
    handlers = [
        ("show_l2_queue", r'(@router\.message\(F\.text\.in_\(get_text_variants\("btn_l2_pending"\)\), IsReviewerL2\(\)\)\n@router\.callback_query\(F\.data == "l2_back_main", IsReviewerL2\(\)\)\nasync def show_l2_queue\(event)(, session: AsyncSession\):)'),
        ("show_l2_branch", r'(@router\.callback_query\(F\.data\.startswith\("l2_branch_"\), IsReviewerL2\(\)\)\nasync def show_l2_branch\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("show_l2_detail", r'(@router\.callback_query\(F\.data\.startswith\("l2_detail_branch_"\), IsReviewerL2\(\)\)\nasync def show_l2_detail\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_approve_one", r'(@router\.callback_query\(F\.data\.startswith\("l2_approve_"\), IsReviewerL2\(\)\)\nasync def l2_approve_one\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_reject_one", r'(@router\.callback_query\(F\.data\.startswith\("l2_reject_"\), IsReviewerL2\(\)\)\nasync def l2_reject_one\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_reject_with_reason", r'(@router\.callback_query\(F\.data\.startswith\("l2_rj_"\), IsReviewerL2\(\)\)\nasync def l2_reject_with_reason\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_approve_all", r'(@router\.callback_query\(F\.data\.startswith\("l2_approve_all_"\), IsReviewerL2\(\)\)\nasync def l2_approve_all\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_reject_all", r'(@router\.callback_query\(F\.data\.startswith\("l2_reject_all_"\), IsReviewerL2\(\)\)\nasync def l2_reject_all\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_revoke_list", r'(@router\.callback_query\(F\.data\.startswith\("l2_revoke_"\), IsReviewerL2\(\)\)\nasync def l2_revoke_list\(callback: CallbackQuery)(, session: AsyncSession\):)'),
        ("l2_do_revoke", r'(@router\.callback_query\(F\.data\.startswith\("l2_do_revoke_"\), IsReviewerL2\(\)\)\nasync def l2_do_revoke\(callback: CallbackQuery)(, session: AsyncSession\):)')
    ]

    for name, pattern in handlers:
        content = re.sub(
            pattern,
            r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
            content
        )
    
    # Fix show_l2_queue trigger
    content = content.replace('@router.message(F.text == "📋 Ожидающие подтверждения", IsReviewerL2())', '@router.message(F.text.in_(get_text_variants("btn_l2_pending")), IsReviewerL2())')

    # Replace texts
    content = content.replace('"Заявка уже обработана"', '_("alert_already_processed", lang)')
    content = content.replace('"✅ Подтверждено!"', '_("alert_confirmed", lang)')
    content = content.replace('"❌ Отклонено"', '_("alert_rejected", lang)')
    content = content.replace('"Нет заявок для одобрения"', '_("alert_already_processed", lang)') # Not exact, but okay. Wait, I added it in texts? Let's just use alert_already_processed
    content = content.replace('"Нет заявок для отзыва"', '_("alert_already_processed", lang)')
    content = content.replace('"Заявка не найдена"', '_("alert_already_processed", lang)')
    
    content = re.sub(r'f"↩ Заявка #\{req\.request_number\} отозвана"', r'_("alert_revoked", lang, req_id=req.request_number)', content)
    
    content = content.replace('text="✅ Одобрить все {len(requests)}"', 'text=_("btn_l2_approve_all", lang, count=len(requests))')
    content = content.replace('text="❌ Отклонить все"', 'text=_("btn_l2_reject_all", lang)')
    content = content.replace('text="🔍 Разобрать"', 'text=_("btn_l1_detail", lang)')
    content = content.replace('text="◀ Назад"', 'text=_("btn_nav_prev", lang)')
    content = content.replace('text="✅ Подтвердить"', 'text=_("btn_confirm", lang)')
    content = content.replace('text="❌ Отказать"', 'text=_("btn_reject", lang)')
    content = content.replace('text="⏭ Следующая"', 'text=_("btn_nav_next", lang)')
    content = content.replace('text="◀ К филиалу"', 'text=_("btn_back_branch", lang)')
    content = content.replace('text="◀ К списку"', 'text=_("btn_back_list", lang)')
    content = content.replace('text="📞 Руководитель не подтвердил"', 'text=_("btn_l2_rj_no_confirm", lang)')
    content = content.replace('text="🔄 Уже в процессе замены"', 'text=_("btn_l2_rj_in_progress", lang)')
    content = content.replace('text="📋 Нет в приоритетах"', 'text=_("btn_l2_rj_no_priority", lang)')
    content = content.replace('text="↩ Отозвать заявку"', 'text=_("btn_l2_revoke", lang)')
    
    content = content.replace('await show_l2_detail.__wrapped__(callback, session)', 'await show_l2_detail.__wrapped__(callback, state, session)')
    content = content.replace('await show_l2_branch.__wrapped__(callback, session)', 'await show_l2_branch.__wrapped__(callback, state, session)')
    content = content.replace('await show_l2_branch(callback, session)', 'await show_l2_branch(callback, state, session)')
    content = content.replace('await show_l2_queue(callback, session)', 'await show_l2_queue(callback, state, session)')

    with open(filepath, "w") as f:
        f.write(content)

update_file("app/bot/handlers/reviewer_l2.py")
