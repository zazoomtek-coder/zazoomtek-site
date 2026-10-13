/* ZazoomTek HOME 45/35/20: approved interactive layout.
   Keep canonical article feed markers in index.html for all importers.
   Reuse real cards, reviews, menus, guides, videos and Shorts. */
(function() {
 "use strict";
 const path=window.location.pathname;
 if(!["/","/index.html","/anteprima-home-produzione-validazione-20261013.html"].includes(path)) return;
 function setup(){
  const layout=document.querySelector('main.page .layout');
  const main=layout&&layout.querySelector(':scope > .maincol');
  const side=layout&&layout.querySelector(':scope > aside.sidebar');
  const original=document.querySelector('section.module#articoli');
  const latest=main&&main.querySelector(".latest-reviews-module");
  const guide=main&&main.querySelector("#ztHomeGuide");
  if(!main||!side||!original||!latest||!guide)return;
  if(document.querySelector(".ztp-final-three"))return;
  const rows=[...original.querySelectorAll('.article-list > article.article-row')];
  if(rows.length<10)return;
  const fragmentHTML="<section class=\"ztp-news-area\" id=\"articoli\" aria-label=\"Ultimi articoli suddivisi tra Tech e Gaming\">\n<div class=\"ztp-split-heading\"><div><span class=\"ztp-kicker\"></span><h2>Le ultime notizie di ZazoomTek</h2></div><span class=\"ztp-count\">15 news · Tech e Gaming</span></div>\n<div class=\"ztp-three-columns ztp-final-three\" id=\"articleList\">\n<div class=\"ztp-primary-feed\">\n<div class=\"ztp-two-news-columns\">\n<section class=\"ztp-news-column ztp-news-tech\" aria-labelledby=\"ztp-tech-heading\"><header class=\"ztp-news-head\"><h2 id=\"ztp-tech-heading\"><span>ULTIMI ARTICOLI</span><b>TECH</b></h2><small>8 news</small></header><div class=\"ztp-news-items\">\n\n\n\n\n\n\n</div></section>\n<section class=\"ztp-news-column ztp-news-gaming\" aria-labelledby=\"ztp-gaming-heading\"><header class=\"ztp-news-head\"><h2 id=\"ztp-gaming-heading\"><span>ULTIMI ARTICOLI</span><b>GAMING</b></h2><small>7 news</small></header><div class=\"ztp-news-items\">\n\n\n\n\n\n<div class=\"ztp-more-gaming\" id=\"ztpMoreGaming\">\n<div class=\"ztp-more-label\">ALTRE NOTIZIE GAMING</div>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"0\" data-search=\"news: ea sports fc 27, tornano le stelle del futuro con rio ngumoha protagonista del team 1 news news: ea sports fc 27, tornano le stelle del futuro con rio ngumoha protagonista del team 1\nea sports fc 27 riporta in primo piano stelle del futuro, la campagna di football ultimate team dedicata ai giovani talenti destinati a diventare protagonisti del calcio mondiale. il team 1 è disponibile dal 9 al 16 ottobre 2026 e vede come volto principale rio ngumoha del liverpool, affiancato da una selezione di promesse provenienti dai principali campionati maschili e femminili.\n⠀\nfuture stars returns earlier than usual in ea sports fc 27, celebrating some of the most promising young players in world football. liverpool’s rio ngumoha headlines team 1, available in football ultimate team from october 9 to october 16, 2026.\n⠀\nrio ngumoha guida il team 1\nil protagonista principale di questa prima selezione è rio ngumoha, giovane talento del liverpool e ambasciatore di ea sports fc. dopo essere diventato il più giovane marcatore nella storia del club grazie al gol decisivo realizzato contro il newcastle nella scorsa stagione, ngumoha ha successivamente debuttato anche con la nazionale inglese, ent\"><a href=\"news-UgkxSZwRsjwa-UE_dTpIcqSMfUbFwtkh3Jn5.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/pY0m2L6tOuYQRHdka4YMSiuhPg84FdSbOUUrhlcXCkNe3xOwjfshTHz0QE0M6OIZVTIaEwAbe-9p=s1600-rw-nd-v1\" alt=\"News: EA SPORTS FC 27, tornano le Stelle del Futuro con Rio Ngumoha protagonista del Team 1\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxSZwRsjwa-UE_dTpIcqSMfUbFwtkh3Jn5.html\">News: EA SPORTS FC 27, tornano le Stelle del Futuro con Rio Ngumoha protagonista del Team 1</a></h3><div class=\"article-meta\">ZazoomTek · 11 ottobre 2026</div><p>EA SPORTS FC 27 riporta in primo piano Stelle del Futuro, la campagna di Football Ultimate Team dedicata ai giovani talenti destinati a diventare protagonisti del calcio mondiale. Il Team 1 è disponibile dal 9 al 16 ottobre 2026…</p><a class=\"read-more\" href=\"news-UgkxSZwRsjwa-UE_dTpIcqSMfUbFwtkh3Jn5.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"1\" data-search=\"news: call of duty modern warfare 4, dmz deep dive parte 2 svela fob, crafting, armi e accesso anticipato news news: call of duty modern warfare 4, dmz deep dive parte 2 svela fob, crafting, armi e accesso anticipato\nactivision ha pubblicato un nuovo approfondimento dedicato alla modalità dmz di call of duty: modern warfare 4, concentrandosi questa volta sulla struttura della fob, sui sistemi di crafting, sull’acquisizione delle armi, sulle taglie, sulle scorte e sulla progressione. la novità più importante riguarda però l’accesso anticipato: chi effettuerà il preordine digitale di modern warfare 4 potrà entrare in dmz già dal 20 ottobre 2026.\n⠀\nthe second dmz deep dive for call of duty: modern warfare 4 reveals more details about the fob, weapon acquisition, crafting, bounties, loadouts and progression systems. players who digitally preorder modern warfare 4 will also receive early access to dmz starting october 20, 2026.\n⠀\nla fob diventa il centro operativo di dmz\nil nuovo approfondimento mostra più nel dettaglio il funzionamento della fob, la base dalla quale i giocatori potranno prepararsi prima delle incursioni. le diverse stazioni presenti al suo interno saranno legate alla g\"><a href=\"news-UgkxFcKuOM5B9s3C-I_wnL7Y-0E4nj3h7bXb.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/q14FYSA6R5xDB4mMIZDhHGXz272eXMpB9lwIbLE5wvuK6C87KEULSTTIpf1Sxv75SUmbzuMDTSCK=s1600-rw-nd-v1\" alt=\"News: Call of Duty Modern Warfare 4, DMZ Deep Dive Parte 2 svela FOB, crafting, armi e accesso anticipato\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxFcKuOM5B9s3C-I_wnL7Y-0E4nj3h7bXb.html\">News: Call of Duty Modern Warfare 4, DMZ Deep Dive Parte 2 svela FOB, crafting, armi e accesso anticipato</a></h3><div class=\"article-meta\">ZazoomTek · 11 ottobre 2026</div><p>Activision ha pubblicato un nuovo approfondimento dedicato alla modalità DMZ di Call of Duty: Modern Warfare 4, concentrandosi questa volta sulla struttura della FOB, sui sistemi di crafting, sull’acquisizione delle armi, sulle…</p><a class=\"read-more\" href=\"news-UgkxFcKuOM5B9s3C-I_wnL7Y-0E4nj3h7bXb.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"2\" data-search=\"news: crazy taxi: world tour corre in brasile, sega svela la quarta mappa della campagna news news: crazy taxi: world tour corre in brasile, sega svela la quarta mappa della campagna\n\nsega ha presentato al brasil game show 2026 una nuova ambientazione di crazy taxi: world tour, confermando il brasile come quarta delle cinque mappe previste nella campagna narrativa tour mondiale. la presentazione è stata affidata a kenji kanno, creatore originale di crazy taxi e producer del nuovo capitolo, che ha mostrato il primo trailer dedicato alla nuova area.\n⠀\ncrazy taxi: world tour is heading to brazil with a new map inspired by vibrant city streets, beaches and coastal landscapes. the brazil location is the fourth of five maps featured in the game’s world tour single-player campaign, with the full game scheduled for 2027.\n⠀\nil brasile entra nel tour mondiale\nla nuova mappa porta i giocatori attraverso un’ambientazione caratterizzata da strade urbane molto vivaci, zone costiere e panorami ispirati al territorio brasiliano. l’obiettivo del team è ricreare il contrasto tra la frenesia delle aree cittadine e gli scenari naturali che circondano la città, mantenendo il ritmo estremamente veloce e\"><a href=\"news-UgkxHwO-OKR3z-qEkJL0MBsZS_tMU0R5Q0fi.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/PdcP0LGfc9LCO05zLQnPdX_jLsp3pxHl_vMGM7x_MsuJgjNeJ_knp1FEP1fvcldjqT7DFnFb09J3dg=s1600-rw-nd-v1\" alt=\"News: Crazy Taxi: World Tour corre in Brasile, SEGA svela la quarta mappa della campagna\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxHwO-OKR3z-qEkJL0MBsZS_tMU0R5Q0fi.html\">News: Crazy Taxi: World Tour corre in Brasile, SEGA svela la quarta mappa della campagna</a></h3><div class=\"article-meta\">ZazoomTek · 11 ottobre 2026</div><p>SEGA ha presentato al Brasil Game Show 2026 una nuova ambientazione di Crazy Taxi: World Tour, confermando il Brasile come quarta delle cinque mappe previste nella campagna narrativa Tour Mondiale. La presentazione è stata…</p><a class=\"read-more\" href=\"news-UgkxHwO-OKR3z-qEkJL0MBsZS_tMU0R5Q0fi.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"3\" data-search=\"news: rockbeasts arriverà a gennaio 2027, demo gratuita su steam e cast con matthew mercer, sam riegel e liam o’brien news news: rockbeasts arriverà a gennaio 2027, demo gratuita su steam e cast con matthew mercer, sam riegel e liam o’brien\nlichthund e critical role hanno svelato nuovi dettagli su rockbeasts, il gdr manageriale narrativo dedicato al mondo del rock, annunciando il lancio a gennaio 2027 e la disponibilità immediata di una demo gratuita su steam. il progetto racconta l’ascesa di una band grunge negli anni ’90 alternativi, combinando gestione, scelte narrative, rapporti interpersonali e una forte identità musicale.\n⠀\nrockbeasts is coming in january 2027, and a free demo is now available on steam with the first two episodes. the game also confirms matthew mercer, sam riegel and liam o’brien in the voice cast, alongside the previously announced iggy pop.\n⠀\nrockbeasts debutta con una demo gratuita su steam\nla demo permette di giocare i primi due episodi dell’avventura, offrendo un primo assaggio della struttura narrativa, della gestione della band e delle decisioni che influenzeranno il percorso del gruppo. un terzo episodio verrà aggiunto durante lo steam next fest, ampl\"><a href=\"news-Ugkx81GUVNUFspfrdJg6MW5WBAeXDwSLumGP.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/8k--O-qWG2k7aEJwhFAbBbGVLWg9-UuyAPeZa8tcsaM03WkpIGdy2hm5_of1OGpnOduEoh8unHSO=s1600-rw-nd-v1\" alt=\"News: ROCKBEASTS arriverà a gennaio 2027, demo gratuita su Steam e cast con Matthew Mercer, Sam Riegel e Liam O’Brien\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-Ugkx81GUVNUFspfrdJg6MW5WBAeXDwSLumGP.html\">News: ROCKBEASTS arriverà a gennaio 2027, demo gratuita su Steam e cast con Matthew Mercer, Sam Riegel e Liam O’Brien</a></h3><div class=\"article-meta\">ZazoomTek · 11 ottobre 2026</div><p>LICHTHUND e Critical Role hanno svelato nuovi dettagli su ROCKBEASTS, il GDR manageriale narrativo dedicato al mondo del rock, annunciando il lancio a gennaio 2027 e la disponibilità immediata di una demo gratuita su Steam. Il…</p><a class=\"read-more\" href=\"news-Ugkx81GUVNUFspfrdJg6MW5WBAeXDwSLumGP.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"4\" data-search=\"news: battlefield 6 stagione 5 porta la guerra a las vegas con tre nuove mappe, rapid royale e crossover dead space news news: battlefield 6 stagione 5 porta la guerra a las vegas con tre nuove mappe, rapid royale e crossover dead space\nelectronic arts e battlefield studios hanno svelato la stagione 5 di battlefield 6 e battlefield redsec, descritta come la stagione più grande realizzata finora. il nuovo ciclo di contenuti prenderà il via il 13 ottobre 2026 e porterà la battaglia a las vegas e nel deserto del nevada con tre nuove mappe, una nuova modalità battle royale più rapida, un evento crossover con dead space, modifiche a mappe esistenti e diverse funzionalità richieste dalla community.\n⠀\nbattlefield 6 season 5 launches on october 13, 2026, with three new maps set in and around las vegas, a faster rapid royale mode for redsec and a limited-time dead space crossover event. the season will roll out across three phases through december, alongside major gameplay updates, competitive events and new community-focused features.\n⠀\nla stagione 5 parte con assedio a las vegas\nla prima fase della stagione si chiama assedio a las vegas e debutterà il 13 ottobre. il lancio introdurrà imme\"><a href=\"news-UgkxnhcQnMs37VSNzyLG45qciYrpRf-UCrx4.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/MnANh54VsEBDhU11uFWa0kl-Rbslqtzp6H7DgBXrWtMw2rSNIMx4jZHzW2IGYlKBaL1FULoLbGdOUnA=s1600-rw-nd-v1\" alt=\"News: Battlefield 6 Stagione 5 porta la guerra a Las Vegas con tre nuove mappe, Rapid Royale e crossover Dead Space\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxnhcQnMs37VSNzyLG45qciYrpRf-UCrx4.html\">News: Battlefield 6 Stagione 5 porta la guerra a Las Vegas con tre nuove mappe, Rapid Royale e crossover Dead Space</a></h3><div class=\"article-meta\">ZazoomTek · 10 ottobre 2026</div><p>Electronic Arts e Battlefield Studios hanno svelato la Stagione 5 di Battlefield 6 e Battlefield REDSEC, descritta come la stagione più grande realizzata finora. Il nuovo ciclo di contenuti prenderà il via il 13 ottobre 2026 e…</p><a class=\"read-more\" href=\"news-UgkxnhcQnMs37VSNzyLG45qciYrpRf-UCrx4.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"5\" data-search=\"news: tower tactics ii entra in accesso anticipato su steam con oltre 190 carte e 150 gingilli news news: tower tactics ii entra in accesso anticipato su steam con oltre 190 carte e 150 gingilli\ntower tactics ii è ora disponibile in accesso anticipato su steam. sviluppato da asraworks e pubblicato da assemble entertainment, il sequel amplia la formula dell’originale combinando tower defense, roguelike e deckbuilding in un sistema costruito attorno a run sempre diverse, ondate nemiche sempre più aggressive e combinazioni di carte da perfezionare partita dopo partita.\n⠀\ntower tactics ii is now available in early access on steam, expanding the original game with deeper deckbuilding, roguelike progression and tower-defense mechanics. players can experiment with more than 190 cards, 150 trinkets, five playable characters and community-created maps through steam workshop.\n⠀\ntower defense e costruzione del mazzo diventano un’unica strategia\nil cuore di tower tactics ii resta la fusione tra difesa della torre e costruzione del mazzo. le carte raccolte durante la partita possono essere utilizzate per costruire e potenziare le difese, attaccare direttamente i nemici, modificare il campo di b\"><a href=\"news-Ugkxfsd8trxein5rQ0XB_q12VqIFPAZ9mgzR.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/1vAiDd2TyG8GayD_1-kypvroTdmpSLS6jnQ7B67NDOCZdTksQvPSxXaAt1U5d7C4ThmvXc3nbqE4Mw=s1600-rw-nd-v1\" alt=\"News: Tower Tactics II entra in Accesso Anticipato su Steam con oltre 190 carte e 150 gingilli\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-Ugkxfsd8trxein5rQ0XB_q12VqIFPAZ9mgzR.html\">News: Tower Tactics II entra in Accesso Anticipato su Steam con oltre 190 carte e 150 gingilli</a></h3><div class=\"article-meta\">ZazoomTek · 10 ottobre 2026</div><p>Tower Tactics II è ora disponibile in Accesso Anticipato su Steam. Sviluppato da asraworks e pubblicato da Assemble Entertainment, il sequel amplia la formula dell’originale combinando tower defense, roguelike e deckbuilding in…</p><a class=\"read-more\" href=\"news-Ugkxfsd8trxein5rQ0XB_q12VqIFPAZ9mgzR.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"6\" data-search=\"news: the talos principle 3 mostra il primo gameplay: l&#x27;anomalia e nuovi enigmi nel capitolo finale della trilogia news news: the talos principle 3 mostra il primo gameplay: l&#x27;anomalia e nuovi enigmi nel capitolo finale della trilogia\n\ncroteam e devolver digital hanno presentato il primo video gameplay di the talos principle 3, il nuovo capitolo della celebre serie di puzzle game filosofici. il filmato, mostrato durante il triple-i initiative, anticipa un&#x27;avventura più ambiziosa, ambientata in decine di mondi differenti e destinata a concludere la trilogia attraverso nuovi enigmi, misteri e interrogativi sulla natura dell&#x27;esistenza.\n\n⠀\nthe talos principle 3 has received its first gameplay reveal, showcasing mysterious environments, challenging puzzles and an ambitious story spanning multiple generations. developed by croteam and published by devolver digital, the final chapter of the philosophical puzzle trilogy is scheduled to launch in 2027 on pc and playstation 5.\n\n⠀\nil ritorno di the talos principle tra filosofia e fantascienza\n\ncon the talos principle 3, croteam si prepara a concludere un percorso narrativo che ha reso la serie particolarmente riconoscibile nel panorama dei vi\"><a href=\"news-UgkxMfJRp-TjYXmdrt2qXU5RVA1pbFYf1H16.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/ahl8LogGQOGEgxY-BQrojHMfWHiMH7uV9uAbfUwXHrTw3dRywRKUFpzneYc6RDhdS48IHI70buVi4g=s1600-rw-nd-v1\" alt=\"News: The Talos Principle 3 mostra il primo gameplay: l&#x27;Anomalia e nuovi enigmi nel capitolo finale della trilogia\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxMfJRp-TjYXmdrt2qXU5RVA1pbFYf1H16.html\">News: The Talos Principle 3 mostra il primo gameplay: l&#x27;Anomalia e nuovi enigmi nel capitolo finale della trilogia</a></h3><div class=\"article-meta\">ZazoomTek · 10 ottobre 2026</div><p>Croteam e Devolver Digital hanno presentato il primo video gameplay di The Talos Principle 3, il nuovo capitolo della celebre serie di puzzle game filosofici. Il filmato, mostrato durante il Triple-I Initiative, anticipa…</p><a class=\"read-more\" href=\"news-UgkxMfJRp-TjYXmdrt2qXU5RVA1pbFYf1H16.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"7\" data-search=\"news: ace combat 8: wings of theve supera 1 milione di copie e firma il record di vendite più veloce della serie news news: ace combat 8: wings of theve supera 1 milione di copie e firma il record di vendite più veloce della serie\n⠀\nuno dei capitoli più apprezzati dalla critica\nace combat 8 non ha stabilito soltanto un record commerciale. secondo i principali aggregatori di recensioni, il nuovo episodio è anche il secondo titolo più apprezzato della serie dalla critica, dietro soltanto ad ace combat 4: shattered skies, pubblicato nel 2001 su playstation 2.\nil risultato rafforza la posizione del nuovo capitolo all’interno della saga, soprattutto considerando il peso storico di alcuni episodi precedenti e le aspettative accumulate durante i sette anni trascorsi dall’ultimo capitolo principale.\n⠀\nuna campagna narrativa più cinematografica\nuno degli elementi maggiormente apprezzati è la modalità campagna, che mette il giocatore nei panni di un asso dell’aviazione all’interno di un mondo immaginario sconvolto dalla guerra.\nla struttura resta fedele all’identità arcade della serie, ma viene accompagnata da una messa in scena più spettacolare, vaste aree di combattimento, nuvole più reali\"><a href=\"news-UgkxSAfW_T-tL6dS7sn7syzWrfKVS2hxnK5L.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/soZXps2f6_LkVELLnTcZjTelGeQafWPOg6YFZ_d-WGhmn4NY80bQR-itQ__Y-PahHkh7VNSnlIPLew=s1600-rw-nd-v1\" alt=\"News: ACE COMBAT 8: WINGS OF THEVE supera 1 milione di copie e firma il record di vendite più veloce della serie\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxSAfW_T-tL6dS7sn7syzWrfKVS2hxnK5L.html\">News: ACE COMBAT 8: WINGS OF THEVE supera 1 milione di copie e firma il record di vendite più veloce della serie</a></h3><div class=\"article-meta\">ZazoomTek · 10 ottobre 2026</div><p>Uno dei capitoli più apprezzati dalla critica ACE COMBAT 8 non ha stabilito soltanto un record commerciale. Secondo i principali aggregatori di recensioni, il nuovo episodio è anche il secondo titolo più apprezzato della serie…</p><a class=\"read-more\" href=\"news-UgkxSAfW_T-tL6dS7sn7syzWrfKVS2hxnK5L.html\">Leggi tutto ›</a></div></article>\n<article class=\"article-row ztp-news-item ztp-gaming-extra\" data-archive-index=\"8\" data-search=\"news: dragon’s dogma 2: dark arisen è disponibile con nuova regione, modalità difficile e aggiornamento 4.0 news news: dragon’s dogma 2: dark arisen è disponibile con nuova regione, modalità difficile e aggiornamento 4.0\ncapcom ha pubblicato dragon’s dogma 2: dark arisen, nuova espansione che amplia in modo significativo l’action rpg con una regione completamente inedita, nuove storie, dungeon, equipaggiamenti e ulteriori possibilità di personalizzazione. il lancio coincide inoltre con l’aggiornamento 4.0, che introduce la modalità difficile e importanti miglioramenti tecnici su playstation 5 pro e pc.\n⠀\ndragon’s dogma 2: dark arisen is now available on playstation 5, xbox series x|s, nintendo switch 2 and pc. the expansion introduces the new region of norgan, additional dungeon challenges, new weapons and abilities, while update 4.0 adds hard mode and major technical improvements.\n⠀\nnorgan apre un nuovo capitolo per gli arisen\ndark arisen conduce i giocatori nella regione settentrionale di norgan, un territorio da tempo abbandonato che rappresenta una zona completamente nuova da esplorare. qui gli arisen dovranno collaborare con gli enigmatici eir per scoprire i segreti legati all\"><a href=\"news-UgkxT_ejrIVnCp0dN2Na_0JgBwXQS7nqESBD.html\"><img class=\"article-image\" src=\"https://yt3.ggpht.com/EGII2lGpaVxnbIYbC4VIjEaNuwpMArt8dbbN_Zs5-7scMUkIaXYsRyEOSnNHT6VOmj34To8C5uhs=s1600-rw-nd-v1\" alt=\"News: Dragon’s Dogma 2: Dark Arisen è disponibile con nuova regione, modalità Difficile e aggiornamento 4.0\" loading=\"lazy\"></a><div class=\"article-copy\"><span class=\"ztp-gaming-kind\">DAL GAMING</span><h3><a href=\"news-UgkxT_ejrIVnCp0dN2Na_0JgBwXQS7nqESBD.html\">News: Dragon’s Dogma 2: Dark Arisen è disponibile con nuova regione, modalità Difficile e aggiornamento 4.0</a></h3><div class=\"article-meta\">ZazoomTek · 10 ottobre 2026</div><p>Capcom ha pubblicato Dragon’s Dogma 2: Dark Arisen, nuova espansione che amplia in modo significativo l’action RPG con una regione completamente inedita, nuove storie, dungeon, equipaggiamenti e ulteriori possibilità di…</p><a class=\"read-more\" href=\"news-UgkxT_ejrIVnCp0dN2Na_0JgBwXQS7nqESBD.html\">Leggi tutto ›</a></div></article>\n</div></div></section>\n</div>\n<div class=\"ztp-videos-anchor\" id=\"ztpVideosAnchor\" aria-label=\"Esplora Ultimi Video del canale ZazoomTek\"></div>\n<div class=\"ztp-news-pagination-internal\" id=\"ztpNewsPager\"></div>\n</div>\n<aside class=\"ztp-news-rail\" id=\"ztpNewsRail\" aria-label=\"Box editoriali, articoli più letti, Tech Impact e Gaming Inside\"></aside>\n</div>\n\n</section>";
  const wrapper=document.createElement("div");
  wrapper.innerHTML=fragmentHTML;
  const area=wrapper.querySelector(".ztp-news-area");
  if(!area) return;
  // The approved Home has no preview caption, layout percentages or debug counter.
  const redundantPreviewHeading=area.querySelector(".ztp-split-heading");
  if(redundantPreviewHeading)redundantPreviewHeading.remove();
  // Defense in depth if older templates still ship a preview-only side header.
  const editorialPreviewBar=area.querySelector(".ztp-editorial-heading");
  if(editorialPreviewBar)editorialPreviewBar.remove();
  const tech=area.querySelector(".ztp-news-tech .ztp-news-items");
  const gaming=area.querySelector(".ztp-news-gaming .ztp-news-items");
  const rail=area.querySelector(".ztp-news-rail");
  if(!tech||!gaming||!rail)return;
  // Build directly from the fifteen canonical, auto-updated Community news.
  // Nothing is retyped or guessed; same image, excerpt, title and actual link.
  const gamingTerms=/\b(be comics|be games|cosplay|street fighter|sonic racing|crossworlds|chivalware|ea sports fc|fc 27|tekken|game ground|castlevania|videogiochi|videogioch|gaming|gameplay|playstation|xbox|nintendo|ps5|ps4|steam|dragon.s dogma|battlefield|monster hunter|assassin.s creed|gta|gran turismo|wolverine|tomb raider)\b/i;
  let techCount=0,gamingCount=0;
  for(const row of rows){
   const title=row.querySelector('h3 a')?.textContent||"";
   const isGaming=gamingTerms.test(title);
   row.classList.add("ztp-news-item");
   if(isGaming){
    const i=gamingCount++;
    if(i===0||i===3)row.classList.add("ztp-gaming-feature");
    else row.classList.remove("ztp-gaming-feature");
    const copy=row.querySelector(".article-copy");
    if(copy&&!copy.querySelector(".ztp-gaming-kind")){
      const label=document.createElement("span");
      label.className="ztp-gaming-kind";
      label.textContent=/sport|fc 27|racing/i.test(title)?"SPORT & CORSE":
        /tekken|street fighter/i.test(title)?"PICCHIADURO":
        /indie|chivalware/i.test(title)?"INDIE & NOVITÀ":"GAMING";
      copy.prepend(label);
    }
    gaming.appendChild(row);
   }else{techCount++;tech.appendChild(row);}
  }
  const previewCounter=area.querySelector('.ztp-count');
  if(previewCounter)previewCounter.textContent=rows.length+' news · Tech e Gaming';
  area.querySelector(".ztp-news-tech .ztp-news-head small").textContent=techCount+" news";
  area.querySelector(".ztp-news-gaming .ztp-news-head small").textContent=gamingCount+" news";
  // Hide only the canonical shell, not its imported content (now moved).
  original.id="ztCanonicalNews";
  original.style.display="none";
  const originalList=original.querySelector("#articleList");
  if(originalList)originalList.id="ztCanonicalArticleList";
  area.id="articoli";
  original.insertAdjacentElement("afterend",area);
  // Move live pagination: still updated by scripts and fully clickable.
  const pagination=original.querySelector("nav.pagination");
  if(pagination)area.querySelector("#ztpNewsPager").appendChild(pagination);
  layout.classList.add("ztp-three-home");
  const top=document.createElement("div");top.className="ztp-top";
  const topMain=document.createElement("div");topMain.className="ztp-top-main";
  const video=document.createElement("section");
  video.className="ztp-review-videos ztp-top-videos";
  video.setAttribute("aria-label","Ultime video recensioni ZazoomTek");
  video.innerHTML='<h2>ULTIME VIDEO RECENSIONI</h2><div class="ztp-review-list" id="ztpReviewVideoList"></div><div class="ztp-review-footer"><a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener noreferrer">TUTTE LE VIDEO RECENSIONI →</a></div>';
  topMain.append(latest,guide);top.append(topMain,video);main.insertBefore(top,area);
  const list=video.querySelector("#ztpReviewVideoList");
  // Selected dynamically from the actual authenticated channel JSON.
  const fallbackReviewIDs=["WwGAaKGfoGY","tb1CAHc1QoM","6Zz4E1FhAY4"];
  function renderReviews(items){
   if(!Array.isArray(items)||items.length<3)return;
   const chosen=items.filter(x=>x&&/^[A-Za-z0-9_-]{11}$/.test(String(x.id||""))).slice(0,3);
   if(chosen.length!==3)return;
   list.replaceChildren();
   for(const item of chosen){
    const id=String(item.id);
    const card=document.createElement("article");card.className="ztp-review-card";
    const link=document.createElement("a");
    link.href="https://www.youtube.com/watch?v="+encodeURIComponent(id);link.target="_blank";link.rel="noopener noreferrer";
    const imageBox=document.createElement("span");imageBox.className="ztp-review-thumb";
    const image=document.createElement("img");image.src="https://i.ytimg.com/vi/"+id+"/hqdefault.jpg";image.alt=item.title||"Recensione ZazoomTek";image.loading="lazy";
    const play=document.createElement("span");play.className="ztp-review-play";play.textContent="▶";play.setAttribute("aria-hidden","true");
    imageBox.append(image,play);
    const copy=document.createElement("span");copy.className="ztp-review-copy";
    const name=document.createElement("strong");name.textContent=item.title||"Recensione";
    const date=document.createElement("small");
    try{date.textContent=new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"long",year:"numeric",timeZone:"Europe/Rome"}).format(new Date(item.publishedAt));}catch(_){date.textContent="ZazoomTek";}
    copy.append(name,date);link.append(imageBox,copy);card.append(link);list.appendChild(card);
   }
  }
  const originalStack=side.querySelector(".zt-video-stack");
  const pop=side.querySelector("#zt-popular-box");
  const impact=side.querySelector('.zt-special-box[data-special-section="tech"]');
  const inside=side.querySelector('.zt-special-box[data-special-section="gaming"]');
  if(pop)rail.appendChild(pop);
  if(impact)rail.appendChild(impact);
  if(inside)rail.appendChild(inside);
  if(originalStack)originalStack.remove();
  while(side.firstElementChild)rail.appendChild(side.firstElementChild);
  side.remove();
  const videoShelfTarget=area.querySelector("#ztpVideosAnchor");
  const root=document.querySelector("main.page");
  function mountShelves(){
   const shelves=document.getElementById("zt-home-shelves");
   if(!shelves||!videoShelfTarget)return false;
   if(shelves.parentElement!==videoShelfTarget)videoShelfTarget.appendChild(shelves);
   const sync=()=>{
     const full=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&!el.querySelector(".zt-shelf-shorts"));
     if(full){const h=full.querySelector(".zt-shelf-head h2");if(h&&h.textContent!=="ESPLORA ULTIMI VIDEO")h.textContent="ESPLORA ULTIMI VIDEO";}
     const shorts=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&el.querySelector(".zt-shelf-shorts"));
     if(!shorts)return;
     shorts.classList.add("ztp-rail-shorts");
     const heading=shorts.querySelector(".zt-shelf-head h2");
     if(heading)heading.textContent="ULTIMI SHORTS";
     const prev=rail.querySelector(".ztp-rail-shorts");
     if(prev&&prev!==shorts)prev.replaceWith(shorts);
     else if(!prev){if(inside)inside.insertAdjacentElement("afterend",shorts);else rail.appendChild(shorts);}
     if(inside&&shorts.previousElementSibling!==inside)inside.insertAdjacentElement("afterend",shorts);
     requestAnimationFrame(reconcileRight);
   };
   sync();
   requestAnimationFrame(reconcileRight);
   if(!shelves.dataset.ztpShortsObserved){
     shelves.dataset.ztpShortsObserved="yes";
     new MutationObserver(sync).observe(shelves,{childList:true});
   }
   return true;
  }
  if(!mountShelves()&&root){
   const obs=new MutationObserver(()=>{if(mountShelves())obs.disconnect();});
   obs.observe(root,{childList:true});
  }
  // Only distinct real archive articles may expand Gaming. A static hidden
  // cache is never shown twice, and card balancing avoids creating new gaps.
  function balance(){
   const columnTech=area.querySelector(".ztp-news-tech");
   const columnGaming=area.querySelector(".ztp-news-gaming");
   if(!columnTech||!columnGaming)return;
   const extras=[...area.querySelectorAll(".ztp-gaming-extra")];
   extras.forEach(card=>card.classList.remove("ztp-extra-visible"));
   if(window.innerWidth<=820)return;
   const existing=new Set([...rows].map(r=>r.querySelector("h3 a")?.getAttribute("href")));
   const seen=new Set(existing);
   const target=columnTech.getBoundingClientRect().height-120;
   for(const card of extras){
     const link=card.querySelector("h3 a")?.getAttribute("href");
     if(!link||seen.has(link))continue;
     seen.add(link);
     const before=columnGaming.getBoundingClientRect().height;
     if(before>=target)break;
     card.classList.add("ztp-extra-visible");
     const after=columnGaming.getBoundingClientRect().height;
     if(Math.abs(after-columnTech.getBoundingClientRect().height)>Math.abs(before-columnTech.getBoundingClientRect().height)){
       card.classList.remove("ztp-extra-visible");break;
     }
   }
  }

  // Fill remaining vertical space with published articles, never blank padding.
  // Entries come from real, distinct archived news URLs on ZazoomTek.
  const sidebarEditorials=[{"title":"News: Nilox amplia gli Smart Eyewear con Lapaz e After Collection tra sport, lifestyle e controllo vocale","url":"/news-UgkxpNjlKte75njZ2upYxawcYu9oj6qranj2.html","image":"https://yt3.ggpht.com/6vzAIrIqM1ApPgE8fvw4D7Fi0e7L_BorqUm32-qwe77wNuwD6FTV48F8QwySB0x7ZJQAvU40noVQNA=s1600-rw-nd-v1"},{"title":"News: NVIDIA protagonista alla finale dell’Italian Hackathon League con DGX Spark e i talenti dell’AI","url":"/news-UgkxVx1yJ8C2gvc88TneX7746ZQ0UoNp0NEi.html","image":"https://yt3.ggpht.com/9FRlJEWGi_Ss_pNt5ErSXTgKUzZ6x2PMYLIJg4zlLdIsxufuePBUH5MLbbYpyhdos48YhYtk7c9d=s1600-rw-nd-v1"},{"title":"News: Vaultbreakers, demo gratuita su Steam e ritorno di Square Enix Collective","url":"/news-UgkxDax8FZb_susV2FQG_lKIddMe1ipqo7ET.html","image":"https://yt3.ggpht.com/b8ZiY8LF4wsvASBT8DYBSG7BYze1r8KDvSHQn4D8-xBsUeseKnZVFrAxLH0NpRSfU3JzpXsLeef9=s1600-rw-nd-v1"},{"title":"News: CORSAIR HS80 v2 MAX WIRELESS punta al gaming competitivo con nuovi driver e fino a 130 ore di autonomia","url":"/news-UgkxUq-6ZzV_TpBbXosV6TqjxCeXjAweSh_f.html","image":"https://yt3.ggpht.com/ArbM4BX2xFi4ZsqJM7XLsND3HLKtAyeEtu2zDa9nsJCYPXV0ymGw5DBbTpHU6dJgNLPf5cxDeUTrpw=s1600-rw-nd-v1"},{"title":"News: Sony ECM-AX10 porta l’audio spaziale professionale sugli smartphone","url":"/news-UgkxSLVy8d-ZS0VYmC3f4aXFW7LCaKQ2q5AO.html","image":"https://yt3.ggpht.com/m3w7-1MuuEWjopola9rPaKwr2bZvqbgtSbWz-Vqd78y0Az_uXemE6R82tefaQsgGDV8yp5ae6mv-csg=s1600-rw-nd-v1"},{"title":"News: Mafia III compie 10 anni e torna su PS5 e Xbox Series X|S a 60 FPS","url":"/news-Ugkxf6xEfOtGRND0MR4yD5bssD8t7TnNbJts.html","image":"https://yt3.ggpht.com/j_HGJQBU_w00Pa86pgXpKr7_9zMgwyQJioJExL31rYjruB-wfYEPN2gfsXjASLh8TmStfDelZYEkaf4=s1600-rw-nd-v1"}];
  const editorialBox=document.createElement("section");
  editorialBox.className="ztp-editorial-archive";
  const editorialHead=document.createElement("h2");editorialHead.textContent="DALLA REDAZIONE";
  editorialBox.append(editorialHead);
  const editorialCards=[];
  for(const item of sidebarEditorials){
    const article=document.createElement("a");article.className="ztp-editorial-story";
    article.href=item.url;article.hidden=true;
    const pic=document.createElement("img");pic.src=item.image;pic.alt=item.title;pic.loading="lazy";
    const title=document.createElement("strong");title.textContent=item.title;
    article.append(pic,title);editorialBox.append(article);editorialCards.push(article);
  }
  const ytFollow=rail.querySelector(".zt-youtube-follow");
  if(ytFollow)ytFollow.insertAdjacentElement("afterend",editorialBox);
  else rail.appendChild(editorialBox);
  function reconcileRight(){
    if(!document.documentElement.classList.contains("ztp-home-live-ready"))return;
    editorialCards.forEach(card=>card.hidden=true);
    editorialBox.style.display="none";
    if(window.innerWidth<=1380)return;
    const primary=area.querySelector(".ztp-primary-feed");
    if(!primary)return;
    if(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom<90)return;
    const alreadyLinked=new Set([...area.querySelectorAll(".ztp-news-item h3 a")].map(a=>a.getAttribute("href")));
    editorialBox.style.display="block";
    for(const card of editorialCards){
      if(alreadyLinked.has(card.getAttribute("href")))continue;
      const before=Math.abs(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom);
      card.hidden=false;
      const after=Math.abs(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom);
      if(after>=before){card.hidden=true;break;}
    }
    if(!editorialCards.some(card=>!card.hidden))editorialBox.style.display="none";
  }

  balance();
  window.addEventListener("load",()=>{balance();requestAnimationFrame(reconcileRight)},{once:true});
  window.addEventListener("resize",()=>requestAnimationFrame(()=>{balance();reconcileRight()}),{passive:true});
  // Channel JSON is authoritative and refreshes all three video review cards.
  fetch("/home-video-feed.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("video catalog unavailable");return r.json();
  }).then(items=>{
    const v=items.filter(x=>x&&x.category==="recensioni"&&!x.short&&!x.live)
       .sort((a,b)=>String(b.publishedAt||"").localeCompare(String(a.publishedAt||""))).slice(0,3);
    renderReviews(v);
  }).catch(()=>{});
  document.documentElement.classList.add("ztp-home-live-ready");
  requestAnimationFrame(reconcileRight);
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup,{once:true});
 else setup();
})();
