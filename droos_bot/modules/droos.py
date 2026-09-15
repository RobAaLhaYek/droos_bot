"""Droos handler module."""



import re

from typing import Any



from telegram import Update

from telegram.ext import ContextTypes, MessageHandler, filters



from droos_bot import DATA_COLUMNS, LECTURE_COMPONENTS, application, sheet

from droos_bot.modules.start import start_handler

from droos_bot.utils.analytics import add_new_chat_to_db, analysis

from droos_bot.utils.keyboards import create_keyboard

from droos_bot.utils.telegram import tg_exceptions_handler





COMPONENTS_KEYS = {

    value.lower(): key

    for key, value in LECTURE_COMPONENTS.items()

}





def extract_links(value: Any) -> list[str]:

    """Extract one or more URLs from a Google Sheet cell."""



    if value is None:

        return []



    text = str(value).strip()



    if not text or text.lower() == "nan":

        return []



    links = re.findall(r"https?://[^\s,;]+", text)



    return [

        link.rstrip(").,;]")

        for link in links

    ]





def is_telegram_link(link: str) -> bool:

    """Check whether a URL points to a Telegram message."""



    return bool(

        re.match(

            r"^https?://(?:www\.)?(?:t\.me|telegram\.me)/",

            link,

            re.IGNORECASE,

        )

    )





async def parse_telegram_link(

    telegram_link: str,

) -> tuple[int, int]:

    """Convert a Telegram message URL to chat_id and message_id."""



    clean_link = telegram_link.rstrip("/")

    parts = clean_link.split("/")



    if len(parts) < 2:

        raise ValueError("Invalid Telegram link")



    message_id = int(parts[-1])

    telegram_chat = parts[-2]



    # Private Telegram channel format:

    # https://t.me/c/123456789/100

    if len(parts) >= 3 and parts[-3] == "c":

        telegram_chat_id = int(f"-100{telegram_chat}")

        return telegram_chat_id, message_id



    # Numeric chat ID

    if telegram_chat.startswith("-") or telegram_chat.isdigit():

        telegram_chat_id = int(telegram_chat)



    # Cached username

    elif application.bot_data.get("chats", {}).get(telegram_chat):

        telegram_chat_id = int(

            application.bot_data["chats"][telegram_chat]

        )



    # Telegram username

    else:

        telegram_chat_id = (

            await application.bot.get_chat(

                f"@{telegram_chat}"

            )

        ).id



        if application.bot_data.get("chats"):

            application.bot_data["chats"][

                telegram_chat

            ] = telegram_chat_id

        else:

            application.bot_data["chats"] = {

                telegram_chat: telegram_chat_id

            }



    return telegram_chat_id, message_id





@tg_exceptions_handler

@add_new_chat_to_db

async def handle_navigation(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE,

) -> None:

    message = update.effective_message



    assert message is not None

    assert message.text is not None



    user_data = context.user_data

    assert user_data is not None



    path = user_data.get("path")



    if not isinstance(path, list):

        path = []

        user_data["path"] = path



    query = message.text.lstrip("•").strip()

    page = 0



    # Main hierarchy button

    if query in DATA_COLUMNS.values():

        path.clear()

        user_data["path"] = path



    # Back

    elif query == "🔙 رجوع":

        if path:

            path.pop()



        if not path:

            return await start_handler(

                update,

                context,

            )



    # First / last page

    elif any(

        symbol in query

        for symbol in ("«", "»")

    ):

        page = 0 if "«" in query else -1



    # Pagination

    elif (

        query.startswith("🔶")

        or any(

            symbol in query

            for symbol in ("←", "→")

        )

        or (

            query.isdigit()

            and not message.text.startswith("•")

        )

    ):

        match = re.search(r"(\d+)", query)

        page = (

            int(match.group(1)) - 1

            if match

            else 0

        )



    # Search result

    elif " > " in query:

        path = query.split(" > ")

        user_data["path"] = path



    # Normal navigation

    else:

        path.append(query)



    current_level = sheet.navigate_hierarchy(path)



    if current_level is None:

        return await start_handler(

            update,

            context,

        )



    # Reached lecture

    if "__data" in current_level:

        path_text = " > ".join(path)



        available_components = []



        for key, value in LECTURE_COMPONENTS.items():

            if extract_links(

                current_level.get(key)

            ):

                available_components.append(value)



        await message.reply_text(

            f"📍 <b>{path_text}</b>",

            reply_markup=create_keyboard(

                available_components,

                show_back=True,

                show_pagination=False,

                show_bullet=False,

            ),

        )



    # Still browsing hierarchy

    else:

        title = " > ".join(path)



        if not title:

            title = "🎓 اختر السنة"



        await message.reply_text(

            title,

            reply_markup=create_keyboard(

                list(current_level.keys()),

                show_back=bool(path),

                current_page=page,

            ),

        )



    return None





@tg_exceptions_handler

@analysis

async def handle_resource_selection(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE,

) -> dict[str, Any] | None:

    message = update.effective_message



    assert message is not None

    assert message.text is not None



    user_data = context.user_data

    assert user_data is not None



    query = message.text.strip().lower()



    current_path = user_data.get("path")



    if not isinstance(current_path, list):

        current_path = []



    current_level = sheet.navigate_hierarchy(

        current_path

    )



    if (

        not current_level

        or not current_level.get("__data")

    ):

        await message.reply_text(

            "لم يتم العثور على المحاضرة المطلوبة."

        )

        await start_handler(update, context)

        return None



    component_key = COMPONENTS_KEYS.get(query)



    if not component_key:

        await message.reply_text(

            "لم يتم العثور على المورد المطلوب."

        )

        return None



    links = extract_links(

        current_level.get(component_key)

    )



    if not links:

        await message.reply_text(

            "هذا المورد غير متوفر حاليًا."

        )

        return None



    external_links: list[str] = []



    for link in links:

        if is_telegram_link(link):

            try:

                from_chat_id, message_id = (

                    await parse_telegram_link(link)

                )



                await application.bot.copy_message(

                    chat_id=message.chat_id,

                    from_chat_id=from_chat_id,

                    message_id=message_id,

                )



            except Exception as e:
                print("COPY ERROR:", repr(e))
                # If Telegram copying fails,

                # send the original URL instead.

                external_links.append(link)



        else:

            external_links.append(link)



    if external_links:

        if len(external_links) == 1:

            await message.reply_text(

                f"🔗 {external_links[0]}"

            )

        else:

            links_text = "\n\n".join(

                f"🔗 {index}. {link}"

                for index, link in enumerate(

                    external_links,

                    start=1,

                )

            )



            await message.reply_text(

                links_text

            )



    return current_level





# Resource buttons

resource_pattern = "^(" + "|".join(

    re.escape(value)

    for value in LECTURE_COMPONENTS.values()

) + ")$"



application.add_handler(

    MessageHandler(

        filters.ChatType.PRIVATE

        & filters.Regex(resource_pattern),

        handle_resource_selection,

    )

)





# Main hierarchy buttons

for (

    _data_column_id,

    _data_column_name,

) in DATA_COLUMNS.items():

    application.add_handler(

        MessageHandler(

            filters.ChatType.PRIVATE

            & filters.Regex(

                f"^{re.escape(_data_column_name)}$"

            ),

            handle_navigation,

        )

    )





# Navigation

application.add_handler(

    MessageHandler(

        filters.ChatType.PRIVATE

        & ~filters.COMMAND

        & filters.Regex(

            r"[«»←→🔶\d]|🔙 رجوع|•"

        ),

        handle_navigation,

    )

)
