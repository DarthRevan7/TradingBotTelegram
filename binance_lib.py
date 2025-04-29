from binance.client import Client
def get_binance_price_pb(symbol: str) -> float | None:
    """
    Recupera il prezzo attuale di una criptovaluta da Binance usando python-binance.

    Args:
        symbol: Il simbolo della coppia di trading (es. 'ETHUSDT').

    Returns:
        Il prezzo attuale come float, o None se c'è un errore o il simbolo non è valido.
    """
    # Le chiavi API non sono necessarie per accedere ai dati di mercato pubblici
    # Puoi istanziare il client senza API key e Secret per questi scopi.
    try:
        # Inizializza il client di Binance
        # Se avessi bisogno di dati utente o trading, metteresti qui la tua API key e Secret
        client = Client("", "") # Lasciamo vuoto per accesso pubblico

        # Ottieni il ticker per il simbolo specificato
        # La libreria gestisce la chiamata API HTTP per te
        ticker = client.get_symbol_ticker(symbol=symbol.upper()) # Simbolo in maiuscolo

        # La risposta è un dizionario {'symbol': '...', 'price': '...'}
        if ticker and 'price' in ticker:
            return float(ticker['price'])
        else:
            # Questo caso si verifica se il simbolo non è valido; get_symbol_ticker potrebbe sollevare un'eccezione
            # o restituire una struttura inaspettata in caso di errore API non gestito internamente.
            # Le eccezioni sono gestite nel blocco except.
            print(f"Risposta API inaspettata per simbolo {symbol}: {ticker}")
            return None

    except Exception as e:
        # python-binance solleva eccezioni specifiche in caso di problemi (es. BinanceAPIException per errori API)
        # Qui catturiamo un'eccezione generica per semplicità
        print(f"Errore durante il recupero del prezzo con python-binance: {e}")
        return None

def get_binance_average_price_30d(symbol: str) -> float | None:
    """
    Calcola il prezzo medio di chiusura degli ultimi 30 giorni per una criptovaluta da Binance.

    Args:
        symbol: Il simbolo della coppia di trading (es. 'ETHUSDT').

    Returns:
        Il prezzo medio degli ultimi 30 giorni come float, o None in caso di errore.
    """
    try:
        client = Client("", "")

        # Ottieni gli ultimi 30 candele giornaliere ('1d')
        # Client.KLINE_INTERVAL_DAILY è una costante che vale '1d'
        klines = client.get_klines(symbol=symbol.upper(), interval="1d", limit=30)

        # get_klines può restituire una lista vuota se il simbolo non esiste o non ha dati per quell'intervallo/limite
        if not klines or len(klines) < 30:
            print(f"Dati storici insufficienti o non trovati per {symbol}. Trovati {len(klines) if klines else 0} giorni.")
            # Potresti restituire None o un messaggio più specifico
            return None

        # I dati klines sono una lista di liste. Il prezzo di chiusura è l'elemento con indice 4
        # Ogni elemento in klines è [ Open time, Open, High, Low, Close, Volume, Close time, ... ]
        closing_prices = [float(kline[4]) for kline in klines]

        # Calcola la media
        average_price = sum(closing_prices) / len(closing_prices)

        return average_price

    except Exception as e:
        # Gestione errori (es. simbolo non valido, problemi di rete/API)
        print(f"Errore in get_binance_average_price_30d per simbolo {symbol}: {e}")
        return None


def get_moving_averages(symbol: str, short_period: int, long_period: int) -> tuple[float | None, float | None]:
    """
    Calcola due medie mobili semplici (SMA) per una criptovaluta da Binance.

    Args:
        symbol: Il simbolo della coppia di trading (es. 'ETHUSDT').
        short_period: Il numero di giorni per la media mobile a breve termine.
        long_period: Il numero di giorni per la media mobile a lungo termine.

    Returns:
        Una tupla contenente (SMA_breve, SMA_lunga), o (None, None) in caso di errore
        o dati insufficienti.
    """
    # Validazione base dei periodi
    if short_period <= 0 or long_period <= 0 or short_period > long_period:
        print("Errore: i periodi delle medie mobili devono essere positivi e il periodo breve <= periodo lungo.")
        return None, None

    try:
        client = Client("", "")

        # Per calcolare sia la media breve che quella lunga, dobbiamo ottenere dati per il periodo più lungo.
        # Usiamo l'intervallo giornaliero ('1d').
        # Richiediamo esattamente 'long_period' candele per calcolare la SMA lunga su quel periodo.
        klines = client.get_klines(symbol=symbol.upper(), interval='1d', limit=long_period) # Usiamo '1d'

        # Controlliamo se abbiamo ricevuto il numero di candele richiesto
        if not klines or len(klines) < long_period:
            print(f"Dati storici insufficienti per calcolare SMA {long_period}d per {symbol}. Trovati {len(klines) if klines else 0} giorni.")
            return None, None

        # Estraiamo i prezzi di chiusura
        # Ogni kline è una lista; l'elemento con indice 4 è il prezzo di chiusura.
        closing_prices = [float(kline[4]) for kline in klines]

        # Calcola la SMA a lungo termine: media degli ultimi 'long_period' prezzi
        long_sma = sum(closing_prices) / len(closing_prices)

        # Per la SMA a breve termine: prendiamo solo gli ultimi 'short_period' prezzi
        # Usiamo lo slicing di lista: [inizio:fine]. [-short_period:] prende gli ultimi 'short_period' elementi.
        short_period_prices = closing_prices[-short_period:]

        # Calcola la SMA a breve termine
        short_sma = sum(short_period_prices) / len(short_period_prices)

        return short_sma, long_sma

    except Exception as e:
        print(f"Errore nel calcolo delle medie mobili per simbolo {symbol}: {e}")
        return None, None


def generate_crossover_signal(short_ma: float | None, long_ma: float | None, proximity_threshold_percent: float = 0.5) -> str:
    """
    Genera un segnale di trading (Rialzista, Ribassista, Hold) basato sul crossover di due medie mobili.

    Args:
        short_ma: Il valore della media mobile a breve termine.
        long_ma: Il valore della media mobile a lungo termine.
        proximity_threshold_percent: La percentuale di differenza (in valore assoluto rispetto alla MA lunga)
                                   al di sotto della quale le medie sono considerate "molto vicine" (segnale Hold).
                                   Default a 0.5 (0.5%).

    Returns:
        Una stringa: "Rialzista", "Ribassista", o "Hold", o "Dati MA non disponibili".
    """
    # Controlla se i dati delle medie sono validi
    if short_ma is None or long_ma is None:
        return "Dati MA non disponibili"
    
    # Evitiamo divisioni per zero se la media lunga fosse 0 (improbabile con prezzi crypto reali, ma buona pratica)
    if long_ma == 0:
         return "Dati MA non validi (MA lunga = 0)"

    # Calcola la differenza assoluta tra le medie
    difference = short_ma - long_ma

    # Calcola la differenza percentuale in valore assoluto rispetto alla media lunga
    # Questo ci serve per valutare la "vicinanza" indipendentemente dal segno della differenza
    relative_difference_percent = (abs(difference) / long_ma) * 100


    # Genera il segnale
    # Se la differenza percentuale è maggiore della soglia di vicinanza E...
    if relative_difference_percent > proximity_threshold_percent:
        # ... la media breve è sopra la lunga
        if difference > 0:
            return "Rialzista" # SMA breve è significativamente sopra SMA lunga
        # ... altrimenti (la media breve è sotto la lunga)
        else: # difference < 0
            return "Ribassista" # SMA breve è significativamente sotto SMA lunga
    else:
        # Se la differenza percentuale NON è maggiore della soglia, le medie sono considerate vicine
        # Questo include anche il caso in cui difference è esattamente 0.
        return "Hold"


def generate_breakout_signal(symbol: str, lookback_period: int) -> str:
    """
    Genera un segnale di breakout (Rialzista, Ribassista, Consolidamento)
    basato sui massimi/minimi degli ultimi N giorni.

    Args:
        symbol: Il simbolo della coppia di trading (es. 'ETHUSDT').
        lookback_period: Il numero di giorni indietro da considerare per massimi/minimi.

    Returns:
        Una stringa: "Breakout Rialzista", "Breakout Ribassista",
        "Consolidamento", o un messaggio di errore/stato.
    """
    # Validazione del lookback period
    if lookback_period <= 0:
        return "Errore: Il lookback period deve essere positivo."

    try:
        client = Client("", "")

        # Ottieni le candele giornaliere per il lookback period specificato.
        # Usiamo l'intervallo giornaliero ('1d').
        # Il limite ci dà le N candele più recenti.
        klines = client.get_klines(symbol=symbol.upper(), interval='1d', limit=lookback_period) # Usiamo '1d'

        # Controlla se abbiamo ricevuto esattamente il numero di candele richiesto
        # Potrebbe esserci meno dati per asset molto nuovi o problemi API
        if not klines or len(klines) < lookback_period:
            print(f"Dati storici insufficienti per breakout {lookback_period}d per {symbol}. Trovati {len(klines) if klines else 0} giorni.")
            return "Dati storici insufficienti per breakout"

        # Trova il prezzo massimo (High) e minimo (Low) nell'intero lookback period
        # Ogni kline è una lista: [ Open time, Open, High, Low, Close, Volume, Close time, ... ]
        # L'indice 2 è il prezzo High, l'indice 3 è il prezzo Low.
        # Inizializziamo con valori appropriati per trovare il vero max/min
        highest_high = 0.0
        lowest_low = float('inf') # Inizializziamo con un valore che è sicuramente maggiore di qualsiasi prezzo

        for kline in klines:
            try:
                high = float(kline[2])
                low = float(kline[3])

                if high > highest_high:
                    highest_high = high
                if low < lowest_low:
                    lowest_low = low
            except (ValueError, IndexError) as e:
                 print(f"Errore nel parsing di una riga kline: {kline}. Errore: {e}")
                 # Decidi come gestire kline malformate - qui le saltiamo
                 continue


        # Ottieni il prezzo attuale (usando la funzione esistente)
        current_price = get_binance_price_pb(symbol)

        if current_price is None:
            return "Errore nel recupero prezzo attuale per breakout"

        # Confronta il prezzo attuale con i livelli di supporto/resistenza trovati.
        # Consideriamo un breakout se il prezzo attuale supera strettamente il massimo/minimo del periodo.
        # N.B.: Nelle strategie reali, spesso si usa un piccolo buffer (%) o si aspetta la chiusura di candela
        # per filtrare i falsi breakout. Qui usiamo la logica più semplice: superamento netto.

        if current_price > highest_high:
            return "Breakout Rialzista"
        elif current_price < lowest_low:
            return "Breakout Ribassista"
        else:
            # Se non è né sopra il massimo né sotto il minimo, è nel range.
            return "Consolidamento"

    except Exception as e:
        # Cattura altri errori API o inattesi
        print(f"Errore nel calcolo del segnale di breakout per simbolo {symbol}: {e}")
        return f"Errore interno nel calcolo breakout."

# --- Blocco di test per l'esecuzione diretta del file ---
if __name__ == "__main__":
    print("--- Test Modulo Binance Lib ---")

    # ... (Test per prezzo attuale rimane come prima) ...
    # ... (Test per media 30gg rimane come prima) ...
    # ... (Test per medie mobili 20d/50d rimane come prima) ...

    print("-" * 20)

    # Nuovo Test SPECIFICO per il segnale di Breakout
    symbol_breakout_test = "ETHUSDT" # Scegli il simbolo
    lookback = 20 # Scegli il lookback period (es. ultimi 20 giorni)
    print(f"Recupero segnale di breakout ({lookback}d) per {symbol_breakout_test}...")

    breakout_signal = generate_breakout_signal(symbol_breakout_test, lookback)

    # **Opzionale:** Per rendere il test più informativo, recuperiamo e stampiamo i livelli di max/min trovati.
    # Notare che stiamo facendo di nuovo la chiamata API solo per scopi di visualizzazione nel test.
    try:
         client_test = Client("", "")
         klines_test_info = client_test.get_klines(symbol=symbol_breakout_test.upper(), interval='1d', limit=lookback)
         if klines_test_info and len(klines_test_info) == lookback:
            # Troviamo max High e min Low di nuovo per stamparli
            highest_high_test_info = max(float(k[2]) for k in klines_test_info)
            lowest_low_test_info = min(float(k[3]) for k in klines_test_info)
            current_price_test_info = get_binance_price_pb(symbol_breakout_test)

            print(f"  Periodo analizzato: ultimi {lookback} giorni.")
            print(f"  Massimo (Resistenza) in questo periodo: {highest_high_test_info:.2f}")
            print(f"  Minimo (Supporto) in questo periodo: {lowest_low_test_info:.2f}")
            if current_price_test_info is not None:
                 print(f"  Prezzo attuale: {current_price_test_info:.2f}")
            else:
                 print("  Prezzo attuale: Non disponibile.")

         else:
             print(f"  Impossibile recuperare dati storici ({lookback}d) per mostrare i livelli nel test.")

    except Exception as e:
         print(f"  Errore nel recupero dati per stampa livelli test breakout: {e}")


    print(f"\n  Segnale di Breakout ({lookback}d): {breakout_signal}")

    print("-" * 20)

    # Esempio con lookback invalidi per testare la gestione errori della funzione
    # print("\n--- Test Breakout con lookback invalidi ---")
    # generate_breakout_signal("BTCUSDT", 0)
    # generate_breakout_signal("BTCUSDT", -10)
