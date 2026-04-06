from aiogram.fsm.state import StatesGroup, State

class RegistrationForm(StatesGroup):
    waiting_for_bhm = State()


class RequestForm(StatesGroup):
    """FSM для заполнения заявки."""
    # Эти параметры мы храним в state.dialog_data
    # equipment_type = "computer" | "printer"
    # request_type = "replacement" | "new_issue" | "repair"
    # branch_id = int
    
    waiting_for_inventory_code = State()  # Пропускается при выдаче новой
    waiting_for_fio = State()
    waiting_for_position = State()
    waiting_for_reason = State()          # Причина замены/выдачи
    waiting_for_problem = State()         # Описание проблемы (только при поломке)


class ErrorReportForm(StatesGroup):
    """FSM для формы отправки ошибки разработчику."""
    waiting_for_error_text = State()


class StatusForm(StatesGroup):
    """FSM для поиска чужих заявок (опционально)."""
    waiting_for_fio_search = State()
