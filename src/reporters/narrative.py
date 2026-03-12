"""Narrative text generator for consultant-style reports."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class NarrativeSection:
    """A section of narrative text."""
    title: str
    premise: str  # Premessa
    current_situation: str  # Situazione attuale
    improvements: str  # Come migliorare
    severity: int = 2  # 1=high, 2=medium, 3=low


class NarrativeGenerator:
    """Generator for consultant-style narrative text."""

    # Standard premises for each section (technical explanations)
    PREMISES = {
        'alberatura': """Per alberatura di un sito s'intende la struttura gerarchica delle varie sezioni del sito partendo dall'homepage e sviluppandosi poi nelle successive sezioni e sottosezioni. L'importanza di una pagina aumenta quindi con il diminuire del livello di profondità: più è vicina alla home-page più è importante.""",

        'canonical': """Per garantire risultati di qualità i sistemi d'indicizzazione dei motori di ricerca pongono una particolare attenzione all'utilizzo di contenuto duplicato all'interno di un sito o tra siti. Per identificare la presenza o meno di contenuto duplicato il motore di ricerca verifica che due URL (indirizzi diversi) non portino a una pagina con lo stesso contenuto. Se questo succede, il sito è penalizzato abbassando il livello di posizionamento nella pagina dei risultati o anche eliminando del tutto la pagina dall'indice.""",

        'hreflang': """Un rilevamento di contenuti duplicati può avvenire anche nel caso ci siano versioni multilingua del sito. Per permettere ai motori di ricerca di comprendere al meglio la lingua di riferimento di ogni pagina è necessario utilizzare le annotazioni per lingua definite tramite il markup hreflang.""",

        'url': """La struttura di un URL è fondamentale per i motori di ricerca in quanto: riflette la struttura del sito nella sua suddivisione in categorie e sotto categorie; se statica e priva di parametri permette di rendere immediatamente chiaro l'argomento della pagina; si consiglia l'utilizzo delle parole chiave all'interno del URL; si consiglia di separare le parole chiave con un dash "-" e non con un underscore "_". È fondamentale, quindi, che le URL siano "parlanti" e permettano una facile comprensione sia al motore di ricerca sia agli utenti stessi che le leggono.""",

        'menu': """Il menu di navigazione principale permette la consultazione delle sezioni più importanti ed è generalmente impostato basandosi sulle decisioni strutturali dell'alberatura del sito. Nel caso dei menu orizzontali la voce di menu a sinistra è la più importante mentre in quelli a disposizione verticale la più importante è quella più in alto.""",

        'title': """Il title è il titolo della pagina: questo campo è utile perché permette all'utente di capire tramite l'interfaccia del browser cosa sta guardando ancora prima di vedere la pagina stessa. La sua funzione è però fondamentale anche nei motori di ricerca poiché il page title influenza sul posizionamento ed è la prima parte dell'abstract delle pagine che è visualizzata.""",

        'description': """La meta-description non è essenziale per il posizionamento ma, insieme al page title, contribuisce alla creazione da parte dei motori di ricerca dell'"annuncio" visualizzato dagli utenti. In altre parole, la meta-description può essere paragonata agli annunci utilizzati nella SEM (Adwords) e per questo motivo è essenziale che sia chiaro, diretto e rispecchi fedelmente il contenuto della pagina. Si consiglia sempre l'utilizzo, all'interno della description, di una call to action come: scopri, trova, acquista...""",

        'keywords': """Questo meta tag è ormai pressoché caduto in disuso in quanto i motori di ricerca non lo considerano se non per eventuali errori di battitura di parole particolari. In particolare Google ne ha deprecato l'utilizzo nel 2009. Detto ciò è comunque un parametro che è consigliabile avere implementato correttamente.""",

        'performance': """Il tempo di caricamento di ogni pagina del sito è un elemento importante sia per il posizionamento sui motori di ricerca sia per gli utenti che nel caso riscontrassero dei tempi di caricamento elevati abbandonerebbero il sito. Google utilizza i Core Web Vitals come fattore di ranking.""",

        'sitemap': """La mappa del sito o anche sitemap permette ai motori di ricerca di capire meglio la struttura del sito e dare rilevanza alle pagine più importanti, in particolar modo a quelle pagine che per motivi di alberatura sono situate più in profondità. Un aggiornamento costante della sitemap in contemporanea all'inserimento di nuove sezioni ne permette una più veloce indicizzazione e conseguente posizionamento.""",

        'robots': """Il file robots.txt contiene delle istruzioni che possono impedire a tutti o alcuni motori di ricerca il prelievo di alcune o tutte le pagine del sito. Oltre a queste indicazioni, il file robots.txt è un altro elemento che indica la qualità di un sito e può contenere altre informazioni come la posizione della sitemap. Google in generale consiglia di non bloccare alcuna risorsa se non in casi strettamente necessari.""",

        'https': """Http è il protocollo di trasferimento delle pagine su internet. Https è anch'esso un protocollo di trasferimento, ma in questo caso è interposto un livello di crittografia che permette una trasmissione dei dati più sicura. Google ha confermato che HTTPS è un fattore di ranking.""",

        'errors': """Il messaggio di errore 404 si verifica quando si cerca di raggiungere una pagina web non trovata sul server. Può accadere quando la pagina che si cerca è stata rimossa o trasferita oppure quando la URL digitata non è corretta. I redirect 301 indicano spostamenti permanenti di pagine.""",

        'pagination': """Gli elementi link rel="next" e rel="prev" servono per indicare la relazione tra le singole URL di un sito web. Nonostante Google nel 2019 abbia dichiarato questo attributo non più utile come segnale di valutazione delle pagine, ne si consiglia comunque una corretta implementazione per altri motori di ricerca.""",

        'headings': """Gli Headings o intestazioni aiutano i Motori di Ricerca a capire il contenuto della pagina e quindi a classificarla. Hanno una numerazione che identifica l'importanza che va dall'uno (H1) al sei (H6), dove con H1 si identifica il titolo del contenuto della pagina. È indispensabile che l'H1 sia presente in ogni pagina del sito e che il suo contenuto sia unico.""",

        'paragraphs': """All'interno di un paragrafo (tag html: <p>...</p>) si inserisce il contenuto testuale della pagina. L'utilizzo di questo tag permette ai motori di ricerca di capire che il testo presente all'interno è contenuto rilevante per le ricerche degli utenti.""",

        'images': """Per rendere le immagini più facilmente comprensibili al motore di ricerca, il file deve avere un nome il più possibile corrispondente al contenuto dell'immagine. È inoltre indispensabile usare l'attributo alt in cui indicare in modo preciso ai motori di ricerca il contenuto dell'immagine.""",

        'linking': """Il linking interno strategico non si limita a collegare pagine correlate, ma mira a creare un flusso di autorità (link equity) dalle pagine informative (blog, guide, FAQ) verso le pagine transazionali (prodotti, servizi, checkout). Questa pratica valorizza i contenuti commerciali attraverso il supporto dei contenuti informativi, migliorando il posizionamento delle pagine strategiche per il business.""",

        'structured_data': """I microdati sono una forma di markup semantico che utilizza tag specifici per etichettare elementi di una pagina web (come titoli, descrizioni, prezzi, recensioni, ecc.). Questi tag forniscono ai motori di ricerca informazioni aggiuntive sul tipo di contenuto presente nella pagina, rendendo più facile per loro comprendere il significato e il contesto delle informazioni.""",
    }

    def __init__(self, site_name: str, site_url: str):
        """Initialize generator.

        Args:
            site_name: Name of the site being analyzed
            site_url: URL of the site
        """
        self.site_name = site_name
        self.site_url = site_url

    def generate_introduction(self) -> str:
        """Generate introduction section."""
        return f"""Questo documento ha lo scopo di identificare le aree d'intervento per il sito {self.site_url} e consigliare gli eventuali accorgimenti da effettuare al fine di migliorare l'indicizzazione e il posizionamento del sito sui principali motori di ricerca. Con l'implementazione di quanto scritto, si potrà:

- Migliorare la visibilità del sito sui motori di ricerca;
- Incrementare il posizionamento all'interno delle pagine dei risultati della ricerca (SERP);
- Aumentare la possibilità che, visualizzato il sito nella SERP, l'utente lo clicchi (CTR);
- Migliorare l'usabilità del sito e l'esperienza dell'utente durante la navigazione.

Gli interventi di ottimizzazione hanno quindi come obiettivo l'aumento del traffico sul sito e di conseguenza le conversioni, tenendo in forte considerazione il miglioramento di tutta l'esperienza di navigazione dell'utente."""

    def generate_structure_intro(self) -> str:
        """Generate document structure introduction."""
        return """Il documento è strutturato in capitoli. Ogni capitolo corrisponde ad un elemento fondamentale per l'ottimizzazione del sito. In ogni capitolo sono presenti:

- Un approfondimento sullo specifico intervento da effettuare;
- Una descrizione della situazione attuale;
- Gli eventuali miglioramenti che saranno da effettuare."""

    def get_premise(self, section: str) -> str:
        """Get premise text for a section.

        Args:
            section: Section key

        Returns:
            Premise text
        """
        return self.PREMISES.get(section, "")

    def generate_alberatura(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate alberatura section narrative.

        Args:
            data: Analysis data

        Returns:
            NarrativeSection
        """
        total = data.get('total_pages', 0)
        depth_dist = data.get('depth_distribution', {})
        deep_pages = data.get('deep_pages_count', 0)
        orphans = data.get('orphan_pages_count', 0)

        # Build current situation with consultant-style narrative
        situation_parts = []

        if total > 0:
            situation_parts.append(
                f"Navigando il sito {self.site_name}, è stata mappata la struttura complessiva "
                f"che comprende {total} pagine indicizzabili."
            )

        if depth_dist:
            shallow = sum(count for depth, count in depth_dist.items() if int(depth) <= 2)
            deep = sum(count for depth, count in depth_dist.items() if int(depth) > 3)
            if shallow > 0 and deep == 0:
                situation_parts.append(
                    f"L'architettura risulta ben organizzata: la maggior parte delle pagine ({shallow}) "
                    f"è raggiungibile entro 2 click dalla homepage, permettendo sia agli utenti che "
                    f"ai motori di ricerca di accedere facilmente ai contenuti."
                )
            elif shallow > 0 and deep > 0:
                situation_parts.append(
                    f"Se da un lato {shallow} pagine sono facilmente raggiungibili (entro 2 click dalla home), "
                    f"dall'altro {deep} pagine risultano troppo profonde nella gerarchia. "
                    f"Questa profondità eccessiva può penalizzare l'indicizzazione e ridurre "
                    f"la visibilità di contenuti potenzialmente importanti."
                )

        if orphans > 0:
            situation_parts.append(
                f"Un aspetto critico riguarda le {orphans} pagine orfane identificate: "
                f"si tratta di contenuti pubblicati ma non raggiungibili attraverso la navigazione interna, "
                f"che rischiano di non essere mai scoperti dai motori di ricerca."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            f"Analizzando la struttura del sito {self.site_name}, l'alberatura risulta ben organizzata "
            f"con una gerarchia chiara e una buona raggiungibilità delle pagine."
        )

        # Build improvements
        improvements_parts = []

        if deep_pages > 0:
            improvements_parts.append(
                "Si consiglia di rivedere la struttura del sito per rendere le pagine più profonde "
                "raggiungibili con meno click dalla homepage."
            )

        if orphans > 0:
            improvements_parts.append(
                "È necessario creare link interni verso le pagine orfane per renderle raggiungibili "
                "sia dagli utenti che dai motori di ricerca."
            )

        if not improvements_parts:
            improvements = "Non sono necessari miglioramenti significativi."
        else:
            improvements = " ".join(improvements_parts)

        severity = 1 if (deep_pages > 10 or orphans > 5) else (2 if (deep_pages > 0 or orphans > 0) else 3)

        return NarrativeSection(
            title="Alberatura",
            premise=self.get_premise('alberatura'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_canonical(self, data: Dict[str, Any], duplicates_data: Dict[str, Any] = None) -> NarrativeSection:
        """Generate canonical/duplicates section narrative."""
        canonical_issues = data.get('canonical_issues', {})
        missing = canonical_issues.get('missing', 0)
        mismatches = canonical_issues.get('mismatches', 0)

        # Critical errors
        to_404 = canonical_issues.get('pointing_to_404', 0)
        to_redirect = canonical_issues.get('pointing_to_redirect', 0)
        relative_urls = canonical_issues.get('relative_urls', 0)
        http_on_https = canonical_issues.get('http_on_https', 0)

        # Classification
        intentional = canonical_issues.get('intentional_count', 0)
        errors = canonical_issues.get('errors_count', 0)

        # Example lists for specificity
        to_404_list = canonical_issues.get('pointing_to_404_list', [])
        errors_list = canonical_issues.get('errors_list', [])
        missing_list = canonical_issues.get('missing_list', [])

        situation_parts = []
        has_critical = to_404 > 0

        # Critical issues first
        if to_404 > 0:
            example = f" (es. {to_404_list[0]['url']})" if to_404_list else ""
            situation_parts.append(
                f"{to_404} pagine hanno il canonical che punta a una pagina 404{example}. "
                f"Questo errore impedisce la corretta indicizzazione delle pagine interessate."
            )

        if to_redirect > 0:
            situation_parts.append(
                f"{to_redirect} pagine hanno il canonical che punta a un redirect. "
                f"Il canonical dovrebbe puntare direttamente alla destinazione finale."
            )

        # Best practice violations
        if relative_urls > 0:
            situation_parts.append(
                f"{relative_urls} pagine usano URL relativi nel canonical. "
                f"È consigliato usare URL assoluti per evitare ambiguità."
            )

        if http_on_https > 0:
            situation_parts.append(
                f"{http_on_https} pagine HTTPS hanno un canonical HTTP, creando un conflitto di segnali."
            )

        # Missing canonicals
        if missing > 0:
            example = f" (es. {missing_list[0]})" if missing_list else ""
            situation_parts.append(
                f"{missing} pagine sono prive del tag canonical{example}. "
                f"Ogni pagina dovrebbe avere almeno un canonical autoreferenziale."
            )

        # Mismatches analysis
        if mismatches > 0:
            if intentional > 0 and errors > 0:
                situation_parts.append(
                    f"Delle {mismatches} pagine con canonical diverso dall'URL, "
                    f"{intentional} appaiono intenzionali (varianti prodotto, parametri tracking) "
                    f"mentre {errors} sembrano errori di configurazione da correggere."
                )
            elif errors > 0:
                error_example = ""
                if errors_list:
                    err = errors_list[0]
                    error_example = f" (es. {err.get('url', '')} → {err.get('canonical', '')})"
                situation_parts.append(
                    f"{errors} pagine presentano canonical errati che richiedono correzione{error_example}."
                )
            elif intentional > 0:
                situation_parts.append(
                    f"{intentional} pagine hanno canonical che puntano ad altre URL, "
                    f"situazione che appare intenzionale per consolidare varianti o parametri."
                )

        # Duplicates with detailed groups
        if duplicates_data:
            exact = duplicates_data.get('duplicates', {}).get('exact', 0)
            near = duplicates_data.get('duplicates', {}).get('near', 0)
            groups_detail = duplicates_data.get('groups_detail', [])

            if exact > 0 or near > 0:
                total_dup = exact + near
                groups_count = duplicates_data.get('groups', 0)

                # Build detailed description with examples
                dup_parts = [f"L'analisi dei contenuti ha rilevato {total_dup} pagine con contenuto duplicato, distribuite in {groups_count} gruppi."]

                # Add specific examples from groups_detail
                if groups_detail:
                    for i, group in enumerate(groups_detail[:3]):  # Show up to 3 groups
                        urls = group.get('urls', [])
                        similarity = group.get('similarity', 0)
                        category = group.get('category', '')

                        if len(urls) >= 2:
                            url_examples = ", ".join(urls[:3])
                            if len(urls) > 3:
                                url_examples += f" e altre {len(urls) - 3} pagine"

                            category_desc = "identico" if category == 'exact' else "quasi identico"
                            dup_parts.append(
                                f"Gruppo {i+1}: le pagine {url_examples} hanno contenuto {category_desc} ({similarity}% di similarità)."
                            )

                    # Add context about what the pages are
                    if duplicates_data.get('product_variant_groups'):
                        dup_parts.append(
                            f"{len(duplicates_data['product_variant_groups'])} gruppi sembrano varianti di prodotto con descrizioni non differenziate."
                        )
                    if duplicates_data.get('parameter_groups'):
                        dup_parts.append(
                            f"{len(duplicates_data['parameter_groups'])} gruppi sono legati a parametri URL (versioni con/senza parametri)."
                        )

                situation_parts.append(" ".join(dup_parts))

        situation = " ".join(situation_parts) if situation_parts else (
            f"I tag canonical del sito {self.site_name} risultano implementati correttamente. "
            f"Non sono stati rilevati errori critici."
        )

        # Improvements based on severity
        improvements_parts = []

        if to_404 > 0:
            improvements_parts.append(
                "Correggere i canonical che puntano a pagine 404, "
                "aggiornandoli per puntare a pagine esistenti o rimuovendoli."
            )

        if to_redirect > 0:
            improvements_parts.append(
                "Aggiornare i canonical che puntano a redirect per puntare direttamente alla URL finale."
            )

        if relative_urls > 0:
            improvements_parts.append(
                "Convertire tutti i canonical da URL relativi a URL assoluti (includendo https://dominio)."
            )

        if http_on_https > 0:
            improvements_parts.append(
                "Aggiornare i canonical HTTP su pagine HTTPS per usare il protocollo HTTPS."
            )

        if missing > 0:
            improvements_parts.append(
                "Implementare canonical autoreferenziali sulle pagine che ne sono prive."
            )

        if errors > 0:
            improvements_parts.append(
                "Verificare e correggere i canonical classificati come probabili errori."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else "Non sono necessari miglioramenti significativi."

        # Severity: 1=critico, 2=importante, 3=ok
        severity = 1 if has_critical else (2 if (missing > 10 or errors > 5 or relative_urls > 0) else 3)

        return NarrativeSection(
            title="Canonicalizzazione e contenuto duplicato",
            premise=self.get_premise('canonical'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_hreflang(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate hreflang section narrative."""
        languages = data.get('hreflang', {}).get('languages', [])
        non_reciprocal = data.get('hreflang', {}).get('non_reciprocal', 0)
        invalid_codes = data.get('hreflang', {}).get('invalid_codes', 0)
        x_default_issues = data.get('hreflang', {}).get('x_default_issues', 0)

        if not languages:
            return NarrativeSection(
                title="Hreflang",
                premise=self.get_premise('hreflang'),
                current_situation="Il sito non presenta implementazione hreflang, suggerendo una singola versione linguistica.",
                improvements="Se il sito è disponibile in più lingue, si consiglia di implementare i tag hreflang.",
                severity=3
            )

        situation_parts = [
            f"Il sito presenta versioni in {len(languages)} lingue: {', '.join(languages)}."
        ]

        if non_reciprocal > 0:
            situation_parts.append(
                f"Sono stati rilevati {non_reciprocal} casi di hreflang non reciproci, "
                f"ovvero pagine che linkano una versione linguistica senza ricevere il link di ritorno."
            )

        if invalid_codes > 0:
            situation_parts.append(
                f"Sono presenti {invalid_codes} codici lingua non validi secondo lo standard ISO."
            )

        if x_default_issues > 0:
            situation_parts.append(
                f"L'implementazione di x-default presenta {x_default_issues} problemi."
            )

        situation = " ".join(situation_parts)

        improvements_parts = []

        if non_reciprocal > 0:
            improvements_parts.append(
                "Si consiglia di correggere gli hreflang non reciproci assicurandosi che "
                "ogni pagina abbia link bidirezionali con le sue traduzioni."
            )

        if invalid_codes > 0:
            improvements_parts.append(
                "Correggere i codici lingua non validi utilizzando il formato ISO 639-1 per la lingua "
                "e ISO 3166-1 Alpha 2 per la regione (es: 'it', 'en-GB', 'de-AT')."
            )

        if x_default_issues > 0:
            improvements_parts.append(
                "L'x-default dovrebbe puntare a una pagina di selezione lingua, "
                "non alla stessa pagina che si sta visitando."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else "L'implementazione hreflang risulta corretta."

        severity = 1 if non_reciprocal > 10 else (2 if non_reciprocal > 0 else 3)

        return NarrativeSection(
            title="Hreflang",
            premise=self.get_premise('hreflang'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_title(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate title section narrative."""
        titles = data.get('titles', {})
        without = titles.get('without_title', 0)
        duplicates = titles.get('duplicates', 0)
        length_dist = titles.get('length_distribution', {})

        situation_parts = []

        if without > 0:
            situation_parts.append(
                f"Esaminando i meta title del sito, emerge una criticità importante: "
                f"{without} pagine risultano prive di questo elemento fondamentale. "
                f"Il title è la prima cosa che l'utente vede nei risultati di ricerca "
                f"e la sua assenza compromette significativamente le possibilità di click."
            )

        if duplicates > 0:
            situation_parts.append(
                f"Un altro aspetto da considerare riguarda i {duplicates} gruppi di pagine "
                f"che condividono lo stesso title. Questa situazione, spesso causata da "
                f"configurazioni automatiche del CMS, impedisce di differenziare le pagine "
                f"agli occhi degli utenti e dei motori di ricerca."
            )

        long_titles = length_dist.get('long', 0)
        short_titles = length_dist.get('short', 0)

        if long_titles > 0:
            situation_parts.append(
                f"{long_titles} pagine presentano un title troppo lungo "
                f"(oltre 60 caratteri). Google troncherà questi title nei risultati di ricerca "
                f"con \"...\", potenzialmente tagliando informazioni importanti o call to action."
            )

        if short_titles > 0:
            situation_parts.append(
                f"Al contrario, {short_titles} pagine presentano title troppo brevi "
                f"(sotto 30 caratteri), sprecando spazio prezioso che potrebbe essere utilizzato "
                f"per includere keyword rilevanti e messaggi persuasivi."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            f"I title delle pagine di {self.site_name} sono implementati correttamente, "
            f"con lunghezze adeguate che permettono una buona visualizzazione nei risultati "
            f"di ricerca senza troncamenti. Non sono state rilevate duplicazioni significative."
        )

        improvements_parts = []

        if without > 0:
            improvements_parts.append(
                "Inserire i title mancanti assicurandosi che siano unici, descrittivi e "
                "contengano le keyword principali della pagina."
            )

        if duplicates > 0:
            improvements_parts.append(
                "Rivedere i title duplicati differenziandoli per riflettere il contenuto specifico di ogni pagina."
            )

        if long_titles > 0:
            improvements_parts.append(
                "Ridurre la lunghezza dei title troppo lunghi mantenendoli entro i 55-60 caratteri."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else "Non sono necessari miglioramenti significativi."

        severity = 1 if (without > 10 or duplicates > 5) else (2 if (without > 0 or duplicates > 0) else 3)

        return NarrativeSection(
            title="Title",
            premise=self.get_premise('title'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_description(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate meta description section narrative."""
        desc = data.get('descriptions', {})
        without = desc.get('without_description', 0)
        duplicates = desc.get('duplicates', 0)

        situation_parts = []

        if without > 0:
            situation_parts.append(
                f"Sono state rilevate {without} pagine senza meta description."
            )

        if duplicates > 0:
            situation_parts.append(
                f"Sono presenti {duplicates} gruppi di pagine con description duplicate."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            "Le meta description sono presenti e non presentano duplicazioni significative."
        )

        improvements_parts = []

        if without > 0:
            improvements_parts.append(
                "Inserire le meta description mancanti con testi tra i 140 e 160 caratteri, "
                "includendo una call to action e rispecchiando fedelmente il contenuto della pagina."
            )

        if duplicates > 0:
            improvements_parts.append(
                "Differenziare le description duplicate creando testi unici per ogni pagina."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else "Non sono necessari miglioramenti."

        severity = 2 if (without > 10 or duplicates > 5) else 3

        return NarrativeSection(
            title="Meta Description",
            premise=self.get_premise('description'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_performance(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate performance section narrative."""
        perf = data.get('performance', {})
        avg_time = perf.get('avg_load_time_ms', 0)
        slow_pages = perf.get('slow_pages', 0)

        situation_parts = []

        if avg_time > 0:
            avg_seconds = avg_time / 1000
            situation_parts.append(
                f"Il tempo medio di caricamento delle pagine è di {avg_seconds:.2f} secondi."
            )

            if avg_seconds > 3:
                situation_parts.append(
                    "Questo valore supera la soglia consigliata di 2.5 secondi per il Largest Contentful Paint (LCP)."
                )
            elif avg_seconds < 2.5:
                situation_parts.append(
                    "Questo valore rientra nei parametri ottimali per i Core Web Vitals."
                )

        if slow_pages > 0:
            situation_parts.append(
                f"Sono state identificate {slow_pages} pagine con tempi di caricamento superiori a 3 secondi."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            "I tempi di caricamento del sito sono nella media."
        )

        improvements = (
            "Si consiglia di ottimizzare le immagini, minimizzare CSS e JavaScript, "
            "implementare lazy loading e valutare l'utilizzo di una CDN per migliorare i tempi di caricamento."
        ) if (avg_time > 2500 or slow_pages > 0) else "Non sono necessari miglioramenti significativi."

        severity = 1 if avg_time > 4000 else (2 if avg_time > 2500 else 3)

        return NarrativeSection(
            title="Tempi di caricamento",
            premise=self.get_premise('performance'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_headings(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate headings section narrative."""
        headings = data.get('headings', {})
        without_h1 = headings.get('without_h1', 0)
        multiple_h1 = headings.get('multiple_h1', 0)
        duplicate_h1 = headings.get('duplicate_h1', 0)

        situation_parts = []

        if without_h1 > 0:
            situation_parts.append(
                f"Sono state rilevate {without_h1} pagine senza tag H1."
            )

        if multiple_h1 > 0:
            situation_parts.append(
                f"{multiple_h1} pagine presentano H1 multipli, il che può confondere i motori di ricerca "
                f"sul contenuto principale della pagina."
            )

        if duplicate_h1 > 0:
            situation_parts.append(
                f"Sono presenti {duplicate_h1} gruppi di pagine con H1 duplicati."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            "La struttura degli heading è corretta, con H1 unici e presenti in tutte le pagine."
        )

        improvements_parts = []

        if without_h1 > 0:
            improvements_parts.append(
                "Inserire un H1 unico in ogni pagina, contenente le keyword principali."
            )

        if multiple_h1 > 0:
            improvements_parts.append(
                "Mantenere un solo H1 per pagina, utilizzando H2-H6 per i sottotitoli."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else "Non sono necessari miglioramenti."

        severity = 1 if (without_h1 > 10 or multiple_h1 > 10) else (2 if (without_h1 > 0 or multiple_h1 > 0) else 3)

        return NarrativeSection(
            title="Intestazione (headings)",
            premise=self.get_premise('headings'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_images(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate images section narrative."""
        images = data.get('images', {})
        total = images.get('total', 0)
        without_alt = images.get('without_alt', 0)
        empty_alt = images.get('empty_alt', 0)
        generic_alt = images.get('generic_alt', 0)

        problematic = without_alt + empty_alt + generic_alt

        situation_parts = [f"Il sito contiene {total} immagini."]

        if problematic > 0:
            situation_parts.append(
                f"Di queste, {without_alt} sono senza attributo alt, "
                f"{empty_alt} hanno alt vuoto e {generic_alt} hanno alt generico."
            )

        situation = " ".join(situation_parts)

        if problematic > 0:
            improvements = (
                "Si consiglia di rivedere le immagini problematiche, assegnando alt text "
                "descrittivi e pertinenti al contenuto dell'immagine. "
                "Questo migliorerà l'accessibilità e il posizionamento in Google Images."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 2 if problematic > total * 0.2 else 3

        return NarrativeSection(
            title="Immagini",
            premise=self.get_premise('images'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_linking(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate strategic internal linking section narrative.

        Uses strategic linking data (page classification + link flow) if available,
        otherwise falls back to basic technical metrics.
        """
        # Check if strategic linking data is available
        strategic = data.get('strategic_linking', {})

        if strategic and 'page_type_distribution' in strategic:
            return self._generate_strategic_linking_narrative(strategic)
        else:
            return self._generate_basic_linking_narrative(data)

    def _generate_strategic_linking_narrative(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate narrative based on strategic linking analysis."""
        distribution = data.get('page_type_distribution', {})
        trans_count = distribution.get('transactional', 0)
        info_count = distribution.get('informational', 0)
        nav_count = distribution.get('navigational', 0)

        info_to_trans = data.get('info_to_trans_count', 0)
        trans_to_info = data.get('trans_to_info_count', 0)
        ratio = data.get('info_to_trans_ratio', 0)
        score = data.get('strategic_linking_score', 50)

        isolated_trans = data.get('isolated_transactional', [])
        isolated_info = data.get('isolated_informational', [])
        hub_pages = data.get('hub_pages', [])

        situation_parts = []

        # Describe page type composition
        total = trans_count + info_count + nav_count
        if total > 0:
            if trans_count > 0 and info_count > 0:
                situation_parts.append(
                    f"Il sito \"{self.site_name}\" presenta contenuti sia transazionali "
                    f"({trans_count} pagine: prodotti, servizi) che informativi "
                    f"({info_count} pagine: blog, guide)."
                )
            elif trans_count > 0 and info_count == 0:
                situation_parts.append(
                    f"Il sito \"{self.site_name}\" presenta solo contenuti transazionali "
                    f"({trans_count} pagine) senza un supporto informativo strutturato."
                )
            elif info_count > 0 and trans_count == 0:
                situation_parts.append(
                    f"Il sito \"{self.site_name}\" presenta principalmente contenuti informativi "
                    f"({info_count} pagine) senza chiare pagine transazionali da valorizzare."
                )

        # Describe link flow
        if trans_count > 0 and info_count > 0:
            if info_to_trans == 0:
                situation_parts.append(
                    "Non risultano presenti link interni finalizzati alla valorizzazione "
                    "delle pagine transazionali da parte dei contenuti informativi."
                )
            elif ratio < 0.1:
                situation_parts.append(
                    f"Solo {info_to_trans} link collegano contenuti informativi a pagine transazionali "
                    f"(ratio {ratio*100:.1f}%), indicando un supporto molto limitato."
                )
            elif ratio < 0.25:
                situation_parts.append(
                    f"Sono presenti {info_to_trans} link da contenuti informativi verso pagine transazionali "
                    f"(ratio {ratio*100:.1f}%), ma il supporto potrebbe essere incrementato."
                )
            else:
                situation_parts.append(
                    f"La struttura di linking mostra {info_to_trans} collegamenti "
                    f"da contenuti informativi verso pagine transazionali (ratio {ratio*100:.1f}%), "
                    f"indicando una buona strategia di supporto."
                )

        # Isolated pages issues
        if len(isolated_trans) > 0:
            examples = isolated_trans[:2]
            example_urls = ", ".join([p.get('url', '')[-40:] for p in examples])
            situation_parts.append(
                f"{len(isolated_trans)} pagine transazionali risultano isolate, "
                f"senza ricevere supporto da contenuti informativi (es. ...{example_urls})."
            )

        if len(isolated_info) > 0:
            situation_parts.append(
                f"{len(isolated_info)} pagine informative non linkano a contenuti transazionali, "
                f"sprecando opportunità di conversione."
            )

        # Hub pages
        if hub_pages:
            info_hubs = sum(1 for h in hub_pages if h.get('type') == 'informational')
            if info_hubs > 0:
                situation_parts.append(
                    f"Sono state identificate {info_hubs} pagine informative che fungono da hub "
                    f"per la distribuzione di link equity."
                )
        elif trans_count > 0 and info_count > 0:
            situation_parts.append(
                "Non sono state identificate pagine hub significative per la distribuzione di link equity."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            f"La struttura di linking interno del sito {self.site_name} non presenta "
            f"una chiara distinzione tra contenuti informativi e transazionali."
        )

        # Improvements
        improvements_parts = []

        if info_to_trans == 0 and trans_count > 0 and info_count > 0:
            improvements_parts.append(
                "Implementare una strategia di linking interno che colleghi i contenuti del blog "
                "e delle guide alle pagine prodotto/servizio correlate, usando CTA contestuali."
            )
        elif ratio < 0.15 and trans_count > 0:
            improvements_parts.append(
                "Aumentare i link contestuali dagli articoli informativi verso le pagine transazionali, "
                "con anchor text descrittivi che includano le keyword target."
            )

        if len(isolated_trans) > 5:
            improvements_parts.append(
                f"Creare contenuti informativi (guide, FAQ, blog post) che supportino "
                f"le {len(isolated_trans)} pagine transazionali attualmente isolate."
            )

        if len(isolated_info) > 5:
            improvements_parts.append(
                f"Aggiungere CTA e link verso prodotti/servizi nelle {len(isolated_info)} "
                f"pagine informative che attualmente non valorizzano contenuti commerciali."
            )

        if not hub_pages and info_count > 5:
            improvements_parts.append(
                "Creare pagine pillar/cornerstone che aggreghino i contenuti per topic "
                "e distribuiscano link equity verso le pagine correlate."
            )

        improvements = " ".join(improvements_parts) if improvements_parts else (
            "La struttura di linking strategico è adeguata. "
            "Continuare a creare contenuti informativi che supportino le pagine commerciali."
        )

        # Severity based on strategic score
        if score < 40:
            severity = 1  # Critical
        elif score < 70:
            severity = 2  # Warning
        else:
            severity = 3  # OK

        return NarrativeSection(
            title="Linking interno strategico",
            premise=self.get_premise('linking'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def _generate_basic_linking_narrative(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate basic linking narrative (fallback when strategic data unavailable)."""
        linking = data.get('internal_linking', {})

        orphans = linking.get('orphan_pages', 0)
        few_incoming = linking.get('pages_with_few_incoming', 0)
        dead_ends = linking.get('dead_end_pages', 0)
        avg_incoming = linking.get('avg_incoming_links', 0)

        situation_parts = []

        if orphans > 0:
            situation_parts.append(
                f"Sono state identificate {orphans} pagine orfane, "
                f"isolate dalla struttura di navigazione."
            )

        if few_incoming > 0:
            situation_parts.append(
                f"{few_incoming} pagine ricevono pochi link interni (1-2)."
            )

        if dead_ends > 0:
            situation_parts.append(
                f"{dead_ends} pagine non contengono link in uscita (dead-end)."
            )

        situation = " ".join(situation_parts) if situation_parts else (
            f"La struttura di linking del sito {self.site_name} appare equilibrata "
            f"con una media di {avg_incoming:.1f} link in ingresso per pagina."
        )

        improvements = (
            "Per un'analisi strategica del linking interno, "
            "attivare la classificazione AI delle pagine."
        )

        severity = 1 if orphans > 10 else (2 if orphans > 0 or dead_ends > 5 else 3)

        return NarrativeSection(
            title="Linking interno",
            premise=self.get_premise('linking'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_structured_data(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate structured data section narrative."""
        total = data.get('total_pages', 0)
        with_schema = data.get('pages_with_schema', 0)
        without_schema = data.get('pages_without_schema', 0)
        types = data.get('schema_types', {})
        issues = data.get('issues', {})

        situation_parts = []

        coverage = (with_schema / total * 100) if total > 0 else 0
        situation_parts.append(
            f"Il {coverage:.1f}% delle pagine ({with_schema} su {total}) presenta dati strutturati."
        )

        if types:
            types_str = ", ".join(types.keys())
            situation_parts.append(f"I tipi di schema rilevati sono: {types_str}.")

        errors = issues.get('errors', 0)
        if errors > 0:
            situation_parts.append(
                f"Sono stati rilevati {errors} errori di implementazione nei dati strutturati."
            )

        situation = " ".join(situation_parts)

        if with_schema == 0:
            improvements = (
                "Si consiglia di implementare dati strutturati Schema.org per abilitare "
                "i rich results nei risultati di ricerca. Iniziare con Organization e WebSite "
                "sulla homepage, e Product per le pagine prodotto."
            )
        elif errors > 0:
            improvements = (
                "Correggere gli errori di implementazione nei dati strutturati esistenti "
                "per garantire la corretta visualizzazione dei rich results."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 2 if with_schema == 0 else (2 if errors > 0 else 3)

        return NarrativeSection(
            title="Microdati",
            premise=self.get_premise('structured_data'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_url(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate URL structure section narrative."""
        url_issues = data.get('url_issues', {})
        underscore = url_issues.get('underscore', 0)
        uppercase = url_issues.get('uppercase', 0)
        double_slash = url_issues.get('double_slash', 0)
        with_params = url_issues.get('with_parameters', 0)

        situation_parts = []
        total_issues = underscore + uppercase + double_slash

        if total_issues == 0:
            situation_parts.append(
                f"Le URL del sito {self.site_name} risultano ben strutturate, "
                f"seguendo le best practice SEO con l'uso di trattini come separatori "
                f"e assenza di caratteri problematici."
            )
        else:
            if underscore > 0:
                situation_parts.append(
                    f"{underscore} URL contengono underscore invece di trattini. "
                    f"Google consiglia l'uso del trattino (-) come separatore di parole."
                )
            if uppercase > 0:
                situation_parts.append(
                    f"{uppercase} URL contengono lettere maiuscole, "
                    f"che possono causare problemi di duplicazione."
                )
            if double_slash > 0:
                situation_parts.append(
                    f"{double_slash} URL presentano doppi slash, "
                    f"indicando possibili errori di configurazione."
                )

        situation = " ".join(situation_parts)

        if total_issues > 0:
            improvements = (
                "Si consiglia di correggere le URL problematiche: "
                "usare trattini (-) invece di underscore, "
                "convertire le lettere in minuscolo e rimuovere i doppi slash. "
                "Implementare redirect 301 dalle vecchie URL alle nuove."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 1 if total_issues > 20 else (2 if total_issues > 0 else 3)

        return NarrativeSection(
            title="Struttura URL",
            premise=self.get_premise('url'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_sitemap(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate sitemap section narrative."""
        sitemap = data.get('sitemap', {})
        found = sitemap.get('found', False)
        urls_count = sitemap.get('urls_count', 0)
        missing = sitemap.get('missing_from_sitemap', 0)
        errors = sitemap.get('urls_with_errors', 0)

        situation_parts = []

        if not found:
            situation_parts.append(
                f"Il sito {self.site_name} non presenta una sitemap XML accessibile. "
                f"Questo può rallentare significativamente l'indicizzazione delle pagine."
            )
        else:
            situation_parts.append(
                f"La sitemap è presente e contiene {urls_count} URL."
            )
            if missing > 0:
                situation_parts.append(
                    f"Sono state rilevate {missing} pagine indicizzabili non presenti nella sitemap."
                )
            if errors > 0:
                situation_parts.append(
                    f"{errors} URL nella sitemap presentano errori (404, redirect, ecc.)."
                )

        situation = " ".join(situation_parts)

        if not found:
            improvements = (
                "Creare una sitemap XML e registrarla in Google Search Console. "
                "Includere tutte le pagine indicizzabili e mantenerla aggiornata."
            )
        elif missing > 0 or errors > 0:
            improvements = (
                "Aggiornare la sitemap aggiungendo le pagine mancanti "
                "e rimuovendo gli URL che restituiscono errori."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 1 if not found else (2 if (missing > 10 or errors > 5) else 3)

        return NarrativeSection(
            title="Sitemap",
            premise=self.get_premise('sitemap'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_robots(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate robots.txt section narrative."""
        robots = data.get('robots_txt', {})
        found = robots.get('found', False)
        sitemap_declared = robots.get('sitemap_declared', False)
        issues = robots.get('issues', 0)

        situation_parts = []

        if not found:
            situation_parts.append(
                f"Il file robots.txt non è stato trovato sul sito {self.site_name}."
            )
        else:
            situation_parts.append("Il file robots.txt è presente.")
            if sitemap_declared:
                situation_parts.append("La sitemap è correttamente dichiarata nel file.")
            else:
                situation_parts.append("La sitemap non è dichiarata nel file robots.txt.")
            if issues > 0:
                situation_parts.append(f"Sono stati rilevati {issues} potenziali problemi nella configurazione.")

        situation = " ".join(situation_parts)

        if not found:
            improvements = "Creare un file robots.txt e dichiarare la posizione della sitemap."
        elif not sitemap_declared or issues > 0:
            improvements = (
                "Aggiungere la dichiarazione della sitemap nel robots.txt "
                "e verificare che non siano bloccate risorse necessarie per il rendering."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 2 if not found else (2 if issues > 0 else 3)

        return NarrativeSection(
            title="Robots.txt",
            premise=self.get_premise('robots'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_https(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate HTTPS section narrative."""
        https = data.get('https', {})
        uses_https = https.get('uses_https', False)
        ssl_valid = https.get('ssl_valid', False)
        mixed_content = https.get('mixed_content', 0)
        http_links = https.get('http_links', 0)

        situation_parts = []

        if uses_https:
            situation_parts.append(f"Il sito {self.site_name} utilizza correttamente il protocollo HTTPS.")
            if ssl_valid:
                situation_parts.append("Il certificato SSL è valido.")
            else:
                situation_parts.append("Il certificato SSL presenta problemi di validità.")
            if mixed_content > 0:
                situation_parts.append(
                    f"Sono stati rilevati {mixed_content} casi di mixed content "
                    f"(risorse HTTP caricate su pagine HTTPS)."
                )
            if http_links > 0:
                situation_parts.append(f"{http_links} link interni puntano ancora a versioni HTTP.")
        else:
            situation_parts.append(
                f"Il sito {self.site_name} non utilizza HTTPS. "
                f"Questo è un fattore di ranking negativo e compromette la sicurezza degli utenti."
            )

        situation = " ".join(situation_parts)

        if not uses_https:
            improvements = "Migrare urgentemente il sito a HTTPS e implementare redirect 301 da HTTP."
        elif mixed_content > 0 or http_links > 0:
            improvements = (
                "Correggere i problemi di mixed content aggiornando i riferimenti HTTP a HTTPS. "
                "Aggiornare i link interni per utilizzare il protocollo sicuro."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 1 if not uses_https else (2 if mixed_content > 5 else 3)

        return NarrativeSection(
            title="HTTPS",
            premise=self.get_premise('https'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )

    def generate_errors(self, data: Dict[str, Any]) -> NarrativeSection:
        """Generate errors/redirects section narrative."""
        redirects = data.get('redirects', {})
        chains = redirects.get('chains', 0)
        loops = redirects.get('loops', 0)
        to_404 = redirects.get('internal_to_404', 0)
        to_redirects = redirects.get('internal_to_redirects', 0)

        situation_parts = []

        if to_404 > 0:
            situation_parts.append(
                f"Sono stati rilevati {to_404} link interni che puntano a pagine 404. "
                f"Questi link rotti peggiorano l'esperienza utente e disperdono il crawl budget."
            )

        if chains > 0:
            situation_parts.append(
                f"Sono presenti {chains} catene di redirect, "
                f"che rallentano il caricamento e diluiscono il PageRank."
            )

        if loops > 0:
            situation_parts.append(
                f"Sono stati rilevati {loops} loop di redirect, "
                f"che impediscono l'accesso alle pagine coinvolte."
            )

        if to_redirects > 0:
            situation_parts.append(
                f"{to_redirects} link interni puntano a pagine che effettuano redirect."
            )

        if not situation_parts:
            situation_parts.append(
                f"Non sono stati rilevati problemi significativi di errori 404 o redirect sul sito {self.site_name}."
            )

        situation = " ".join(situation_parts)

        total_issues = to_404 + chains + loops
        if total_issues > 0:
            improvements = (
                "Correggere i link rotti aggiornandoli o rimuovendoli. "
                "Risolvere le catene di redirect puntando direttamente alla destinazione finale. "
                "Eliminare i loop di redirect identificando la configurazione errata."
            )
        else:
            improvements = "Non sono necessari miglioramenti significativi."

        severity = 1 if (to_404 > 10 or loops > 0) else (2 if total_issues > 0 else 3)

        return NarrativeSection(
            title="Errori 404 e Redirect",
            premise=self.get_premise('errors'),
            current_situation=situation,
            improvements=improvements,
            severity=severity
        )
