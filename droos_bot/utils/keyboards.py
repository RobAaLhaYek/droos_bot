from telegram import ReplyKeyboardMarkup

from telegram.constants import InlineKeyboardMarkupLimit



from droos_bot import CONFIG, DATA_COLUMNS





def create_keyboard(

    items: list[str],

    show_back: bool = True,

    show_pagination: bool = True,

    show_bullet: bool = True,

    current_page: int = 0,

    items_per_page: int = 10,

    max_pages_displayed: int = InlineKeyboardMarkupLimit.BUTTONS_PER_ROW - 3,

) -> ReplyKeyboardMarkup:

    """Create navigation keyboard with pagination."""



    total_pages = (len(items) + items_per_page - 1) // items_per_page



    if total_pages == 0:

        total_pages = 1



    if current_page < 0:

        current_page = total_pages - 1



    if current_page >= total_pages:

        current_page = total_pages - 1



    half_display = max_pages_displayed // 2



    start_page = max(

        1,

        current_page + 1 - half_display,

    )



    end_page = min(

        total_pages,

        start_page + max_pages_displayed - 1,

    )



    if (

        end_page - start_page + 1 < max_pages_displayed

        and start_page > 1

    ):

        start_page = max(

            1,

            end_page - max_pages_displayed + 1,

        )



    pagination: list[str] = []



    if show_pagination and total_pages > 1:

        if current_page > 0:

            pagination.append("«")



        for page in range(start_page, end_page + 1):

            if page == current_page + 1:

                pagination.append(f"🔶{page}")



            elif page < current_page + 1:

                pagination.append(f"←{page}")



            else:

                pagination.append(f"{page}→")



        if current_page < total_pages - 1:

            pagination.append("»")



    start_idx = current_page * items_per_page

    end_idx = start_idx + items_per_page



    keyboard = [

        [f"• {item}" if show_bullet else str(item)]

        for item in items[start_idx:end_idx]

    ]



    if pagination:

        keyboard.append(pagination)



    if show_back:

        keyboard.append(["🔙 رجوع"])



    return ReplyKeyboardMarkup(

        keyboard,

        resize_keyboard=True,

    )





def create_main_keyboard() -> list[list[str]]:

    """

    Main menu.



    Only show the first hierarchy level.

    With the current config this is:

    🎓 السنة

    """



    hidden = CONFIG.get("hide", [])



    visible_columns = [

        value

        for key, value in DATA_COLUMNS.items()

        if key not in hidden

    ]



    if not visible_columns:

        return []



    return [[visible_columns[0]]]





main_keyboard = ReplyKeyboardMarkup(

    create_main_keyboard(),

    resize_keyboard=True,

)





cancel_search_keyboard = ReplyKeyboardMarkup(

    [["🔙 رجوع"]],

    resize_keyboard=True,

)





cancel_keyboard = ReplyKeyboardMarkup(

    [["🔙 رجوع"]],

    resize_keyboard=True,

)