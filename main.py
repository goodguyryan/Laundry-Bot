import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    JobQueue,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

#Initialise variables to be used later
START_ROUTES, LOAD_ROUTES = range(2)
STATUS, LOAD = range(2)
W1, W2, D1, D2 = range(4)

#Create a class Machine 
class Machine:
    def __init__(self, name, timeleft) -> None:
        self.name = name
        self.timeleft = timeleft
        self.in_use = False

#Dictionary to hold my laundry machines
machines = {
    'washer1': Machine("W1", 0),
    'washer2': Machine("W2", 0),
    'dryer1' : Machine("D1", 0),
    'dryer2' : Machine("D2", 0),
}

#Start command to create inline keyboard(buttons) for user to press
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s started the bot", user.first_name)
    keyboard = [
        [
            InlineKeyboardButton("Status", callback_data=str(STATUS)),
            InlineKeyboardButton("Load", callback_data=str(LOAD))
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What would you like to do?", reply_markup=reply_markup)

    return START_ROUTES

#Status function (To check status of machines)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Generate status messages for all machines
    status_messages = []
    for key, machine in machines.items():
        if machine.timeleft <= 0:
            status_messages.append(f"{machine.name} is empty")
        else:
            status_messages.append(f"{machine.name} has {machine.timeleft//60 + 1} minutes left")
    
    status_text = "\n".join(status_messages)
    await query.edit_message_text(status_text)

#Load function (to update status of Machine)
async def load(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("W1", callback_data=str(W1)),
            InlineKeyboardButton("W2", callback_data=str(W2)),
        ],
        [
            InlineKeyboardButton("D1", callback_data=str(D1)),
            InlineKeyboardButton("D2", callback_data=str(D2)),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Which machine would you like to load?", reply_markup=reply_markup
    )
    return LOAD_ROUTES

#Countdown function that countdowns the time left if machine in use
async def countdown(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job #Create job queue
    machine_key = job.data['machine_key']
    chat_id = job.data['chat_id']
    machine = machines[machine_key]
    
    while machine.timeleft > 0:
        await asyncio.sleep(1)
        machine.timeleft -= 1
    
    # Notify that the countdown is complete
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{machine.name} has completed its countdown. {machine.name} moving in 5."
    )
    
    # Mark the machine as not in use after countdown completes
    machine.in_use = False

#Start countdown of any machine when Load
async def start_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE, machine_key: str) -> int:
    query = update.callback_query
    await query.answer()
    
    machine = machines[machine_key]
    
    #Prevent double loading
    if machine.in_use:
        await query.edit_message_text(f"{machine.name} is already in use. Please wait until the current countdown is finished.")
        return LOAD_ROUTES
    
    machine.timeleft = 1800
    machine.in_use = True  
    await query.edit_message_text(f"{machine.name} Loaded! Countdown started.")
    
    # Start the countdown in the background
    context.job_queue.run_once(
        countdown,
        when=0,
        data={
            'chat_id': update.effective_chat.id,
            'machine_key': machine_key
        }
    )
    
    return LOAD_ROUTES

#Button that starts countdown of respective machines
async def w1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_countdown(update, context, 'washer1')

async def w2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_countdown(update, context, 'washer2')

async def d1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_countdown(update, context, 'dryer1')

async def d2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_countdown(update, context, 'dryer2')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(status, pattern="^" + str(STATUS) + "$"),
                CallbackQueryHandler(load, pattern="^" + str(LOAD) + "$"),
            ],
            LOAD_ROUTES: [
                CallbackQueryHandler(w1, pattern="^" + str(W1) + "$"),
                CallbackQueryHandler(w2, pattern="^" + str(W2) + "$"),
                CallbackQueryHandler(d1, pattern="^" + str(D1) + "$"),
                CallbackQueryHandler(d2, pattern="^" + str(D2) + "$"),
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()