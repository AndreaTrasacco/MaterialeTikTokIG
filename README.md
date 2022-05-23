# MaterialeTikTokIG

## Descrizione
Il materiale inserito in questa repository serve allo scopo di implementare il campionamento di un certo numero di utenti da TikTok e Instagram su una macchina Linux.

- <tiktok_ig.py> è lo script che effettua il campionamento degli utenti, al suo interno è presente la variabile <absolute_path> da modificare con il path assoluto della directory che contiene lo script
- <id_users.pkl> contiene id e nickname di circa 11k utenti TikTok ed è usato dallo script <tiktok_ig.py>, deve trovarsi nella stessa directory di tale script
- <crontask.py> è lo script che inserisce il comando di eseguire il campionamento all'interno della "crontab" di un utente della macchina, utente e comando si possono modificare nello script (oltre ovviamente all'orario di partenza e frequenza del campionamento)
- <ig_accounts.txt> contiene gli account Instagram usati nel campionamento, si consiglia di creare altri account per effettuare il campionamento e modificare la corrispondente struttura dati in <tiktok_ig.py>.

## Librerie da installare:

Eseguire i seguenti comandi sotto l'utente che dovrà eseguire il campionamento (si suppone installato python3)

- python3 -m pip install sys
- python3 -m pip install requests==2.27.1
- python3 -m pip install elasticsearch==8.2.0
- python3 -m pip install TikTokApi==5.0.0
- python3 -m pip install instagrapi==1.16.17
- python3 -m pip install Pillow==9.1.0
- playwright install (ed eventualmente: playwright install-deps)
- pip install python-crontab==2.6.0
- copiare i file modifiche_TikTokApi/tiktok.py e modifiche_TikTokApi/user.py nelle apposite cartelle della liberia python TikTokApi (per trovare il percorso in cui questa libreria è stata installata, eseguire $ python3 -m pip show TikTokApi)

## Istruzioni:

1. Scaricare in una directory a piacere la repository con <git clone https://github.com/AndreaTrasacco/MaterialeTikTokIG.git>
2. Eseguire i comandi di installazione
3. Modificare opportunamente la variabile absolute_path nel file <tiktok_ig.py> (eventualmente anche altre variabili come per esempio <es_address> se serve)
4. Dopo aver modificato utente, path, orario del crontask nello script <crontask.py> eseguire tale script tramite "python3 crontask.py"

## Ulteriori informazioni

- Lo script <tiktok_ig.py> è attualmente impostato per effettuare il campionamento di 5000 utenti (modificare main_info() per cambiare tale valore)
- Al termine dell'esecuzione, <tiktok_ig.py>, produce e salva nella directory dove si trova tale script, il file <ig_accounts_to_verify.json> che contiene gli account che sono stati temporaneamente bloccati durante il campionamento, serve accedere manualmente con tali account su Instagram al fine di sbloccarli e, se richiesto il cambio della passoword, aggiornare la password in <ig_accounts.txt> e <tiktok_ig.py> (lista ig_passwords)

