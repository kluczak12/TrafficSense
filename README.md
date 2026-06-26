
# TrafficSense

## Cel i zakres projektu

Celem projektu jest opracowanie kompleksowego systemu wykorzystującego model sieci neuronowej do wykrywania i przewidywania przyszłych intencji uczestników ruchu drogowego. System ten skupia się na predykcji niebezpiecznych zdarzeń ze strony pieszych (np. wtargnięcie na jezdnię), w celu zapobiegania kolizjom poprzez inicjalizację szybkiej, automatycznej reakcji ze strony samochodu, adekwatnej do zaistniałej sytuacji na drodze.

Za zakres projektu można uznać zagadnienia i cele szczegółowe, których poznanie i zaimplementowanie pozwoliło go wykonać. Takimi zagadnieniami są między innymi:

-   Konteneryzacja za pomocą Docker’a i architektura mikroserwisowa, 
-   Sieci neuronowe, a w szczególności zastosowanie modelu służącego do rozpoznawania ludzi na obrazie,
-   Zastosowanie bazy danych, wczytanie i agregacja zbioru danych z adnotacjami,
-   Wykorzystanie technologii  websocket  i REST API do komunikacji między mikroserwisami,
-   Opracowanie szybkiego protokołu wymiany klatek i statusów między przeglądarką, serwerem frontend-owym i silnikiem AI w oparciu o websockety,
-   Stworzenie logiki łączącej analizę i predykcję ruchu pieszego, jego pozycję i rozmiar względem kamery, oraz czynniki środowiskowe i otoczenie do określania stopnia zagrożenia zderzeniem,
-   Akceleracja sprzętowa - wykorzystanie mocy obliczeniowej karty graficznej NVIDIA z użyciem API  CUDA do obsługi sieci neuronowej

  

Źródło danych wykorzystanych w zadaniu: zbiór danych JAAD (Joint Attention in Autonomous Driving) 346 nagrań w formacie mp4 o długości ok. 5-10 sekund oraz adnotacji niezbędnych do predykcji zachowań, dostępny w http://data.nvision2.eecs.yorku.ca/JAAD_dataset/)



## Uruchomienie projektu

### Wymagania wstępne

- [Docker](https://www.docker.com/) oraz Docker Compose
- Karta graficzna NVIDIA z zainstalowanymi sterownikami oraz [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) (wymagane do akceleracji GPU)

### Struktura katalogów

Katalog `data/` powinien zawierać następujące podkatalogi z danymi ze zbioru [JAAD](http://data.nvision2.eecs.yorku.ca/JAAD_dataset/):

```
data/
├── videos/               # nagrania wideo (.mp4)
├── annotations/          # adnotacje JAAD
├── annotations_vehicle/  # adnotacje dotyczące pojazdów
└── annotations_traffic/  # adnotacje dotyczące infrastruktury drogowej
```

### Uruchomienie

```bash
docker compose up --build
```

Po zakończeniu budowania i uruchomienia kontenerów aplikacja dostępna jest pod adresem:

```
http://localhost:3000
```

Kontenery uruchamiają się w następującej kolejności: najpierw `data` (ładuje adnotacje do bazy SQLite i kończy pracę), następnie `engine` (silnik AI, port 8000) oraz `frontend` (interfejs użytkownika, port 3000).

---

**Zespół:** Klaudia Łuczak 251575, Hanna Dudek 251508, Julia Rzeźniczak 251624, Jakub Smyczyński 251631, Piotr Błaszczyk 251486 - IOAD 2

**Opiekun:** mgr inż. Krzysztof Stępień

**Repozytorium:** https://github.com/kluczak12/TrafficSense.git