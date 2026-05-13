"""
L1 Reviewer handler — обработка заявок проверяющим первого уровня.

UX v2: динамическое меню, компактные карточки, пагинация, подтверждение
массовых действий.

Каждый L1-проверяющий (mintaqaviy) видит заявки только своей области.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import IsReviewerL1
from app.bot.keyboards.default import get_reviewer_l1_menu_kb
from app.models.branch import BhmBranch
from app.models.request import Request, RequestStatus, FinalDecision, RequestType
from app.models.telegram_account import TelegramAccount
from aiogram.fsm.context import FSMContext
from app.bot.utils.texts import _, get_text_variants

logger = logging.getLogger(__name__)
router = Router()

# ── Константы ────────────────────────────────────────────────────────────
TYPE_LABELS = {"replacement": "Замена", "new_issue": "Новая выдача", "repair": "Поломка"}
TYPE_ICONS = {"replacement": "🔴", "new_issue": "🟡", "repair": "🔵"}
EQUIP_LABELS = {"computer": "ПК", "printer": "Принтер"}
PRIORITY_HOURS = 24


# ── Утилиты ──────────────────────────────────────────────────────────────

def _age_short(created_at: datetime) -> str:
    """Короткая метка давности."""
    now = datetime.now(timezone.utc)
    ca = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
    delta = now - ca
    hours = delta.total_seconds() / 3600
    if hours > 48:
        return f"{int(hours // 24)}д"
    return f"{int(hours)}ч"


def _is_priority(created_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    ca = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
    return (now - ca).total_seconds() > PRIORITY_HOURS * 3600


async def _get_reviewer_region(session: AsyncSession, tg_id: int, state: FSMContext = None) -> Optional[str]:
    """Получить assigned_region из FSM-кэша (RAM), при отсутствии — из БД."""
    if state:
        data = await state.get_data()
        cached = data.get("assigned_region", "__UNSET__")
        # Если в кэше уже есть непустое значение — берем его. 
        # Если там None или __UNSET__ — идем в БД (на случай, если регион только что назначили).
        if cached and cached != "__UNSET__":
            return cached
            
    # Первый вызов или если было None — идём в БД
    stmt = select(TelegramAccount.assigned_region).where(
        TelegramAccount.telegram_user_id == tg_id
    )
    region = await session.scalar(stmt)
    if region:
        region = region.strip()
    if state:
        await state.update_data(assigned_region=region)
    return region


async def _get_new_requests(session: AsyncSession, region: Optional[str] = None):
    """
    Новые заявки. 
    Если region задан — только из филиалов этой области.
    Если region НЕ задан — возвращаем ПУСТОЙ список (L1 должен быть привязан).
    """
    if not region:
        return []

    stmt = select(Request).where(Request.status.in_([RequestStatus.new, RequestStatus.in_progress]))
    stmt = stmt.join(BhmBranch, Request.branch_id == BhmBranch.id).where(
        BhmBranch.region_name == region
    )
    stmt = stmt.order_by(Request.created_at.asc())
    return (await session.scalars(stmt)).all()


async def _get_new_by_branch(session: AsyncSession, bhm_code: str):
    stmt = (
        select(Request)
        .where(and_(Request.status.in_([RequestStatus.new, RequestStatus.in_progress]), Request.bhm_code_snapshot == bhm_code))
        .order_by(Request.created_at.asc())
    )
    return (await session.scalars(stmt)).all()


def _sorted_by_priority(requests):
    """Приоритетные (старые) сверху."""
    priority = [r for r in requests if _is_priority(r.created_at)]
    normal = [r for r in requests if not _is_priority(r.created_at)]
    return priority + normal


async def _safe_edit(callback: CallbackQuery, text: str, kb, parse_mode="Markdown"):
    """edit_text с защитой от 'message is not modified'."""
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb, parse_mode=parse_mode)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════
# РЕЖИМ 1: ОЧЕРЕДЬ ЗАЯВОК
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("queue"), IsReviewerL1())
@router.message(F.text.in_(get_text_variants("btn_l1_queue")), IsReviewerL1())
async def show_queue(message: Message, state: FSMContext, session: AsyncSession):
    """Сводка очереди + динамическое Reply-меню (режим queue)."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    region = await _get_reviewer_region(session, message.from_user.id, state)
    requests = await _get_new_requests(session, region)
    total = len(requests)

    if not region:
        await message.answer(
            "⚠️ *Вам не назначен регион для проверки.*\n"
            "Пожалуйста, обратитесь к администратору для привязки к области.",
            parse_mode="Markdown",
            reply_markup=get_reviewer_l1_menu_kb("default", lang),
        )
        return

    if total == 0:
        await message.answer(
            _("l1_queue_empty", lang),
            reply_markup=get_reviewer_l1_menu_kb("queue", lang),
        )
        return

    text = _build_queue_summary(requests, region)
    # В режиме очереди: только "Начать проверку" (без "По филиалам" inline)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_l1_start", lang), callback_data="l1_start")],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    # Переключаем Reply-клавиатуру на режим queue
    await message.answer("⬇️", reply_markup=get_reviewer_l1_menu_kb("queue", lang))


def _build_queue_summary(requests, region: Optional[str] = None) -> str:
    total = len(requests)
    by_type = {}
    for r in requests:
        by_type[r.request_type] = by_type.get(r.request_type, 0) + 1
    priority_count = sum(1 for r in requests if _is_priority(r.created_at))

    header = f"📂 *Режим: Очередь заявок*\n"
    if region:
        header += f"📍 *Область: {region}*\n"
    lines = [header, f"📋 *{total} новых заявок*", "━" * 20]
    for rt, count in by_type.items():
        lines.append(f"{TYPE_ICONS.get(rt, '⚪')} {TYPE_LABELS.get(rt, rt)}: {count}")
    if priority_count:
        lines.append(f"\n🔥 *Приоритетных (>{PRIORITY_HOURS}ч):* {priority_count}")
    return "\n".join(lines)


@router.callback_query(F.data == "l1_back_queue", IsReviewerL1())
async def back_to_queue(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Вернуться к сводке очереди (inline)."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    region = await _get_reviewer_region(session, callback.from_user.id, state)
    requests = await _get_new_requests(session, region)

    if not requests:
        await _safe_edit(callback, _("l1_queue_empty", lang), None)
        return

    text = _build_queue_summary(requests, region)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_l1_start", lang), callback_data="l1_start")],
    ])
    await _safe_edit(callback, text, kb)


# ── Начать проверку (карточки по дате) ───────────────────────────────────

@router.callback_query(F.data == "l1_start", IsReviewerL1())
async def start_review(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    region = await _get_reviewer_region(session, callback.from_user.id, state)
    requests = await _get_new_requests(session, region)
    if not requests:
        await _safe_edit(callback, "✅ Очередь пуста!", None)
        return
    sorted_reqs = _sorted_by_priority(requests)
    await _show_compact_card(callback, sorted_reqs, 0, session, lang=lang)


# ══════════════════════════════════════════════════════════════════════════
# РЕЖИМ 2: ПО ФИЛИАЛАМ
# ══════════════════════════════════════════════════════════════════════════

@router.message(F.text.in_(get_text_variants("btn_l1_branches")), IsReviewerL1())
@router.callback_query(F.data == "l1_branches", IsReviewerL1())
async def show_branches(event, state: FSMContext, session: AsyncSession):
    """Список филиалов + динамическое Reply-меню (режим branch)."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    tg_id = event.from_user.id
    region = await _get_reviewer_region(session, tg_id, state)

    if not region:
        msg = "⚠️ *Вам не назначен регион для проверки.*\nПожалуйста, обратитесь к администратору."
        if isinstance(event, CallbackQuery):
            await _safe_edit(event, msg, None)
        else:
            await event.answer(msg, parse_mode="Markdown", reply_markup=get_reviewer_l1_menu_kb("default", lang))
        return

    stmt = (
        select(Request.bhm_code_snapshot, Request.branch_name_snapshot, func.count(Request.id))
        .join(BhmBranch, Request.branch_id == BhmBranch.id)
        .where(and_(
            Request.status.in_([RequestStatus.new, RequestStatus.in_progress]),
            BhmBranch.region_name == region
        ))
        .group_by(Request.bhm_code_snapshot, Request.branch_name_snapshot)
        .order_by(func.count(Request.id).desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        text = _("l1_branches_empty", lang)
        if isinstance(event, CallbackQuery):
            await _safe_edit(event, text, None)
        else:
            await event.answer(text, reply_markup=get_reviewer_l1_menu_kb("branch", lang))
        return

    total = sum(r[2] for r in rows)
    buttons = []
    for bhm_code, name, count in rows:
        buttons.append([InlineKeyboardButton(
            text=f"🏢 {name} ({count})",
            callback_data=f"l1_branch_{bhm_code}",
        )])
    buttons.append([InlineKeyboardButton(text=_("btn_back_queue", lang), callback_data="l1_back_queue")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    region_label = f"\n📍 Область: {region}" if region else ""
    text = f"🏢 *Режим: По филиалам*{region_label}\n📋 Всего {total} заявок в {len(rows)} филиалах\n\nВыберите филиал:"

    if isinstance(event, CallbackQuery):
        await _safe_edit(event, text, kb)
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")
        # Переключаем Reply-клавиатуру на режим branch
        await event.answer("⬇️", reply_markup=get_reviewer_l1_menu_kb("branch", lang))


# ── Заявки филиала ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("l1_branch_"), IsReviewerL1())
async def show_branch_requests(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    bhm_code = callback.data.replace("l1_branch_", "")
    requests = await _get_new_by_branch(session, bhm_code)

    if not requests:
        await _safe_edit(callback, _("l1_branch_done", lang), InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=_("btn_back_branches", lang), callback_data="l1_branches")]]
        ))
        return

    branch_name = requests[0].branch_name_snapshot
    lines = [f"🏢 *Режим: {branch_name} ({bhm_code})*", f"📋 {len(requests)} заявок\n"]

    for i, r in enumerate(requests[:10], 1):  # Максимум 10 в превью
        age = _age_short(r.created_at)
        fire = "🔥 " if _is_priority(r.created_at) else ""
        equip = EQUIP_LABELS.get(r.equipment_type, "")
        lines.append(
            f"{fire}{i}. {TYPE_LABELS.get(r.request_type, '')} {equip} | "
            f"{r.employee_fio_snapshot} | {age}"
        )

    if len(requests) > 10:
        lines.append(f"\n_...и ещё {len(requests) - 10} заявок_")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_l1_detail", lang), callback_data=f"l1_br_detail_{bhm_code}_0")],
        [
            InlineKeyboardButton(text=_("btn_approve_all", lang), callback_data=f"l1_confirm_approve_all_{bhm_code}"),
            InlineKeyboardButton(text=_("btn_reject_all", lang), callback_data=f"l1_confirm_reject_all_{bhm_code}"),
        ],
        [InlineKeyboardButton(text=_("btn_back_branches", lang), callback_data="l1_branches")],
    ])

    await _safe_edit(callback, "\n".join(lines), kb)


# ══════════════════════════════════════════════════════════════════════════
# КАРТОЧКА ЗАЯВКИ (КОМПАКТНЫЙ ФОРМАТ + ПАГИНАЦИЯ)
# ══════════════════════════════════════════════════════════════════════════

async def _show_compact_card(callback: CallbackQuery, sorted_reqs, idx: int, session: AsyncSession, back_cb: str = "l1_back_queue", lang: str = "uz"):
    """Компактная карточка заявки с пагинацией ◀/▶."""
    total = len(sorted_reqs)
    if idx >= total:
        await _safe_edit(callback, _("l1_all_viewed", lang), InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data=back_cb)]]
        ))
        return

    req = sorted_reqs[idx]
    fire = "🔥 " if _is_priority(req.created_at) else ""
    age = _age_short(req.created_at)
    equip = EQUIP_LABELS.get(req.equipment_type, req.equipment_type)
    inv = req.inventory_code_snapshot or ""
    inv_str = f" {inv}" if inv else ""
    reason = req.reason_text or req.problem_text or "—"

    text = (
        f"{fire}*#{req.request_number}* | {TYPE_LABELS.get(req.request_type, req.request_type)}\n"
        f"👤 {req.employee_fio_snapshot} · {req.employee_position_snapshot or '—'}\n"
        f"🏢 {req.branch_name_snapshot} ({req.bhm_code_snapshot}) · {equip}{inv_str}\n"
        f"⏱ {age} · 📄 {idx + 1}/{total}\n"
        f"\n💬 _{reason}_"
    )

    # Кнопки действий
    buttons = [
        [
            InlineKeyboardButton(text=_("btn_approve", lang), callback_data=f"l1_approve_{req.id}"),
            InlineKeyboardButton(text=_("btn_reject", lang), callback_data=f"l1_reject_{req.id}"),
        ],
    ]

    # Навигация ◀ / ▶  в одном ряду
    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data=f"l1_nav_{idx - 1}_{back_cb}"))
    if idx + 1 < total:
        nav_row.append(InlineKeyboardButton(text=_("btn_nav_next", lang), callback_data=f"l1_nav_{idx + 1}_{back_cb}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=_("btn_back_list", lang), callback_data=back_cb)])

    await _safe_edit(callback, text, InlineKeyboardMarkup(inline_keyboard=buttons))


# ── Навигация по карточкам (общая очередь) ───────────────────────────────

@router.callback_query(F.data.startswith("l1_nav_"), IsReviewerL1())
async def navigate_card(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    """Пагинация: переход к карточке N."""
    parts = callback.data.replace("l1_nav_", "").split("_", 1)
    idx = int(parts[0])
    back_cb = parts[1] if len(parts) > 1 else "l1_back_queue"

    region = await _get_reviewer_region(session, callback.from_user.id, state)
    requests = await _get_new_requests(session, region)
    if not requests:
        await _safe_edit(callback, _("l1_all_done", lang), None)
        return
    sorted_reqs = _sorted_by_priority(requests)
    await _show_compact_card(callback, sorted_reqs, min(idx, len(sorted_reqs) - 1), session, back_cb, lang=lang)


# ── Навигация по карточкам (внутри филиала) ──────────────────────────────

@router.callback_query(F.data.startswith("l1_br_detail_"), IsReviewerL1())
async def show_branch_detail(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    """Карточка заявки внутри филиала."""
    parts = callback.data.replace("l1_br_detail_", "").rsplit("_", 1)
    bhm_code = parts[0]
    idx = int(parts[1])
    requests = await _get_new_by_branch(session, bhm_code)
    if not requests:
        await _safe_edit(callback, _("l1_all_done", lang), InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=_("btn_back_branches", lang), callback_data="l1_branches")]]
        ))
        return

    # Для навигации внутри филиала используем специальный back_cb
    back_cb = f"l1_branch_{bhm_code}"
    sorted_reqs = _sorted_by_priority(requests)

    total = len(sorted_reqs)
    if idx >= total:
        idx = total - 1

    req = sorted_reqs[idx]
    fire = "🔥 " if _is_priority(req.created_at) else ""
    age = _age_short(req.created_at)
    equip = EQUIP_LABELS.get(req.equipment_type, req.equipment_type)
    inv = req.inventory_code_snapshot or ""
    inv_str = f" {inv}" if inv else ""
    reason = req.reason_text or req.problem_text or "—"

    text = (
        f"{fire}*#{req.request_number}* | {TYPE_LABELS.get(req.request_type, req.request_type)}\n"
        f"👤 {req.employee_fio_snapshot} · {req.employee_position_snapshot or '—'}\n"
        f"🏢 {req.branch_name_snapshot} ({req.bhm_code_snapshot}) · {equip}{inv_str}\n"
        f"⏱ {age} · 📄 {idx + 1}/{total}\n"
        f"\n💬 _{reason}_"
    )

    buttons = [
        [
            InlineKeyboardButton(text=_("btn_approve", lang), callback_data=f"l1_approve_{req.id}"),
            InlineKeyboardButton(text=_("btn_reject", lang), callback_data=f"l1_reject_{req.id}"),
        ],
    ]
    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data=f"l1_br_detail_{bhm_code}_{idx - 1}"))
    if idx + 1 < total:
        nav_row.append(InlineKeyboardButton(text=_("btn_nav_next", lang), callback_data=f"l1_br_detail_{bhm_code}_{idx + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=_("btn_back_branch", lang), callback_data=back_cb)])

    await _safe_edit(callback, text, InlineKeyboardMarkup(inline_keyboard=buttons))


# ── Показ конкретной заявки по ID ────────────────────────────────────────

@router.callback_query(F.data.startswith("l1_detail_"), IsReviewerL1())
async def show_detail(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    req_id = int(callback.data.replace("l1_detail_", ""))
    req = await session.get(Request, req_id)
    if not req or req.status != RequestStatus.new:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return
    await _show_compact_card(callback, [req], 0, session, lang=lang)


# ══════════════════════════════════════════════════════════════════════════
# ОДОБРИТЬ / ОТКЛОНИТЬ
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("l1_approve_"), IsReviewerL1())
async def approve_request(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    # Защита от пересечения с l1_approve_all_
    if callback.data.startswith("l1_approve_all_"):
        return
    req_id = int(callback.data.replace("l1_approve_", ""))
    req = await session.get(Request, req_id)
    if not req or req.status != RequestStatus.new:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    req.status = RequestStatus.approved_l1
    req.l1_reviewer_tg_id = callback.from_user.id
    await session.commit()
    await callback.answer(_("alert_approved", lang), show_alert=True)

    # Показать следующую (с учётом региона проверяющего)
    region = await _get_reviewer_region(session, callback.from_user.id, state)
    remaining = await _get_new_requests(session, region)
    if remaining:
        sorted_reqs = _sorted_by_priority(remaining)
        await _show_compact_card(callback, sorted_reqs, 0, session, lang=lang)
    else:
        await _safe_edit(callback, _("l1_all_done", lang), InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=_("btn_back_queue", lang), callback_data="l1_back_queue")]]
        ))


@router.callback_query(F.data.startswith("l1_reject_"), IsReviewerL1())
async def reject_request(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    # Защита от l1_reject_all_
    if callback.data.startswith("l1_reject_all_"):
        return
    req_id = callback.data.replace("l1_reject_", "")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_reject_reason_new", lang), callback_data=f"l1_rj_reason_{req_id}_new_tech")],
        [InlineKeyboardButton(text=_("btn_reject_reason_crit", lang), callback_data=f"l1_rj_reason_{req_id}_criteria")],
        [InlineKeyboardButton(text=_("btn_nav_prev", lang), callback_data=f"l1_detail_{req_id}")],
    ])
    await _safe_edit(callback, _("l1_choose_rj_reason", lang), kb, parse_mode=None)


@router.callback_query(F.data.startswith("l1_rj_reason_"), IsReviewerL1())
async def reject_with_reason(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    parts = callback.data.replace("l1_rj_reason_", "").split("_", 1)
    req_id = int(parts[0])
    reason_key = parts[1]

    reasons = {
        "new_tech": "Техника новая, замена не требуется",
        "criteria": "Не соответствует критериям замены",
    }

    req = await session.get(Request, req_id)
    if not req or req.status != RequestStatus.new:
        await callback.answer(_("alert_already_processed", lang), show_alert=True)
        return

    req.status = RequestStatus.closed
    req.final_decision = FinalDecision.rejected
    req.reject_reason = reasons.get(reason_key, reason_key)
    req.l1_reviewer_tg_id = callback.from_user.id
    req.closed_at = datetime.now(timezone.utc)
    await session.commit()

    await callback.answer(_("alert_rejected", lang), show_alert=True)

    region = await _get_reviewer_region(session, callback.from_user.id, state)
    remaining = await _get_new_requests(session, region)
    if remaining:
        sorted_reqs = _sorted_by_priority(remaining)
        await _show_compact_card(callback, sorted_reqs, 0, session, lang=lang)
    else:
        await _safe_edit(callback, _("l1_all_done", lang), None)


# ══════════════════════════════════════════════════════════════════════════
# МАССОВЫЕ ОПЕРАЦИИ С ПОДТВЕРЖДЕНИЕМ
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("l1_confirm_approve_all_"), IsReviewerL1())
async def confirm_approve_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    """Диалог подтверждения массового одобрения."""
    bhm_code = callback.data.replace("l1_confirm_approve_all_", "")
    requests = await _get_new_by_branch(session, bhm_code)
    count = len(requests)
    branch_name = requests[0].branch_name_snapshot if requests else bhm_code

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("btn_yes_approve", lang, count=count), callback_data=f"l1_approve_all_{bhm_code}"),
            InlineKeyboardButton(text=_("btn_no_cancel", lang), callback_data=f"l1_branch_{bhm_code}"),
        ]
    ])
    await _safe_edit(callback, _("l1_confirm_approve", lang, count=count, branch=branch_name), kb)


@router.callback_query(F.data.startswith("l1_confirm_reject_all_"), IsReviewerL1())
async def confirm_reject_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    """Диалог подтверждения массового отклонения."""
    bhm_code = callback.data.replace("l1_confirm_reject_all_", "")
    requests = await _get_new_by_branch(session, bhm_code)
    count = len(requests)
    branch_name = requests[0].branch_name_snapshot if requests else bhm_code

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_("btn_yes_reject", lang, count=count), callback_data=f"l1_reject_all_{bhm_code}"),
            InlineKeyboardButton(text=_("btn_no_cancel_arr", lang), callback_data=f"l1_branch_{bhm_code}"),
        ]
    ])
    await _safe_edit(callback, _("l1_confirm_reject", lang, count=count, branch=branch_name), kb)


@router.callback_query(F.data.startswith("l1_approve_all_"), IsReviewerL1())
async def approve_all_branch(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    bhm_code = callback.data.replace("l1_approve_all_", "")
    requests = await _get_new_by_branch(session, bhm_code)
    count = 0
    for r in requests:
        r.status = RequestStatus.approved_l1
        r.l1_reviewer_tg_id = callback.from_user.id
        count += 1
    await session.commit()

    await _safe_edit(callback, f"✅ Одобрено *{count}* заявок по *{bhm_code}*", InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_back_branches", lang), callback_data="l1_branches")]]
    ))


@router.callback_query(F.data.startswith("l1_reject_all_"), IsReviewerL1())
async def reject_all_branch(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    bhm_code = callback.data.replace("l1_reject_all_", "")
    requests = await _get_new_by_branch(session, bhm_code)
    count = 0
    for r in requests:
        r.status = RequestStatus.closed
        r.final_decision = FinalDecision.rejected
        r.reject_reason = "Массовый отказ L1"
        r.l1_reviewer_tg_id = callback.from_user.id
        r.closed_at = datetime.now(timezone.utc)
        count += 1
    await session.commit()

    await _safe_edit(callback, f"❌ Отклонено *{count}* заявок по *{bhm_code}*", InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_back_branches", lang), callback_data="l1_branches")]]
    ))
