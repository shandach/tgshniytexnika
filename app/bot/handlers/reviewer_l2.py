"""
L2 Reviewer handler — подтверждение заявок проверяющим второго уровня.

L2 видит только заявки со статусом approved_l1.
L2 получает уведомления-сводки при одобрении L1.
"""

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import IsReviewerL2
from aiogram.fsm.context import FSMContext
from app.bot.utils.texts import _, get_text_variants
from app.bot.keyboards.default import get_reviewer_l2_menu_kb
from app.models.request import Request, RequestStatus, FinalDecision

logger = logging.getLogger(__name__)
router = Router()

# ── Константы ────────────────────────────────────────────────────────────
TYPE_LABELS = {"replacement": "Замена", "new_issue": "Новая выдача", "repair": "Поломка"}
EQUIP_LABELS = {"computer": "ПК", "printer": "Принтер"}


# ── Утилиты ──────────────────────────────────────────────────────────────

async def _get_approved_l1_requests(session: AsyncSession):
    """Все заявки со статусом approved_l1 (одобренные L1, ожидают L2)."""
    stmt = (
        select(Request)
        .where(Request.status == RequestStatus.approved_l1)
        .order_by(Request.created_at.asc())
    )
    return (await session.scalars(stmt)).all()


async def _get_approved_l1_by_branch(session: AsyncSession, bhm_code: str):
    """Заявки филиала со статусом approved_l1."""
    stmt = (
        select(Request)
        .where(and_(
            Request.status == RequestStatus.approved_l1,
            Request.bhm_code_snapshot == bhm_code,
        ))
        .order_by(Request.created_at.asc())
    )
    return (await session.scalars(stmt)).all()


# ── Главное меню L2 ─────────────────────────────────────────────────────

@router.message(F.text.in_(get_text_variants("btn_l2_pending")), IsReviewerL2())
@router.callback_query(F.data == "l2_back_main", IsReviewerL2())
async def show_l2_queue(event, state: FSMContext, session: AsyncSession):
    """Сводка ожидающих подтверждения L2 — группировка по филиалам."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    stmt = (
        select(
            Request.bhm_code_snapshot,
            Request.branch_name_snapshot,
            func.count(Request.id),
        )
        .where(Request.status == RequestStatus.approved_l1)
        .group_by(Request.bhm_code_snapshot, Request.branch_name_snapshot)
        .order_by(func.count(Request.id).desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        text = "✅ Нет заявок для подтверждения." if lang == "ru" else "✅ Tasdiqlash uchun arizalar yo'q."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_reviewer_l2_menu_kb())
        return

    total = sum(r[2] for r in rows)
    header = f"📋 *Ожидающие подтверждения L2: {total}*\n" if lang == "ru" else f"📋 *L2 tasdiqlashini kutayotganlar: {total}*\n"
    lines = [header]

    buttons = []
    for bhm_code, name, count in rows:
        req_text = "заявок" if lang == "ru" else "ta ariza"
        lines.append(f"• {name} ({bhm_code}) — {count} {req_text}")
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({count})",
            callback_data=f"l2_branch_{bhm_code}",
        )])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "\n".join(lines)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")


# ── Сводка по филиалу ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("l2_branch_"), IsReviewerL2())
async def show_l2_branch(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Показать заявки филиала для L2."""
    bhm_code = callback.data.replace("l2_branch_", "")
    requests = await _get_approved_l1_by_branch(session, bhm_code)

    if not requests:
        await callback.message.edit_text(_("l1_branch_done", lang))
        await callback.answer()
        return

    branch_name = requests[0].branch_name_snapshot
    branch_lbl = "Филиал" if lang == "ru" else "Filial"
    approved_lbl = "L1 одобрено" if lang == "ru" else "L1 tasdiqlagan"
    reqs_lbl = "заявок" if lang == "ru" else "ta ariza"
    
    lines = [
        f"📍 *{branch_lbl}: {branch_name} ({bhm_code})*",
        f"{approved_lbl}: {len(requests)} {reqs_lbl}\n",
    ]

    for r in requests:
        equip = _("lbl_" + r.equipment_type, lang) if r.equipment_type in ["computer", "printer"] else r.equipment_type
        r_type = _("lbl_" + r.request_type, lang) if r.request_type in ["replacement", "new_issue", "repair"] else r.request_type
        lines.append(
            f"• #{r.request_number} — {r_type} "
            f"{equip} | {r.employee_fio_snapshot}"
        )

    call_lbl = "\n📞 _Не забудьте позвонить руководителю филиала_" if lang == "ru" else "\n📞 _Filial rahbariga qo'ng'iroq qilishni unutmang_"
    lines.append(call_lbl)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Одобрить все {len(requests)}" if lang == "ru" else f"✅ Barchasini tasdiqlash ({len(requests)})", callback_data=f"l2_approve_all_{bhm_code}"),
            InlineKeyboardButton(text=_("btn_l1_detail", lang), callback_data=f"l2_detail_branch_{bhm_code}_0"),
        ],
        [InlineKeyboardButton(text=_("btn_l2_reject_all", lang), callback_data=f"l2_reject_all_{bhm_code}")],
        [InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data="l2_back_main")],
    ])

    await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ── Разобрать по одной ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("l2_detail_branch_"), IsReviewerL2())
async def show_l2_detail(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Карточка заявки для L2."""
    parts = callback.data.replace("l2_detail_branch_", "").rsplit("_", 1)
    bhm_code = parts[0]
    idx = int(parts[1])

    requests = await _get_approved_l1_by_branch(session, bhm_code)
    if not requests or idx >= len(requests):
        await callback.message.edit_text(_("l1_all_done", lang))
        await callback.answer()
        return

    req = requests[idx]
    equip = _("lbl_" + req.equipment_type, lang) if req.equipment_type in ["computer", "printer"] else req.equipment_type
    inv = req.inventory_code_snapshot or "—"
    l1_comment = req.l1_comment or "—"
    r_type = _("lbl_" + req.request_type, lang) if req.request_type in ["replacement", "new_issue", "repair"] else req.request_type

    text = (
        f"{idx + 1} из {len(requests)} | *#{req.request_number}* — {bhm_code}\n" if lang == "ru" else f"{len(requests)} tadan {idx + 1} | *#{req.request_number}* — {bhm_code}\n"
    ) + (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Тип: {r_type}\n" if lang == "ru" else f"━━━━━━━━━━━━━━━━━━\nTuri: {r_type}\n"
    ) + (
        f"Сотрудник: {req.employee_fio_snapshot} / {req.employee_position_snapshot or '—'}\n" if lang == "ru" else f"Xodim: {req.employee_fio_snapshot} / {req.employee_position_snapshot or '—'}\n"
    ) + (
        f"Устройство: {equip} / {inv}\n" if lang == "ru" else f"Uskuna: {equip} / {inv}\n"
    ) + (
        f"\nL1 комментарий: _{l1_comment}_" if lang == "ru" else f"\nL1 izohi: _{l1_comment}_"
    )

    buttons = [
        [
            InlineKeyboardButton(text=_("btn_confirm", lang), callback_data=f"l2_approve_{req.id}_{bhm_code}_{idx}"),
            InlineKeyboardButton(text=_("btn_reject", lang), callback_data=f"l2_reject_{req.id}_{bhm_code}_{idx}"),
        ],
    ]
    if idx + 1 < len(requests):
        buttons.append([InlineKeyboardButton(
            text=_("btn_nav_next", lang),
            callback_data=f"l2_detail_branch_{bhm_code}_{idx + 1}",
        )])
    buttons.append([InlineKeyboardButton(text=_("btn_back_branch", lang), callback_data=f"l2_branch_{bhm_code}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ── Одобрить / Отклонить одну ────────────────────────────────────────────

@router.callback_query(F.data.startswith("l2_approve_"), IsReviewerL2())
async def l2_approve_one(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """L2 подтверждает заявку → closed + approved."""
    parts = callback.data.replace("l2_approve_", "").split("_")
    req_id = int(parts[0])
    bhm_code = parts[1]
    idx = int(parts[2]) if len(parts) > 2 else 0

    req = await session.get(Request, req_id)
    if not req or req.status != RequestStatus.approved_l1:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    req.status = RequestStatus.closed
    req.final_decision = FinalDecision.approved
    req.l2_reviewer_tg_id = callback.from_user.id
    req.closed_at = datetime.now(timezone.utc)
    await session.commit()

    await callback.answer(_("alert_confirmed", lang), show_alert=True)

    # Показать следующую заявку из того же филиала
    remaining = await _get_approved_l1_by_branch(session, bhm_code)
    if remaining:
        await show_l2_detail.__wrapped__(callback, state, session) if hasattr(show_l2_detail, '__wrapped__') else None
        # Проще: вернуть к списку филиала
        await show_l2_branch.__wrapped__(callback, state, session) if hasattr(show_l2_branch, '__wrapped__') else None
        # Fallback
        callback.data = f"l2_branch_{bhm_code}"
        await show_l2_branch(callback, state, session)
    else:
        await callback.message.edit_text(
            f"✅ Все заявки по {bhm_code} обработаны!" if lang == "ru" else f"✅ {bhm_code} bo'yicha barcha arizalar ko'rib chiqildi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("btn_back_list", lang), callback_data="l2_back_main")]
            ]),
        )


@router.callback_query(F.data.startswith("l2_reject_"), IsReviewerL2())
async def l2_reject_one(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """L2 отклоняет заявку — причины."""
    parts = callback.data.replace("l2_reject_", "").split("_")
    req_id = parts[0]
    bhm_code = parts[1]
    
    idx = parts[2] if len(parts) > 2 else "0"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_l2_rj_no_confirm", lang), callback_data=f"l2_rj_{req_id}_{bhm_code}_no_confirm")],
        [InlineKeyboardButton(text=_("btn_l2_rj_in_progress", lang), callback_data=f"l2_rj_{req_id}_{bhm_code}_in_progress")],
        [InlineKeyboardButton(text=_("btn_l2_rj_no_priority", lang), callback_data=f"l2_rj_{req_id}_{bhm_code}_no_priority")],
        [InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data=f"l2_detail_branch_{bhm_code}_{idx}")],
    ])
    await callback.message.edit_text(_("l1_choose_rj_reason", lang), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("l2_rj_"), IsReviewerL2())
async def l2_reject_with_reason(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Применить отказ L2."""
    parts = callback.data.replace("l2_rj_", "").split("_")
    req_id = int(parts[0])
    bhm_code = parts[1]
    reason_key = "_".join(parts[2:])

    reasons = {
        "no_confirm": "Руководитель филиала не подтвердил" if lang == "ru" else "Filial rahbari tasdiqlamadi",
        "in_progress": "Уже в процессе замены" if lang == "ru" else "Allaqachon almashtirish jarayonida",
        "no_priority": "Не в списке приоритетов" if lang == "ru" else "Ustuvor ro'yxatda yo'q",
    }

    req = await session.get(Request, req_id)
    if not req or req.status != RequestStatus.approved_l1:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    req.status = RequestStatus.closed
    req.final_decision = FinalDecision.rejected
    req.reject_reason = reasons.get(reason_key, reason_key)
    req.l2_reviewer_tg_id = callback.from_user.id
    req.closed_at = datetime.now(timezone.utc)
    await session.commit()

    await callback.answer(_("alert_rejected", lang), show_alert=True)

    # Вернуться к филиалу
    callback.data = f"l2_branch_{bhm_code}"
    await show_l2_branch(callback, state, session)


# ── Массовые операции ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("l2_approve_all_"), IsReviewerL2())
async def l2_approve_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Одобрить все заявки филиала."""
    bhm_code = callback.data.replace("l2_approve_all_", "")
    requests = await _get_approved_l1_by_branch(session, bhm_code)

    if not requests:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    # Подсчёт техники для сводки
    tech_summary = {}
    count = 0
    for r in requests:
        r.status = RequestStatus.closed
        r.final_decision = FinalDecision.approved
        r.l2_reviewer_tg_id = callback.from_user.id
        r.closed_at = datetime.now(timezone.utc)
        equip = EQUIP_LABELS.get(r.equipment_type, r.equipment_type)
        tech_summary[equip] = tech_summary.get(equip, 0) + 1
        count += 1

    await session.commit()

    branch_name = requests[0].branch_name_snapshot
    tech_lines = ", ".join(f"{c} {t}" for t, c in tech_summary.items())

    text = (
        f"✅ *{bhm_code} — {count} одобрено*\n"
        f"📋 Сводный отчёт для отдела выдачи\n\n"
        f"• Нужно техники: {tech_lines}\n"
        f"• Филиал: {branch_name} ({bhm_code})"
    ) if lang == "ru" else (
        f"✅ *{bhm_code} — {count} ta tasdiqlandi*\n"
        f"📋 Ajratish bo'limi uchun umumiy hisobot\n\n"
        f"• Kerakli texnika: {tech_lines}\n"
        f"• Filial: {branch_name} ({bhm_code})"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_l2_revoke", lang), callback_data=f"l2_revoke_{bhm_code}")],
        [InlineKeyboardButton(text=_("btn_back_list", lang), callback_data="l2_back_main")],
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("l2_reject_all_"), IsReviewerL2())
async def l2_reject_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Отклонить все заявки филиала."""
    bhm_code = callback.data.replace("l2_reject_all_", "")
    requests = await _get_approved_l1_by_branch(session, bhm_code)
    count = 0
    for r in requests:
        r.status = RequestStatus.closed
        r.final_decision = FinalDecision.rejected
        r.reject_reason = "Массовый отказ L2" if lang == "ru" else "L2 tomonidan ommaviy rad etish"
        r.l2_reviewer_tg_id = callback.from_user.id
        r.closed_at = datetime.now(timezone.utc)
        count += 1
    await session.commit()

    text = f"❌ Отклонено {count} заявок по {bhm_code}" if lang == "ru" else f"❌ {bhm_code} bo'yicha {count} ta ariza rad etildi"
    await callback.message.edit_text(text)
    await callback.answer()


# ── Отозвать заявку ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("l2_revoke_"), IsReviewerL2())
async def l2_revoke_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Показать недавно одобренные для отзыва."""
    bhm_code = callback.data.replace("l2_revoke_", "")

    stmt = (
        select(Request)
        .where(and_(
            Request.bhm_code_snapshot == bhm_code,
            Request.status == RequestStatus.closed,
            Request.final_decision == FinalDecision.approved,
            Request.l2_reviewer_tg_id == callback.from_user.id,
        ))
        .order_by(Request.closed_at.desc())
        .limit(10)
    )
    requests = (await session.scalars(stmt)).all()

    if not requests:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    buttons = []
    for r in requests:
        buttons.append([InlineKeyboardButton(
            text=f"↩ #{r.request_number} — {r.employee_fio_snapshot}",
            callback_data=f"l2_do_revoke_{r.id}_{bhm_code}",
        )])
    buttons.append([InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data="l2_back_main")])

    await callback.message.edit_text(
        "Выберите заявку для отзыва:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("l2_do_revoke_"), IsReviewerL2())
async def l2_do_revoke(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "ru")
    """Отозвать ранее одобренную заявку → обратно в approved_l1."""
    parts = callback.data.replace("l2_do_revoke_", "").split("_")
    req_id = int(parts[0])
    bhm_code = parts[1]

    req = await session.get(Request, req_id)
    if not req:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    req.status = RequestStatus.approved_l1
    req.final_decision = FinalDecision.pending
    req.l2_reviewer_tg_id = None
    req.closed_at = None
    await session.commit()

    await callback.answer(_("alert_revoked", lang, req_id=req.request_number), show_alert=True)
    callback.data = "l2_back_main"
    await show_l2_queue(callback, state, session)
