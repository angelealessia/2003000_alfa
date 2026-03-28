1. System Overview
Il sistema è una piattaforma di monitoraggio sismico distribuita e fault-tolerant progettata per il contesto geopolitico del 2038. Il sistema ingerisce dati grezzi da sensori remoti, li analizza nel dominio della frequenza per identificare minacce (terremoti, esplosioni o eventi nucleari) e garantisce la persistenza dei dati anche in caso di distruzione parziale dei centri di calcolo.
+3

2. User Stories (Target: 25)
Area: Ingestione e Distribuzione (Broker)

Come operatore di sistema, voglio che il Broker si connetta ai WebSocket dei sensori per ricevere misurazioni in tempo reale.
+2

Come amministratore, voglio che il Broker distribuisca i dati a più repliche di calcolo contemporaneamente (broadcast).

Come responsabile della sicurezza, voglio che il Broker risieda in una regione neutrale eseguendo solo il routing leggero dei dati.
+2

Come sviluppatore, voglio che il Broker sia in grado di scoprire i sensori disponibili tramite l'endpoint /api/devices/.

Come sistema, voglio ricevere i campionamenti a una frequenza di 20 Hz per garantire la precisione dell'analisi.

Area: Elaborazione e Analisi (Processing)

Come analista militare, voglio che il sistema applichi la trasformata di Fourier (FFT) per identificare la frequenza dominante dei segnali.

Come utente, voglio che il sistema utilizzi una finestra scorrevole (sliding window) per analizzare i segnali recenti.

Come comandante, voglio che un evento sia classificato come "Earthquake" se la frequenza è tra 0.5 e 3.0 Hz.

Come comandante, voglio che un evento sia classificato come "Conventional Explosion" se la frequenza è tra 3.0 e 8.0 Hz.

Come comandante, voglio ricevere un'allerta "Nuclear-like event" per frequenze superiori o uguali a 8.0 Hz.

Come sviluppatore, voglio che ogni replica rimanga in ascolto del flusso di controllo SSE per gestire i segnali di arresto.

Come sistema, voglio che una replica si spenga immediatamente (forced shutdown) al ricevimento del comando "SHUTDOWN".

Area: Persistenza e De-duplicazione

Come data scientist, voglio che tutti gli eventi rilevati siano salvati in un database condiviso (Postgres/MongoDB).

Come amministratore di sistema, voglio che il database ignori i duplicati se più repliche inviano lo stesso evento.
+1

Come utente, voglio che ogni evento salvato includa il timestamp UTC e l'ID del sensore di origine.
+1

Come analista, voglio poter consultare lo storico di tutti gli eventi sismici passati tramite la dashboard.

Area: Fault Tolerance e Gateway

Come utente frontend, voglio accedere al sistema tramite un unico entry point (Gateway) che smisti le richieste.

Come amministratore, voglio che il Gateway esegua health check automatici sulle repliche di calcolo.

Come sistema, voglio che le repliche non raggiungibili siano rimosse automaticamente dal bilanciamento.

Come utente, voglio che il sistema continui a funzionare regolarmente anche se alcune repliche falliscono.

Area: Dashboard e Visualizzazione

Come operatore, voglio vedere i nuovi eventi apparire in tempo reale sulla dashboard tramite WebSocket o SSE.
+1

Come analista, voglio filtrare gli eventi per tipologia (es. solo nucleari).

Come analista, voglio filtrare gli eventi in base alla posizione geografica del sensore.

Come utente, voglio un'interfaccia web intuitiva per monitorare lo stato di salute dei sensori.

Come sviluppatore, voglio poter avviare l'intero ambiente di monitoraggio con un singolo comando docker compose up.

3. Event Schema
Ogni misurazione ricevuta dal broker seguirà questo schema:

sensor_id: stringa identificativa univoca.

timestamp: data e ora in formato UTC.

value: valore della vibrazione in mm/s.

4. Rule Model
La classificazione avviene secondo le seguenti soglie di frequenza dominante (f):

Earthquake: 0.5≤f<3.0 Hz.

Explosion: 3.0≤f<8.0 Hz.

Nuclear: f≥8.0 Hz.
