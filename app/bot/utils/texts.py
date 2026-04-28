from typing import List

TEXTS = {
    # Кнопки главного меню
    "btn_computer": {"ru": "Компьютер", "uz": "Kompyuter"},
    "btn_printer": {"ru": "Принтер", "uz": "Printer"},
    "btn_status": {"ru": "Статус моей заявки", "uz": "Mening arizam holati"},
    "btn_error": {"ru": "Сообщить об ошибке", "uz": "Xatolik haqida xabar berish"},
    
    # Кнопки подменю
    "btn_new": {"ru": "Выдача новой", "uz": "Yangi ajratish"},
    "btn_replace": {"ru": "Замена", "uz": "Almashtirish"},
    "btn_repair": {"ru": "Поломка", "uz": "Buzilish"},
    "btn_back": {"ru": "⬅️ Назад в меню", "uz": "⬅️ Menyuga qaytish"},
    "btn_cancel": {"ru": "⬅️ Отмена и в меню", "uz": "⬅️ Bekor qilish va menyuga qaytish"},
    "btn_use_fio": {"ru": "Использовать: {fio} ({pos})", "uz": "Foydalanish: {fio} ({pos})"},

    # Плейсхолдеры
    "ph_main": {"ru": "Выберите нужное действие...", "uz": "Kerakli amalni tanlang..."},
    "ph_fio": {"ru": "Введите новые данные или используйте старые", "uz": "Yangi ma'lumotlarni kiriting yoki eskisidan foydalaning"},

    # Сообщения меню
    "msg_select_equip": {"ru": "Вы выбрали оборудование: **{equip}**.\n\nКакую заявку вы хотите подать?", "uz": "Siz uskunani tanladingiz: **{equip}**.\n\nQanday ariza yubormoqchisiz?"},
    "msg_back_main": {"ru": "Вы вернулись в главное меню.", "uz": "Siz asosiy menyuga qaytdingiz."},
    "msg_cancel": {"ru": "Заполнение заявки отменено.", "uz": "Arizani to'ldirish bekor qilindi."},
    "msg_not_auth": {"ru": "Сначала необходимо выбрать филиал. Нажмите /start", "uz": "Avval filialni start orqali tanlashingiz kerak."},
    "msg_bhm_req": {"ru": "👋 Добро пожаловать!\nДля работы с системой заявок на ИТ-технику, пожалуйста, введите ваш **5-значный BXM код** филиала:", "uz": "👋 Xush kelibsiz!\nIT-texnika arizalar tizimi bilan ishlash uchun 5-raqamli BXM kodingizni kiriting:"},
    "err_bhm_invalid": {"ru": "Пожалуйста, введите корректный 5-значный числовой код (например, 11200).", "uz": "Iltimos, to'g'ri 5 xonali raqamli kodni kiriting (masalan, 11200)."},
    "err_bhm_not_found": {"ru": "Филиал с таким кодом не найден. Проверьте код и попробуйте снова:", "uz": "Bunday kodli filial topilmadi. Kodni tekshirib, qaytadan urinib ko'ring:"},
    "msg_bhm_found": {
        "ru": "✅ Филиал успешно найден:\n🏢 **{branch}**\n📍 {region}, {city}\n\nВыберите нужное действие в меню ниже 👇",
        "uz": "✅ Filial muvaffaqiyatli topildi:\n🏢 **{branch}**\n📍 {region}, {city}\n\nQuyidagi menyudan kerakli amalni tanlang 👇"
    },

    # Сообщения FSM заявок
    "msg_req_inv": {"ru": "Введите инвентарный номер оборудования:", "uz": "Uskunaning inventar raqamini kiriting:"},
    "err_inv_locked": {"ru": "❌ По данной технике уже есть активная заявка (находится в процессе).\nДождитесь её закрытия перед подачей новой.", "uz": "❌ Ushbu texnika bo'yicha allaqachon faol ariza mavjud (jarayonda).\nYangi ariza berishdan oldin uning yopilishini kuting."},
    "err_inv_not_found": {"ru": "❌ Техника с таким инвентарным номером не найдена. Проверьте номер и введите снова:", "uz": "❌ Bunday inventar raqamli texnika topilmadi. Raqamni tekshirib, qaytadan kiriting:"},
    "err_inv_branch": {"ru": "❌ Данная техника не принадлежит вашему филиалу. Проверьте номер.", "uz": "❌ Ushbu texnika sizning filialingizga tegishli emas. Raqamni tekshiring."},
    "err_inv_type": {"ru": "❌ Эта техника не является {type}. Введите корректный инвентарный номер.", "uz": "❌ Ushbu texnika turi {type} emas. To'g'ri inventar raqamini kiriting."},
    "err_rep_year": {"ru": "❌ В *Замене* отказано!\nЗамена разрешена только для техники, выпущенной до 2024 года.", "uz": "❌ *Almashtirish* rad etildi!\nAlmashtirish faqat 2024 yildan oldin chiqarilgan texnikalar uchun ruxsat etiladi."},
    
    "msg_fio_use": {"ru": "Введите ваше ФИО полностью.\n_Вы можете использовать данные из прошлой заявки (кнопка внизу)_ 👇", "uz": "FIShingizni to'liq kiriting.\n_Oldingi arizadagi ma'lumotlardan foydalanishingiz mumkin (pastdagi tugma)_ 👇"},
    "msg_fio_req": {"ru": "Введите ваше ФИО полностью:", "uz": "FIShingizni to'liq kiriting:"},
    "msg_pos_req": {"ru": "Введите вашу должность:", "uz": "Lavozimingizni kiriting:"},
    
    "msg_prob_req": {"ru": "Опишите проблему с техникой (что случилось, симптомы):", "uz": "Texnikadagi muammoni tasvirlang (nima bo'ldi, belgilari):"},
    "msg_reas_new": {"ru": "Укажите причину для выдачи новой техники:", "uz": "Yangi texnika ajratish sababini ko'rsating:"},
    "msg_reas_rep": {"ru": "Укажите причину для замены старой техники:", "uz": "Eski texnikani almashtirish sababini ko'rsating:"},
    
    "msg_success": {"ru": "✅ Ваша заявка успешно создана!\n\n**Номер заявки:** #{req_id}\nСтатус всегда можно отследить в меню 'Статус моей заявки'.", "uz": "✅ Arizangiz muvaffaqiyatli yaratildi!\n\n**Ariza raqami:** #{req_id}\nHolatni doimo 'Mening arizam holati' menyusida kuzatishingiz mumkin."},
    "err_fail": {"ru": "❌ Произошла системная ошибка при сохранении заявки. Попробуйте снова или сообщите об ошибке.", "uz": "❌ Arizani saqlashda tizimli xatolik yuz berdi. Qaytadan urinib ko'ring yoki xatolik haqida xabar bering."},

    # Статусы
    "status_empty": {"ru": "У вас пока нет поданных заявок.", "uz": "Sizda hozircha arizalar yo'q."},
    "status_header": {"ru": "📋 **Ваши последние заявки:**\n", "uz": "📋 **Sizning so'nggi arizalaringiz:**\n"},
    "status_req": {"ru": "🔸 #{req_id} | {type} ({equip})\n   ФИО: {fio}\n   Статус: {status}{decision}", "uz": "🔸 #{req_id} | {type} ({equip})\n   FIO: {fio}\n   Holati: {status}{decision}"},
    "status_reject": {"ru": "\n   Причина отказа: {reason}", "uz": "\n   Rad etish sababi: {reason}"},
    "status_limit": {"ru": "_Показаны 5 последних заявок из {total}_", "uz": "_{total} tadan so'nggi 5 ta ariza ko'rsatildi_"},

    # Ошибка (Репорт)
    "rep_start": {"ru": "Опишите обнаруженную ошибку или проблему приложения.\nВаше сообщение будет отправлено напрямую разработчику.", "uz": "Dasturdagi xatolik yoki muammoni tasvirlang.\nXabaringiz to'g'ridan-to'g'ri dasturchiga yuboriladi."},
    "rep_sending": {"ru": "Отправка сообщения...", "uz": "Xabar yuborilmoqda..."},
    "rep_sent": {"ru": "✅ Ваше сообщение успешно отправлено разработчику. Спасибо!", "uz": "✅ Xabaringiz dasturchiga muvaffaqiyatli yuborildi. Rahmat!"},
    "rep_fail": {"ru": "❌ Произошла ошибка при отправке email, попробуйте позже.", "uz": "❌ Elektron pochta yuborishda xatolik yuz berdi, keyinroq urinib ko'ring."},
    "rep_no_mail": {"ru": "✅ Внимание: Email не настроен. Ошибка записана локально.", "uz": "✅ Diqqat: Email sozlanmagan. Xatolik lokal saqlandi."}
}

def _(key: str, lang: str = "uz", **kwargs) -> str:
    """Возвращает перевод по ключу."""
    text = TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("uz", f"[{key}]"))
    if kwargs:
        return text.format(**kwargs)
    return text

def get_text_variants(key: str) -> List[str]:
    """Возвращает список всех вариантов для F.text.in_()"""
    return list(TEXTS.get(key, {}).values())
