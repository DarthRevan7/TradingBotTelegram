# File: telegram_interface.py

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio # Importa asyncio
import telegram_api_code as tapic

# Importa le funzioni necessarie dal tuo file di utilità Binance
# Assicurati che binance_lib.py sia nella stessa directory
from binance_lib import ( # <-- Importa le funzioni specifiche
    get_binance_price_pb,
    get_moving_averages,
    generate_crossover_signal,
    generate_breakout_signal
)

# SOSTITUISCI CON IL TUO TOKEN DEL BOT
BOT_TOKEN = tapic.API_CODE

# Configura il logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Parametri per le Analisi (puoi modificarli qui) ---
# Simbolo della criptovaluta (per ora fisso per questi pulsanti)
CRYPTO_SYMBOL = "ETHUSDT" # O un'altra coppia valida su Binance

# Parametri per Medie Mobili
SHORT_MA_PERIOD = 20
LONG_MA_PERIOD = 50
MA_PROXIMITY_THRESHOLD_PERCENT = 0.5

# Parametri per Breakout
BREAKOUT_LOOKBACK_PERIOD = 20

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia un messaggio di benvenuto con i tre pulsanti inline."""
    # Definisci la tastiera inline con i tre pulsanti
    # Ogni pulsante ha un testo visibile e una callback_data univoca
    keyboard = [
        [
            InlineKeyboardButton(f"{CRYPTO_SYMBOL} Info (Prezzo)", callback_data=f"get_price_{CRYPTO_SYMBOL}"),
        ],
        [
            InlineKeyboardButton("Segnale Moving AVG", callback_data=f"get_ma_signal_{CRYPTO_SYMBOL}"),
        ],
        [
            InlineKeyboardButton("Segnale Breakout", callback_data=f"get_breakout_signal_{CRYPTO_SYMBOL}"),
        ],
    ]

    # Crea l'oggetto InlineKeyboardMarkup
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Invia il messaggio con la tastiera
    await update.message.reply_text(
        "Seleziona l'informazione che desideri su " + CRYPTO_SYMBOL + ":",
        reply_markup=reply_markup # Allega la tastiera
    )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il click sui pulsanti inline e fornisce l'informazione specifica."""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    logger.info(f"Ricevuta callback_data: {callback_data}")

    # Inizializza il messaggio di risposta
    message_text = "..." # Messaggio di fallback

    # --- Ottieni l'evento loop corrente ---
    loop = asyncio.get_event_loop() # <-- AGGIUNTO QUI

    # --- Logica basata sul callback_data ---

    # 1. Pulsante "ETH Info" -> Prezzo attuale
    if callback_data == f"get_price_{CRYPTO_SYMBOL}":
        # Recupera il prezzo usando la funzione dal tuo modulo, eseguendola in un thread separato
        # Ora usiamo il 'loop' ottenuto prima
        price = await loop.run_in_executor( # <-- MODIFICATO QUI
            None, get_binance_price_pb, CRYPTO_SYMBOL
        )

        # Prepara il messaggio
        if price is not None:
            message_text = f"📈 Prezzo attuale di {CRYPTO_SYMBOL} su Binance: {price}"
        else:
            message_text = f"❌ Non è stato possibile ottenere il prezzo per {CRYPTO_SYMBOL}."

    # 2. Pulsante "Moving AVG" -> Segnale Crossover
    elif callback_data == f"get_ma_signal_{CRYPTO_SYMBOL}":
        # Recupera le medie mobili usando la funzione, eseguendola in un thread separato
        # Usiamo il 'loop' ottenuto prima
        short_ma, long_ma = await loop.run_in_executor( # <-- MODIFICATO QUI
            None, get_moving_averages, CRYPTO_SYMBOL, SHORT_MA_PERIOD, LONG_MA_PERIOD
        )

        # Genera il segnale crossover
        signal = generate_crossover_signal(short_ma, long_ma, MA_PROXIMITY_THRESHOLD_PERCENT)

        # Prepara il messaggio
        if signal.startswith("Dati MA non"): # Controlla sia l'errore dati non disponibili che non validi
             message_text = f"⚠️ Impossibile calcolare il segnale MA per {CRYPTO_SYMBOL}. {signal}."
        else:
             # Assicurati che i valori delle medie siano validi prima di stamparli
             ma_values_text = ""
             if short_ma is not None and long_ma is not None:
                  ma_values_text = f"\n  (SMA {SHORT_MA_PERIOD}d: {short_ma:.2f}, SMA {LONG_MA_PERIOD}d: {long_ma:.2f})"

             message_text = (
                f"📊 Segnale Moving Average ({SHORT_MA_PERIOD}d/{LONG_MA_PERIOD}d) per {CRYPTO_SYMBOL}:\n"
                f"  Segnale: **{signal}**" # Usiamo il grassetto per il segnale
                f"{ma_values_text}" # Aggiungi i valori solo se disponibili
             )


    # 3. Pulsante "Breakout Analysis" -> Segnale Breakout
    elif callback_data == f"get_breakout_signal_{CRYPTO_SYMBOL}":
         # Genera il segnale breakout, eseguendo la funzione in un thread separato
         # Usiamo il 'loop' ottenuto prima
         signal = await loop.run_in_executor( # <-- MODIFICATO QUI
             None, generate_breakout_signal, CRYPTO_SYMBOL, BREAKOUT_LOOKBACK_PERIOD
         )

         # Prepara il messaggio
         if signal.startswith("Errore") or signal == "Dati storici insufficienti per breakout":
              message_text = f"⚠️ Impossibile calcolare il segnale Breakout per {CRYPTO_SYMBOL}. {signal}."
         else:
              message_text = (
                f"💥 Segnale Breakout ({BREAKOUT_LOOKBACK_PERIOD}d) per {CRYPTO_SYMBOL}:\n"
                f"  Segnale: **{signal}**" # Usiamo il grassetto
              )


    # Modifica il messaggio originale (quello con i pulsanti) con la risposta specifica
    # ATTENZIONE: MarkdownV2 richiede l'escaping di certi caratteri se non fanno parte della sintassi Markdown.
    # Esempi: _ * [ ] ( ) ~ ` > # + - = | { } . ! \
    # Se i tuoi simboli crypto o numeri contengono questi caratteri, dovresti gestirli.
    # Per i simboli tipo "ETHUSDT" e numeri float, di solito non ci sono problemi.
    # Il problema maggiore sono . e ! nei numeri o testi liberi.
    # Se riscontri errori di parsing Markdown, la soluzione più semplice è rimuovere parse_mode='MarkdownV2'.
    try:
        await query.edit_message_text(
            text=message_text,
            reply_markup=query.message.reply_markup, # Mantiene la tastiera
            parse_mode='MarkdownV2' # Permette grassetto/emoji
        )
    except Exception as e:
        # Gestisci errori di editing, es. messaggio non modificabile o errori Markdown
        logger.error(f"Errore nell'editare il messaggio: {e}. Messaggio originale:\n{message_text}")
        # Riprova inviando un nuovo messaggio senza formattazione Markdown
        try:
            await query.message.reply_text(text=message_text)
        except Exception as e_reply:
             logger.error(f"Errore nell'inviare messaggio di fallback: {e_reply}")
             # Ultima risorsa: invia un messaggio di errore semplice
             await query.message.reply_text("Si è verificato un errore interno nel bot.")

# --- Funzione Principale per Avviare il Bot ---

def main() -> None:
    """Avvia il bot."""
    # Costruisci l'applicazione del bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Aggiungi gli handlers
    # Handler per il comando /start
    application.add_handler(CommandHandler("start", start))

    # Handler per i click sui pulsanti inline
    # Il pattern "^get_" cattura callback_data che iniziano con "get_"
    # Se aggiungerai altri callback_data che iniziano con "get_" ma non sono questi,
    # dovrai rendere il pattern più specifico (es. "^get_(price|ma_signal|breakout_signal)_")
    application.add_handler(CallbackQueryHandler(handle_button_click, pattern="^get_"))

    logger.info("Bot avviato. In polling...")
    # Avvia il bot in polling. run_polling blocca l'esecuzione.
    application.run_polling(poll_interval=3.0, timeout=10) # Aggiunto un timeout per run_polling

# --- Esegui la Funzione Principale ---
if __name__ == "__main__":
    main()