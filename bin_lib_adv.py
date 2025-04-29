# File: bin_lib_adv.py

# Importa le funzioni o classi necessarie dai file di libreria
# In questo file avanzato, useremo direttamente Client da python-binance per i dati grezzi
# e potremmo importare funzioni di base da binance_lib.py se necessario per calcoli combinati
# Ad esempio, get_binance_price_pb potrebbe servire qui, ma per il solo volume non serve.
# Mantengo l'importazione di Client che serve per get_klines.
from binance.client import Client

# Se in futuro avessimo bisogno, ad esempio, di chiamare get_moving_averages da qui:
# from binance_lib import get_moving_averages


# --- Funzioni Avanzate di Analisi ---

def get_current_volume(symbol: str) -> float | None:
    """
    Recupera il volume scambiato nel giorno corrente (candela non chiusa) da Binance.

    Args:
        symbol: Il simbolo della coppia di trading (es. 'ETHUSDT').

    Returns:
        Il volume attuale come float, o None in caso di errore o dati mancanti.
    """
    try:
        client = Client("", "") # Inizializza il client (nessuna chiave API necessaria per dati pubblici)

        # Ottieni l'ultima candela (quella relativa al giorno corrente)
        # Usiamo intervallo '1d' e limite 1 per ottenere solo la candela del giorno attuale
        klines = client.get_klines(symbol=symbol.upper(), interval='1d', limit=1)

        # get_klines con limit=1 restituisce una lista contenente 0 o 1 candela.
        # Se la lista è vuota, non ci sono dati disponibili per quel simbolo/intervallo oggi.
        if not klines or len(klines) == 0:
            # Questo può succedere per simboli non validi o problemi API
            print(f"DEBUG: Nessun dato kline trovato per il giorno corrente per {symbol}.")
            return None

        # La risposta è una lista di liste. klines[0] è la singola candela.
        # Ogni candela è una lista: [ Open time, Open, High, Low, Close, Volume, Close time, ... ]
        # L'elemento con indice 5 è il volume scambiato in quel periodo.
        volume_str = klines[0][5]

        # Converti il volume da stringa a float
        current_volume = float(volume_str)
        return current_volume

    except Exception as e:
        # Cattura qualsiasi errore durante la chiamata API, il parsing della risposta o la conversione
        print(f"Errore nel recupero del volume corrente per {symbol}: {e}")
        return None


# --- Qui aggiungeremo altre funzioni avanzate (Volume Medio, Bande di Bollinger, RSI, ecc.) ---

# Esempio di struttura per la media storica dei volumi (la implementeremo dopo)
# def get_average_historical_volume(symbol: str, lookback_period: int) -> float | None:
#     """
#     Calcola il volume medio delle ultime N giornate chiuse.
#     """
#     pass # Placeholder


# --- Nuova Funzione: Volume Medio Storico ---
def get_average_historical_volume(symbol: str, lookback_period: int) -> float | None:
    """
    Calcola il volume medio di scambio degli ultimi N giorni (candele chiuse) da Binance.

    Args:
        symbol: Il simbolo della coppia di trading.
        lookback_period: Il numero di giorni (candele chiuse) su cui calcolare la media.

    Returns:
        Il volume medio storico come float, o None in caso di errore o dati insufficienti.
    """
    if lookback_period <= 0:
        print("Errore: Il lookback period per il volume medio deve essere positivo.")
        return None

    try:
        client = Client("", "")

        # Per calcolare la media su N giorni CHIUSI, dobbiamo chiedere N+1 candele.
        # Questo perché get_klines(limit=N) include la candela corrente non chiusa.
        # Chiedendo N+1 e scartando l'ultima, otteniamo le N candele CHIUSE precedenti.
        klines = client.get_klines(symbol=symbol.upper(), interval='1d', limit=lookback_period + 1)

        # Controlliamo se abbiamo ricevuto abbastanza candele per avere almeno 'lookback_period' CHIUSE
        if not klines or len(klines) < lookback_period + 1:
            print(f"Dati storici insufficienti per volume medio {lookback_period}d per {symbol}. Trovati {len(klines) if klines else 0} giorni.")
            # Se ci sono meno di N+1 candele, significa che l'asset è listato da meno di N giorni
            # o c'è stato un problema API. Potremmo comunque calcolare la media sui dati disponibili
            # in una versione più robusta, ma per ora richiediamo N giorni pieni.
            return None

        # Estraiamo i volumi dalle candele *chiuse*.
        # Klines[:-1] prende tutti gli elementi tranne l'ultimo (la candela corrente non chiusa).
        # L'elemento con indice 5 in ogni candela è il volume.
        closing_volumes = [float(kline[5]) for kline in klines[:-1]]

        # Calcola la media aritmetica dei volumi chiusi
        average_volume = sum(closing_volumes) / len(closing_volumes) # len(closing_volumes) sarà lookback_period

        print("Candele analizzate: " + len(closing_volumes))

        return average_volume

    except Exception as e:
        # Cattura errori API o altri problemi
        print(f"Errore nel calcolo del volume medio storico per {symbol}: {e}")
        return None


# --- Nuova Funzione: Genera Segnale Volume ---
def generate_volume_signal(current_volume: float | None, avg_volume: float | None, high_threshold_factor: float = 1.5, low_threshold_factor: float = 0.7) -> str:
    """
    Genera un segnale basato sul confronto tra il volume corrente e il volume medio storico,
    ma mappato ai termini "RIALZISTA", "RIBASSISTA", "STABILE" come richiesto.

    Args:
        current_volume: Il volume scambiato nel giorno corrente (finora).
        avg_volume: Il volume medio storico su un periodo definito.
        high_threshold_factor: Fattore moltiplicativo dell'avg_volume. Volume corrente > media * fattore -> "Volume Alto".
        low_threshold_factor: Fattore moltiplicativo dell'avg_volume. Volume corrente < media * fattore -> "Volume Basso".
        (Tra le due soglie è "Volume Nella Media").

    Returns:
        Una stringa: "RIALZISTA" (se volume alto), "RIBASSISTA" (se volume basso), "STABILE" (se volume nella media),
        o un messaggio di errore/stato.
    """
    # Controlla se i dati volume sono validi
    if current_volume is None or avg_volume is None:
        return "Dati Volume non disponibili"

    # Evita divisione per zero se la media è 0 o negativa (impossibile per volume reale)
    if avg_volume <= 0:
         # Consideriamo STABILE un volume medio non positivo, non possiamo fare confronti significativi
         return "STABILE"

    # Confronta il volume corrente con la media storica usando i fattori soglia
    if current_volume > avg_volume * high_threshold_factor:
        # Se il volume attuale è significativamente *sopra* la media
        return "RIALZISTA" # Mappato come richiesto dall'utente per "Volume Alto"

    elif current_volume < avg_volume * low_threshold_factor:
        # Se il volume attuale è significativamente *sotto* la media
        return "RIBASSISTA" # Mappato come richiesto dall'utente per "Volume Basso"

    else:
        # Se il volume attuale è tra le due soglie (né significativamente alto né basso)
        return "STABILE" # Mappato come richiesto dall'utente per "Volume Nella Media"

    # NOTA IMPORTANTE: Ribadiamo che questa mappatura ("Volume Alto" -> RIALZISTA, ecc.)
    # è una semplificazione specifica richiesta e NON è la standard analisi del volume nel trading.
    # Nell'analisi standard, il volume è un indicatore di *conferma* della tendenza di prezzo.
    # Un volume alto è rialzista se accompagna un aumento del prezzo, e ribassista se accompagna una diminuzione del prezzo.
    # Qui stiamo solo valutando il *livello* del volume odierno rispetto alla sua media passata.


# --- Blocco di test per l'esecuzione diretta del file ---
if __name__ == "__main__":
    print("--- Test Modulo Binance Lib Adv ---")

    # Test per la funzione get_current_volume (già presente e aggiornata per la formattazione)
    test_symbol_volume = "ETHUSDT"
    print(f"Recupero volume corrente per {test_symbol_volume}...")
    volume_oggi = get_current_volume(test_symbol_volume)
    if volume_oggi is not None:
        # Formattazione personalizzata (punto in alto per migliaia, punto per decimali)
        formatted_volume_final = f"{volume_oggi:,.2f}".replace(",", "˙")
        print(f"Volume scambiato oggi (finora) per {test_symbol_volume}: {formatted_volume_final}")
    else:
        print(f"Non è stato possibile ottenere il volume corrente per {test_symbol_volume}.")

    print("-" * 20)

    # Nuovo Test SPECIFICO per l'analisi completa del Volume e il suo segnale
    test_symbol_volume_analysis = "ETHUSDT"
    volume_avg_lookback = 3 # Periodo per la media del volume storico (es. 30 giorni)

    print(f"Analisi volume completa per {test_symbol_volume_analysis} (media su {volume_avg_lookback}gg)...")

    # 1. Recupera il volume corrente (riutilizziamo la variabile se già ottenuta per lo stesso simbolo, altrimenti la richiamiamo)
    volume_oggi_analysis = volume_oggi if (volume_oggi is not None and test_symbol_volume == test_symbol_volume_analysis) else get_current_volume(test_symbol_volume_analysis)

    # 2. Calcola il volume medio storico
    avg_volume_history = get_average_historical_volume(test_symbol_volume_analysis, volume_avg_lookback)

    # 3. Genera il segnale volume
    # Definiamo qui le soglie per il test (puoi modificarle)
    high_factor = 1.5 # Es: volume oggi > 1.5 * media -> RIALZISTA volume-wise
    low_factor = 0.7  # Es: volume oggi < 0.7 * media -> RIBASSISTA volume-wise

    volume_signal = generate_volume_signal(volume_oggi_analysis, avg_volume_history, high_factor, low_factor)

    # 4. Stampa i risultati del test
    if volume_oggi_analysis is not None:
         print(f"  Volume scambiato oggi (finora): {f'{volume_oggi_analysis:,.2f}'.replace(',', '˙')}")
    else:
         print("  Volume scambiato oggi (finora): Non disponibile.")

    if avg_volume_history is not None:
        print(f"  Volume medio ultimi {volume_avg_lookback} giorni: {f'{avg_volume_history:,.2f}'.replace(',', '˙')}")
    else:
        print(f"  Volume medio ultimi {volume_avg_lookback} giorni: Non disponibile.")

    print(f"\n  Segnale Volume (mapping richiesto): **{volume_signal}**") # Stampiamo il segnale generato

    print("-" * 20)

    # Puoi aggiungere test per scenari specifici (es. simulando volumi diversi)
    # print("\n--- Test Segnale Volume (Valori Fittizi) ---")
    # print(f"Vol Oggi: 150, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(150, 100, 1.5, 0.7)}") # 150 > 100 * 1.5 (False)
    # print(f"Vol Oggi: 151, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(151, 100, 1.5, 0.7)}") # 151 > 100 * 1.5 (True) -> RIALZISTA
    # print(f"Vol Oggi: 69, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(69, 100, 1.5, 0.7)}")  # 69 < 100 * 0.7 (False)
    # print(f"Vol Oggi: 70, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(70, 100, 1.5, 0.7)}")  # 70 < 100 * 0.7 (False) -> STABILE
    # print(f"Vol Oggi: 0, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(0, 100, 1.5, 0.7)}") # 0 < 100 * 0.7 (True) -> RIBASSISTA
    # print(f"Vol Oggi: None, Media: 100, Soglie: 1.5/0.7 -> Segnale: {generate_volume_signal(None, 100)}") # Dati non disponibili