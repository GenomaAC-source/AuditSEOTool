# AuditSEO Tool

## Obiettivo
Creare un tool CLI in Python che analizza un sito web e genera un report di audit SEO completo in formato Markdown e DOCX, seguendo la struttura professionale degli audit di riferimento presenti nella cartella.

## Principi Fondamentali

### Scalabilità
Il tool deve essere progettato per analizzare siti con **migliaia di pagine**. Questo significa:
- Crawling asincrono e parallelo per velocità
- Gestione efficiente della memoria (non caricare tutto in RAM)
- Salvataggio progressivo dei dati durante l'analisi
- Possibilità di riprendere analisi interrotte
- Database locale (SQLite) per memorizzare i dati del crawl

### Tono da Consulente Esperto
Il report NON deve essere un elenco meccanico di errori. Deve essere scritto come se un consulente SEO senior avesse:
- Navigato personalmente tutto il sito
- Fatto riflessioni strategiche sui problemi trovati
- Contestualizzato i problemi rispetto al tipo di sito (e-commerce, corporate, blog, etc.)
- Dato consigli pratici e prioritizzati

Esempi di tono corretto:
- "Navigando il sito, si nota che le pagine prodotto presentano..."
- "Analizzando la struttura delle categorie, emerge che..."
- "Un aspetto critico riguarda..."
- "Si consiglia di intervenire prioritariamente su..."

Esempi di tono da EVITARE:
- "Trovati 47 errori nel tag title"
- "La pagina X ha un errore"
- Elenchi puntati senza contesto

### Documentazione Visiva
Il report deve includere **screenshot** per rendere chiare le problematiche:
- Screenshot delle pagine del sito (usando Playwright/Selenium)
- Screenshot del codice sorgente con evidenziazione degli errori
- Screenshot dei risultati di Google (SERP) se rilevanti
- Tabelle e grafici per visualizzare i dati

## Stack Tecnologico
- Python 3.11+
- Librerie consigliate:
  - `httpx` con `asyncio` per crawling asincrono
  - `beautifulsoup4` / `lxml` per il parsing HTML
  - `python-docx` per generare report DOCX
  - `playwright` per screenshot delle pagine
  - `Pillow` per elaborazione immagini
  - `rich` per output CLI
  - `sqlite3` per database locale
  - `scikit-learn` o `difflib` per analisi similarità contenuti
  - Altre librerie a discrezione per funzionalità specifiche

## Funzionalità Richieste

### 1. Crawler del sito
- **Crawling asincrono** con httpx/aiohttp per massima velocità
- Rispetto del robots.txt e rate limiting configurabile
- **Nessun limite fisso** di pagine - deve poter analizzare siti con migliaia di pagine
- Estrazione di tutti i link interni
- **Salvataggio progressivo su SQLite** durante il crawl
- Possibilità di **riprendere crawl interrotti**
- Gestione intelligente della memoria (streaming, non caricare tutto in RAM)
- Deduplicazione URL in tempo reale
- Gestione di redirect, errori, timeout
- Estrazione e salvataggio del contenuto testuale per analisi duplicati

### 2. Analisi Architettura Sito Web

#### 2.1 Alberatura
**NOTA IMPORTANTE:** L'alberatura NON è il menu di navigazione. Sono concetti distinti:
- **Alberatura** = struttura logica/gerarchica delle URL e delle pagine (come sono organizzate)
- **Menu di navigazione** = scelta UX su come permettere agli utenti di navigare (può differire dall'alberatura)

**Cosa analizzare:**
- Mappare la struttura gerarchica basandosi sulle URL (es. /categoria/sottocategoria/pagina)
- Calcolare la profondità di ogni pagina dalla homepage (click depth)
- Clusterizzare le pagine per sezione/categoria logica
- Identificare pagine troppo profonde (>3-4 livelli dalla home)
- Verificare coerenza tra struttura URL e gerarchia logica
- Identificare pagine "orfane" (non raggiungibili dalla navigazione)

**Best practice:**
- Struttura piatta: le pagine importanti dovrebbero essere a max 3 click dalla home
- URL che riflettono la gerarchia: /categoria/sottocategoria/pagina
- Distribuzione equilibrata: evitare categorie con troppe o troppo poche pagine

**Output atteso:**
- Mappa visuale della struttura (albero)
- Statistiche per livello di profondità
- Lista pagine troppo profonde
- Suggerimenti di riorganizzazione se necessario

#### 2.2 Canonicalizzazione e Contenuti Duplicati
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/canonicalization

**Cosa analizzare - Canonical Tag:**
- Verificare presenza del tag canonical in ogni pagina
- Verificare che il canonical sia assoluto (non relativo)
- Controllare coerenza: il canonical deve puntare alla versione "principale" della pagina
- Identificare canonical autoreferenziali (pagina che punta a se stessa - OK se intenzionale)
- Rilevare canonical che puntano a pagine 404, redirect, o pagine noindex
- Verificare che pagine con parametri URL abbiano canonical verso versione pulita

**Errori comuni da rilevare:**
- Canonical mancante
- Canonical che punta a URL diversa senza motivo (errore di configurazione)
- Canonical chain (A->B->C invece di A->C)
- Canonical verso pagina con contenuto diverso
- Canonical non HTTPS su sito HTTPS

**Analisi intelligente dei duplicati basata sul contenuto:**
- Estrarre il contenuto testuale principale (escludendo header, footer, sidebar comuni)
- Calcolare hash/fingerprint del contenuto (SimHash o MinHash per scalabilità)
- Usare cosine similarity o Jaccard per confronto accurato
- Soglie di similarità:
  - >95% = duplicato esatto (stesso contenuto, URL diverse)
  - 85-95% = quasi duplicato (varianti minime: colore, taglia, etc.)
  - 70-85% = contenuto simile (potrebbe essere ok, da valutare)

**Casi specifici da rilevare:**
- Pagine prodotto con varianti (colore, taglia) che hanno stesso testo
- Pagine di categoria con filtri che generano contenuto duplicato
- Versioni www/non-www, http/https, trailing slash
- Pagine con parametri di tracking (?utm_source=...)
- Paginazione che duplica contenuti

**Output atteso:**
- Gruppi di pagine duplicate con % di similarità
- Per ogni gruppo, suggerimento su quale dovrebbe essere il canonical
- Evidenziare le differenze tra pagine quasi-duplicate
- Stima dell'impatto SEO (quante pagine "sprecate" per contenuto duplicato)

#### 2.3 Hreflang
**Riferimento:** Linee guida ufficiali Google: https://developers.google.com/search/docs/specialty/international/localized-versions

**Cosa analizzare:**
- Verificare presenza dei tag hreflang in tutte le pagine multilingua
- Controllare che ogni pagina abbia link hreflang verso TUTTE le versioni linguistiche (inclusa se stessa)
- Verificare reciprocità: se pagina IT linka a EN, pagina EN deve linkare a IT
- Controllare formato codice lingua (ISO 639-1) e paese (ISO 3166-1 Alpha 2)
- Verificare implementazione: può essere in <head>, HTTP header, o sitemap

**Errori comuni da rilevare:**
- Hreflang non reciproci (pagina A linka B, ma B non linka A)
- Codici lingua errati (es. "en-UK" invece di "en-GB")
- Hreflang che puntano a pagine 404 o redirect
- Hreflang mancanti per alcune lingue
- Mix di implementazioni (alcuni in head, altri in sitemap)

**x-default:**
- Verificare se presente e se usato correttamente
- x-default dovrebbe puntare a una pagina di selezione lingua O alla versione "default"
- NON deve puntare alla stessa pagina che si sta visitando (errore comune)
- È opzionale ma consigliato per gestire utenti con lingua non supportata

**Formato corretto:**
```html
<link rel="alternate" hreflang="it" href="https://example.com/it/pagina" />
<link rel="alternate" hreflang="en" href="https://example.com/en/page" />
<link rel="alternate" hreflang="x-default" href="https://example.com/language-selector" />
```

**Output atteso:**
- Mappa delle corrispondenze tra versioni linguistiche
- Lista errori di reciprocità
- Lista codici lingua/paese non validi
- Suggerimenti specifici per ogni errore trovato

#### 2.4 Struttura URL
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/url-structure

**Cosa analizzare:**
- Verificare che le URL siano "parlanti" e descrittive
- Controllare che contengano keyword rilevanti per la pagina
- Verificare lunghezza (Google mostra ~512px, circa 50-60 caratteri visibili)
- Identificare URL con parametri dinamici (?id=123&cat=5)
- Controllare encoding caratteri speciali

**Problemi da rilevare:**
- Underscore (_) invece di dash (-): i motori trattano underscore come parte della parola
- Doppi slash (//): possono creare duplicati
- Maiuscole: le URL sono case-sensitive, meglio tutto minuscolo
- Caratteri speciali non encodati
- URL troppo lunghe o troppo generiche (/page1, /article123)
- Parametri di sessione nelle URL
- Struttura incoerente (mix di /categoria/prodotto e /prodotto/categoria)

**Best practice:**
- Usare solo minuscole
- Separare parole con dash (-)
- Evitare parametri quando possibile
- Struttura logica che riflette gerarchia: /categoria/sottocategoria/pagina
- Keyword principali nella URL
- Evitare date nelle URL di contenuti evergreen

**Output atteso:**
- Lista URL problematiche raggruppate per tipo di problema
- Suggerimenti di URL ottimizzate
- Statistiche sulla qualità complessiva delle URL

#### 2.5 Menu di Navigazione
**NOTA:** Il menu è una SCELTA UX, non deve necessariamente riflettere l'alberatura. L'analisi deve valutare se il menu supporta efficacemente la navigazione e il crawling.

**Cosa analizzare - Menu Principale:**
- Estrarre struttura del menu (voci, sottovoci, livelli)
- Verificare che le pagine più importanti siano raggiungibili dal menu
- Controllare che i link siano crawlabili (no JavaScript-only navigation)
- Verificare anchor text descrittivi (non "clicca qui")
- Controllare ordine delle voci (le più importanti a sinistra/in alto)

**Cosa analizzare - Menu Secondari e Footer:**
- Verificare presenza di navigazione secondaria per sezioni profonde
- Analizzare il footer come "mappa del sito" alternativa
- Controllare breadcrumb per la navigazione gerarchica
- Verificare link a pagine importanti (contatti, privacy, etc.)

**Problemi da rilevare:**
- Menu solo JavaScript (non crawlabile)
- Troppe voci (overwhelm utente e diluisce link equity)
- Pagine importanti non linkate dal menu
- Link rotti nel menu
- Anchor text generici o duplicati
- Mega-menu con troppi livelli

**Confronto con Alberatura:**
- Identificare pagine nell'alberatura ma non nel menu (scelta ok se intenzionale)
- Identificare pagine nel menu ma "orfane" nell'alberatura
- Valutare se le scelte di menu supportano gli obiettivi SEO del sito

**Output atteso:**
- Mappa del menu con tutti i livelli
- Lista pagine importanti (per traffico/conversione) non nel menu
- Suggerimenti per migliorare la navigazione

#### 2.6 Title Tag
**Riferimento:** https://developers.google.com/search/docs/appearance/title-link

**Cosa analizzare:**
- Presenza in tutte le pagine
- Lunghezza: ideale 50-60 caratteri (Google mostra ~600px, circa 50-60 char)
- Unicità: ogni pagina deve avere title unico
- Rilevanza: il title deve descrivere accuratamente il contenuto
- Keyword: la keyword principale dovrebbe essere presente, preferibilmente all'inizio
- Brand: pattern comune "Keyword | Brand" o "Brand | Keyword"

**Problemi da rilevare:**
- Title mancante
- Title troppo lungo (verrà troncato con "...")
- Title troppo corto (< 30 char, poco descrittivo)
- Title duplicati tra pagine diverse
- Title in ALL CAPS (percepito come spam)
- Title generico ("Home", "Pagina", "Untitled")
- Title che non corrisponde al contenuto della pagina
- Title con keyword stuffing
- Title con caratteri speciali problematici

**Valutazione qualitativa:**
- Il title invoglia al click? (CTR potenziale)
- Contiene la keyword principale?
- È unico e descrittivo?
- Segue un pattern coerente con il resto del sito?

**Output atteso:**
- Lista title problematici raggruppati per tipo di problema
- Suggerimenti di title ottimizzati per le pagine principali
- Statistiche: % pagine con title ok, duplicati, mancanti, troppo lunghi

#### 2.7 Meta Description
**Riferimento:** https://developers.google.com/search/docs/appearance/snippet

**NOTA:** Google può ignorare la meta description e generarne una propria. Tuttavia, una buona description aumenta le probabilità che venga usata.

**Cosa analizzare:**
- Presenza in tutte le pagine
- Lunghezza: ideale 140-160 caratteri (Google mostra ~920px)
- Unicità: ogni pagina dovrebbe avere description unica
- Call to action: presenza di inviti all'azione (Scopri, Acquista, Leggi...)
- Rilevanza: deve descrivere accuratamente il contenuto

**Problemi da rilevare:**
- Description mancante
- Description troppo lunga (verrà troncata)
- Description troppo corta (< 70 char, poco informativa)
- Description duplicate tra pagine
- Description che non corrisponde al contenuto
- Description senza call to action
- Description con keyword stuffing

**Valutazione qualitativa:**
- La description funziona come "annuncio" per la pagina?
- Contiene un beneficio per l'utente?
- Ha una call to action?
- È differenziata dalla concorrenza?

**Output atteso:**
- Lista description problematiche
- Esempi di description ottimizzate per pagine chiave
- Statistiche sulla qualità complessiva

#### 2.8 Meta Keywords
**NOTA:** Google ha dichiarato nel 2009 di NON usare meta keywords per il ranking.
https://developers.google.com/search/blog/2009/09/google-does-not-use-keywords-meta-tag

**Cosa analizzare:**
- Verificare presenza (solo per completezza)
- NON è un problema se mancante
- Può essere utile per altri motori (Bing in passato, motori interni)

**Output:** Semplice nota sulla presenza/assenza, nessuna raccomandazione prioritaria.

#### 2.9 Tempi di Caricamento e Core Web Vitals
**Riferimento:** https://developers.google.com/search/docs/appearance/core-web-vitals

**Core Web Vitals (metriche Google):**
- **LCP (Largest Contentful Paint):** tempo per il rendering dell'elemento più grande
  - Buono: < 2.5s | Da migliorare: 2.5-4s | Scarso: > 4s
- **INP (Interaction to Next Paint):** reattività alle interazioni
  - Buono: < 200ms | Da migliorare: 200-500ms | Scarso: > 500ms
- **CLS (Cumulative Layout Shift):** stabilità visiva
  - Buono: < 0.1 | Da migliorare: 0.1-0.25 | Scarso: > 0.25

**Cosa analizzare:**
- Tempo di caricamento base (TTFB, DOMContentLoaded, Load)
- Core Web Vitals tramite PageSpeed Insights API o Lighthouse
- Dimensione totale della pagina (HTML + CSS + JS + immagini)
- Numero di richieste HTTP
- Risorse che bloccano il rendering

**Problemi da rilevare:**
- Pagine con LCP > 2.5 secondi
- Immagini non ottimizzate (formato, dimensioni, lazy loading)
- JavaScript che blocca il rendering
- CSS non minificato o non critico inline
- Troppe richieste HTTP
- Assenza di caching
- Server lento (TTFB alto)

**Output atteso:**
- Punteggi Core Web Vitals per homepage e pagine template
- Lista pagine più lente
- Suggerimenti specifici per migliorare (con priorità)
- Screenshot del report PageSpeed se disponibile

#### 2.10 Sitemap.xml
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview

**Cosa analizzare:**
- Esistenza e accessibilità (status 200)
- Formato corretto (XML valido, namespace corretto)
- Dichiarazione nel robots.txt
- Sitemap index se presente (per siti grandi)

**Contenuto della sitemap:**
- Conteggio URL nella sitemap
- Confronto con pagine crawlate:
  - Pagine nel sito ma NON in sitemap (mancanti)
  - Pagine in sitemap ma NON nel sito o 404 (obsolete)
  - Pagine in sitemap ma con redirect
  - Pagine in sitemap ma noindex
- Verifica tag opzionali: lastmod, changefreq, priority

**Problemi da rilevare:**
- Sitemap mancante
- Sitemap con errori XML
- URL in sitemap che restituiscono 404/301/302
- URL in sitemap con canonical diverso
- URL in sitemap con noindex
- Sitemap troppo grande (>50MB o >50.000 URL per file)
- lastmod non aggiornato o fittizio

**Output atteso:**
- Statistiche sitemap vs sito reale
- Lista URL problematiche nella sitemap
- Suggerimenti per ottimizzazione

#### 2.11 Robots.txt
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/robots/intro

**Cosa analizzare:**
- Esistenza e accessibilità
- Sintassi corretta
- Direttive per user-agent (Googlebot, *, etc.)
- Presenza link alla sitemap

**Direttive da verificare:**
- Disallow: cosa viene bloccato?
- Allow: eccezioni ai disallow
- Crawl-delay: (non supportato da Google, ma da altri)
- Sitemap: link alla sitemap

**Problemi da rilevare:**
- Robots.txt mancante (non bloccante ma consigliato)
- Blocco accidentale di risorse importanti (CSS, JS necessari per rendering)
- Blocco di pagine che dovrebbero essere indicizzate
- Sintassi errata
- Disallow: / (blocca tutto!)
- Blocco di risorse necessarie per il rendering JavaScript

**Output atteso:**
- Contenuto del robots.txt con analisi
- Lista risorse bloccate con valutazione se intenzionale
- Suggerimenti se necessario

#### 2.12 HTTP/HTTPS
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/https

**HTTPS è un fattore di ranking confermato da Google.**

**Cosa analizzare:**
- Il sito usa HTTPS?
- Certificato SSL valido (non scaduto, dominio corretto)
- Redirect da HTTP a HTTPS (deve essere 301, non 302)
- Mixed content: risorse HTTP su pagine HTTPS
- HSTS header presente?

**Problemi da rilevare:**
- Sito ancora su HTTP
- Certificato scaduto o non valido
- Certificato per dominio sbagliato
- Redirect HTTP->HTTPS mancante o 302 invece di 301
- Mixed content (immagini, script, CSS su HTTP)
- Link interni che puntano a versione HTTP

**Output atteso:**
- Stato certificato SSL (validità, scadenza, emittente)
- Test redirect HTTP->HTTPS
- Lista risorse mixed content
- Raccomandazioni

#### 2.13 Errori 404 e Redirect 301
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/http-network-errors

**Cosa analizzare:**
- Tutti i link interni del sito e il loro status code
- Pagine che restituiscono 404
- Redirect 301 (permanente) vs 302 (temporaneo)
- Catene di redirect (A->B->C->D)
- Redirect loop (A->B->A)

**Status code da tracciare:**
- 200: OK
- 301: Redirect permanente (corretto per spostamenti definitivi)
- 302/307: Redirect temporaneo (da evitare per spostamenti definitivi)
- 404: Pagina non trovata
- 410: Pagina rimossa definitivamente
- 500: Errore server
- 503: Servizio non disponibile

**Problemi da rilevare:**
- Link interni che puntano a 404
- Link interni che puntano a redirect (spreco di crawl budget)
- Catene di redirect (max 1 hop consigliato)
- Redirect loop
- 302 usato invece di 301 per spostamenti permanenti
- Pagine importanti che restituiscono 404
- Soft 404 (pagina che dice "non trovato" ma restituisce 200)

**Output atteso:**
- Lista completa errori 404 con sorgente del link
- Mappa dei redirect con numero di hop
- Suggerimenti: quali 404 correggere, quali redirect accorciare
- Priorità basata su importanza della pagina/numero di link in entrata

#### 2.14 Paginazione
**Riferimento:** https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading

**NOTA IMPORTANTE:** Google ha dichiarato nel 2019 che rel="next/prev" NON è più usato come segnale di ranking. Tuttavia, può ancora essere utile per altri motori e per chiarezza semantica.

**Cosa analizzare:**
- Identificare pagine di paginazione (es. /categoria?page=2, /categoria/page/2/)
- Verificare implementazione rel="next" e rel="prev" (se presente)
- Verificare canonical sulle pagine paginate
- Verificare se esiste pagina "view all"

**Strategie di paginazione accettabili:**
1. **Paginazione classica** con rel="next/prev" (ancora valida)
2. **View all** page come canonical (se non troppo pesante)
3. **Infinite scroll** con URL cambiate per ogni "pagina" (per crawlability)
4. **Load more** con gestione corretta delle URL

**Problemi da rilevare:**
- Canonical su pagina 2,3,4... che punta a pagina 1 (ERRORE comune!)
- rel="next/prev" che puntano a pagine 404
- Contenuto duplicato tra pagine paginate
- Infinite scroll senza URL discrete (non crawlabile)
- Parametri di paginazione non gestiti (creano duplicati)

**Output atteso:**
- Lista sezioni paginate del sito
- Verifica implementazione per ogni sezione
- Raccomandazioni specifiche

### 3. Analisi Contenuti

#### 3.1 Headings (H1-H6)
**Riferimento:** https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-headings

**Cosa analizzare:**
- Presenza H1 in ogni pagina (dovrebbe esserci sempre)
- Unicità H1 nella pagina (preferibilmente uno solo)
- Gerarchia corretta: H1 > H2 > H3 (non saltare livelli)
- Contenuto degli heading: descrittivi e con keyword rilevanti
- Lunghezza: non troppo lunghi, non troppo generici

**Problemi da rilevare:**
- H1 mancante
- H1 multipli nella stessa pagina
- H1 duplicato tra pagine diverse
- H1 identico al title (ok, ma opportunità persa)
- Gerarchia rotta (H1 seguito da H3, saltando H2)
- Heading usati per stile invece che per struttura
- Heading vuoti o con solo immagini
- Heading troppo lunghi (>70 caratteri)
- Heading generici ("Benvenuto", "Informazioni")

**Output atteso:**
- Statistiche: pagine senza H1, con H1 multipli, con H1 duplicati
- Lista problemi con esempi specifici
- Suggerimenti per heading ottimizzati su pagine chiave

#### 3.2 Paragrafi e Contenuto Testuale
**Cosa analizzare:**
- Presenza di contenuto testuale sostanziale
- Uso corretto del tag <p>
- Densità di contenuto (rapporto testo/HTML)
- Leggibilità del testo
- Uso appropriato di formattazione (bold, liste, etc.)

**Problemi da rilevare:**
- Pagine con poco o nessun testo (thin content)
- Testo nascosto (display:none, font-size:0)
- Keyword stuffing (ripetizione eccessiva di keyword)
- Contenuto duplicato da altre fonti (scraping)
- Mancanza di formattazione (muro di testo)

**Metriche:**
- Conteggio parole per pagina
- Rapporto testo/HTML
- Pagine sotto soglia minima (es. <300 parole per pagine informative)

**Output atteso:**
- Statistiche contenuto per tipo di pagina
- Lista pagine thin content
- Raccomandazioni per migliorare la qualità dei contenuti

#### 3.3 Immagini
**Riferimento:** https://developers.google.com/search/docs/appearance/google-images

**Cosa analizzare:**
- Presenza attributo alt su tutte le immagini
- Qualità degli alt text (descrittivi, non keyword stuffing)
- Nomi file immagini (parlanti vs IMG_12345.jpg)
- Formato immagini (WebP, AVIF vs PNG/JPG)
- Dimensioni e peso (ottimizzazione)
- Lazy loading implementato

**Problemi da rilevare:**
- Immagini senza alt
- Alt text vuoto (alt="")
- Alt text generico ("immagine", "foto", "image1")
- Alt text troppo lungo (>125 caratteri)
- Alt text con keyword stuffing
- Nomi file non descrittivi
- Immagini troppo pesanti (>500KB per web)
- Immagini non responsive
- Immagini importanti caricate via CSS (non indicizzabili)

**Output atteso:**
- Statistiche: % immagini con alt, senza alt, con alt generico
- Lista immagini problematiche
- Peso totale immagini per pagina
- Suggerimenti per ottimizzazione

#### 3.4 Linking Interno
**Riferimento:** https://developers.google.com/search/docs/crawling-indexing/links-crawlable

**Il linking interno è FONDAMENTALE per:**
- Distribuire PageRank/autorità tra le pagine
- Aiutare il crawling di pagine profonde
- Indicare ai motori la gerarchia e le relazioni tra contenuti
- Migliorare l'esperienza utente

**Cosa analizzare:**
- Mappa completa dei link interni
- PageRank interno (quali pagine ricevono più link)
- Pagine orfane (zero link in entrata)
- Anchor text dei link interni
- Numero di link in uscita per pagina

**Problemi da rilevare:**
- Pagine orfane (nessun link interno verso di esse)
- Pagine con troppi link in uscita (>100, diluizione PageRank)
- Pagine importanti con pochi link in entrata
- Anchor text generici ("clicca qui", "leggi di più")
- Anchor text duplicati che puntano a pagine diverse
- Link JavaScript-only (non crawlabili)
- Link nofollow interni (spreco di PageRank)
- Broken internal links

**Metriche:**
- Link interni ricevuti per pagina
- Distribuzione del PageRank interno
- Profondità di click dalla homepage

**Output atteso:**
- Top pagine per link ricevuti
- Lista pagine orfane o sotto-linkate
- Suggerimenti per migliorare il linking verso pagine strategiche
- Analisi anchor text

### 4. Microdati / Schema.org
**Riferimento:**
- https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- https://schema.org/

**I dati strutturati permettono rich results su Google: stelle recensioni, prezzi, FAQ, breadcrumb, etc.**

**Formati supportati:**
- **JSON-LD** (raccomandato da Google)
- Microdata (HTML attributes)
- RDFa

**Cosa analizzare:**
- Presenza di dati strutturati per tipo di pagina
- Formato utilizzato (preferibile JSON-LD)
- Validità secondo Schema.org
- Proprietà obbligatorie vs opzionali

**Tipi di Schema comuni da verificare:**

| Tipo pagina | Schema consigliato |
|-------------|-------------------|
| Homepage | Organization, WebSite, SearchAction |
| Prodotto | Product (con offers, review, aggregateRating) |
| Articolo/Blog | Article, BlogPosting, NewsArticle |
| Categoria | CollectionPage, ItemList |
| Contatti | ContactPage, LocalBusiness |
| FAQ | FAQPage |
| How-to | HowTo |
| Evento | Event |
| Ricetta | Recipe |
| Video | VideoObject |

**Problemi da rilevare:**
- Dati strutturati mancanti su pagine chiave
- Errori di sintassi JSON-LD
- Proprietà obbligatorie mancanti
- Valori errati (es. prezzo senza valuta)
- Doppia implementazione (JSON-LD + Microdata che confliggono)
- Schema non pertinente al contenuto
- URL immagini non accessibili
- Dati strutturati che non corrispondono al contenuto visibile (spam)

**Validazione:**
- Usare Google Rich Results Test: https://search.google.com/test/rich-results
- Verificare proprietà obbligatorie per ogni tipo

**Output atteso:**
- Lista pagine con dati strutturati e tipo
- Lista errori di validazione
- Suggerimenti per implementare Schema mancanti
- Screenshot del test Rich Results per pagine chiave

## Output

### Report Markdown
Generare un file `.md` con questa struttura:

```
# Audit SEO - [Nome Sito]

## 1. INTRODUZIONE
### 1.1 Gli obiettivi
### 1.2 La struttura

## 2. ARCHITETTURA SITO WEB
### 2.1 Alberatura
**Premessa:** [spiegazione tecnica]
**Situazione attuale:** [analisi del sito]
**Come migliorare:** [suggerimenti]

[... stesso formato per ogni sezione ...]

## 3. CONTENUTI DEL SITO WEB
[... sezioni contenuti ...]

## 4. MICRODATI
[... analisi dati strutturati ...]

## 5. PRIORITÀ E IMPORTANZA
| Elemento | Criticità | Status | Priorità |
|----------|-----------|--------|----------|
| ... | 1-3 | OK/KO | 1-3 |
```

### Report DOCX
- Generare documento Word con stessa struttura
- Includere formattazione professionale
- Aggiungere indice navigabile

### Screenshot e Documentazione Visiva
Il tool deve catturare automaticamente screenshot per documentare i problemi:

#### Screenshot delle pagine
- Homepage (desktop e mobile)
- Pagine con problemi significativi
- Esempi di pagine duplicate
- Menu di navigazione
- Footer

#### Screenshot del codice
- Evidenziare errori nei meta tag (title, description)
- Mostrare implementazione errata di canonical/hreflang
- Evidenziare problemi nei dati strutturati
- Mostrare heading mal strutturati

#### Come includere gli screenshot
```
screenshots/
├── homepage_desktop.png
├── homepage_mobile.png
├── code_title_error_example.png
├── code_canonical_issue.png
├── duplicate_page_1.png
├── duplicate_page_2.png
└── ...
```

Nel report, gli screenshot devono essere inseriti nel contesto:
- "Come si può vedere dall'immagine seguente, il title della homepage supera i 60 caratteri:"
- [screenshot]
- "Si nota inoltre che..."

### File JSON
- Salvare tutti i dati grezzi dell'analisi in un file JSON per elaborazioni successive

## Interfaccia CLI

```bash
# Analisi completa (crawla tutto il sito)
python audit.py https://www.example.com

# Con limite pagine (per test rapidi)
python audit.py https://www.example.com --max-pages 100

# Riprendi crawl interrotto
python audit.py https://www.example.com --resume

# Solo report (senza nuovo crawl, usa dati esistenti)
python audit.py https://www.example.com --report-only

# Opzioni disponibili:
# --max-pages N         Limite pagine (default: illimitato)
# --output FILE         Nome file output (default: audit_[domain]_[timestamp])
# --format md|docx|both Formato output (default: both)
# --screenshots         Cattura screenshot (richiede playwright)
# --no-screenshots      Disabilita screenshot
# --resume              Riprendi crawl interrotto
# --report-only         Genera report da dati esistenti
# --concurrency N       Richieste parallele (default: 10)
# --delay MS            Delay tra richieste in ms (default: 100)
# --verbose             Output dettagliato
# --similarity N        Soglia similarità duplicati % (default: 85)
```

## Struttura Progetto

```
AuditSEOTool/
├── audit.py              # Entry point CLI
├── requirements.txt      # Dipendenze
├── README.md            # Documentazione
├── src/
│   ├── __init__.py
│   ├── crawler.py       # Crawler asincrono
│   ├── database.py      # Gestione SQLite
│   ├── screenshot.py    # Cattura screenshot con Playwright
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── architecture.py   # Analisi architettura
│   │   ├── content.py        # Analisi contenuti
│   │   ├── duplicates.py     # Rilevamento duplicati (similarità)
│   │   ├── technical.py      # Analisi tecnica
│   │   └── structured_data.py # Analisi microdati
│   ├── reporters/
│   │   ├── __init__.py
│   │   ├── markdown.py       # Generatore MD
│   │   ├── docx.py           # Generatore DOCX
│   │   └── narrative.py      # Generazione testo "da consulente"
│   └── utils/
│       ├── __init__.py
│       ├── similarity.py     # Algoritmi similarità (SimHash, etc.)
│       └── helpers.py        # Funzioni utility
├── data/                     # Directory per dati crawl
│   └── [domain]/
│       ├── crawl.db          # Database SQLite
│       └── screenshots/      # Screenshot catturati
└── tests/
    └── test_*.py            # Test unitari
```

## Esempi di Scrittura da Consulente

### Esempio 1: Contenuti Duplicati
**SBAGLIATO (troppo tecnico/freddo):**
> Rilevate 47 pagine con similarità > 90%. Lista URL: ...

**CORRETTO (da consulente):**
> Analizzando il catalogo prodotti, è emerso un problema significativo di contenuti duplicati. In particolare, le pagine relative alle varianti colore dei prodotti (ad esempio /borsa-pelle-nera, /borsa-pelle-marrone, /borsa-pelle-rossa) presentano testi pressoché identici, differendo unicamente per il nome del colore nel titolo.
>
> Questa situazione può creare confusione nei motori di ricerca, che potrebbero non sapere quale versione indicizzare, penalizzando potenzialmente il posizionamento di tutte le varianti.
>
> Si consiglia di implementare il tag canonical che punti alla pagina "madre" del prodotto, oppure di differenziare i contenuti aggiungendo descrizioni specifiche per ogni variante.

### Esempio 2: Meta Title
**SBAGLIATO:**
> 23 pagine hanno title > 60 caratteri. 12 pagine hanno title duplicati.

**CORRETTO:**
> Nell'analisi dei meta title sono stati riscontrati alcuni aspetti da migliorare. Diverse pagine di categoria presentano title che superano i 60 caratteri consigliati, rischiando di essere troncati nei risultati di ricerca.
>
> Inoltre, si è notato che alcune pagine prodotto condividono lo stesso title, probabilmente a causa di una configurazione automatica che non tiene conto delle specificità di ogni articolo.
>
> Come si può vedere dall'immagine seguente, il title della homepage risulta: [screenshot]

### Esempio 3: Errori 404
**SBAGLIATO:**
> Trovati 8 link rotti.

**CORRETTO:**
> Durante la navigazione del sito sono stati individuati alcuni link che portano a pagine non più esistenti (errore 404). In particolare, nella sezione news sono presenti collegamenti a categorie rimosse (/category/non-categorizzato/) che restituiscono un errore.
>
> Questa situazione può impattare negativamente sia sull'esperienza utente, che si trova di fronte a pagine di errore, sia sulla valutazione del sito da parte dei motori di ricerca.

## Criteri di Completamento

Il progetto è completo quando:
1. Il crawler funziona e rispetta robots.txt
2. Tutte le analisi elencate sono implementate
3. Il report MD viene generato correttamente
4. Il report DOCX viene generato correttamente
5. La CLI funziona con tutte le opzioni
6. Il tool può analizzare con successo un sito reale
7. I test passano

## Come Segnalare Completamento

Quando tutte le funzionalità sono implementate e testate, output:

```
<promise>AUDIT TOOL COMPLETE</promise>
```

## Note Importanti
- Seguire la struttura e il tono degli audit di riferimento nella cartella
- Le sezioni "Premessa" contengono spiegazioni tecniche standard
- Le sezioni "Situazione attuale" contengono l'analisi specifica del sito
- Le sezioni "Come migliorare" contengono suggerimenti pratici
- La tabella finale assegna priorità 1-3 (1=alta, 3=bassa)
