import re

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Handlers that need state added
    # 1. my_req_detail
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("myreq_"\)\)\nasync def my_req_detail\(callback: CallbackQuery, session: AsyncSession)(, state: FSMContext\):)',
        r'\1\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )

    # 2. repair_confirmed_yes
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("rep_yes_"\)\)\nasync def repair_confirmed_yes\(callback: CallbackQuery, session: AsyncSession)(\):)',
        r'\1, state: FSMContext\2\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )

    # 3. repair_escalate_no
    content = re.sub(
        r'(@router\.callback_query\(F\.data\.startswith\("rep_no_"\)\)\nasync def repair_escalate_no\(callback: CallbackQuery, session: AsyncSession, state: FSMContext\):)',
        r'\1\n    data = await state.get_data()\n    lang = data.get("language", "uz")',
        content
    )

    # Note: process_escalation_comment already extracts lang

    # Replace texts with placeholders
    # In my_req_detail:
    content = content.replace('await callback.answer("Заявка не найдена")', 'await callback.answer(_("alert_already_processed", lang))')
    
    # Let's add strings to texts.py or just leave them if we don't have exact translations, but we must translate them.
    # Actually, the user asked for full translation. I'll replace the text building with a translated format string.
    
    # We will use `_("status_req_detail_... ", lang)` and add them to texts.py later.
    
    with open(filepath, "w") as f:
        f.write(content)

update_file("app/bot/handlers/status.py")
