"""
Утилиты нормализации и транслитерации ФИО.

Правила:
1. normalize_basic  — trim, collapse spaces, lower-case.
2. translit_to_cyrillic — O'zbekcha латиница → кириллица.
3. normalize_translit — normalize_basic + translit → каноническая форма.

Если после транслитерации строки совпадают, считаем что это один человек.
Если нет — это разные люди.
"""

import re

# ── Таблица транслитерации (O'zbekcha lotin → кириллица) ────────────────
# Порядок ВАЖЕН: многобуквенные комбинации первыми!
_TRANSLIT_MAP: list[tuple[str, str]] = [
    # Диграфы и спец. символы (сначала длинные)
    ("sh", "ш"),
    ("ch", "ч"),
    ("o'", "ў"),
    ("oʻ", "ў"),
    ("g'", "ғ"),
    ("gʻ", "ғ"),
    ("ng", "нг"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ye", "е"),
    ("ts", "ц"),
    # Одиночные буквы
    ("a", "а"),
    ("b", "б"),
    ("d", "д"),
    ("e", "е"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "ҳ"),
    ("i", "и"),
    ("j", "ж"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "қ"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("x", "х"),
    ("y", "й"),
    ("z", "з"),
    # Апострофы (тупой / умный) — убираем
    ("'", ""),
    ("ʻ", ""),
    ("'", ""),
    ("'", ""),
]


def normalize_basic(fio: str) -> str:
    """
    Базовая нормализация:
    - strip пробелов по краям
    - схлопывание множественных пробелов
    - lower-case
    """
    text = fio.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def translit_to_cyrillic(text: str) -> str:
    """
    Конвертирует O'zbekcha-латиницу в кириллицу.
    Предполагает, что текст уже lower-case.
    Кириллические символы остаются без изменений.
    """
    result = []
    i = 0
    while i < len(text):
        matched = False
        # Пробуем сначала двух- и трёхбуквенные комбинации
        for latin, cyrillic in _TRANSLIT_MAP:
            ln = len(latin)
            if text[i: i + ln] == latin:
                result.append(cyrillic)
                i += ln
                matched = True
                break
        if not matched:
            result.append(text[i])
            i += 1
    return "".join(result)


def normalize_translit(fio: str) -> str:
    """
    Каноническая нормализация:
    - базовая нормализация
    - транслитерация латиницы → кириллица
    Результат = fio_normalized_translit
    """
    basic = normalize_basic(fio)
    return translit_to_cyrillic(basic)


# ── Удобные функции для создания обоих полей сразу ──────────────────────

def compute_fio_fields(fio_raw: str) -> tuple[str, str]:
    """
    Возвращает (fio_normalized_basic, fio_normalized_translit).

    Использовать при создании/обновлении заявок.
    """
    basic = normalize_basic(fio_raw)
    translit = translit_to_cyrillic(basic)
    return basic, translit
