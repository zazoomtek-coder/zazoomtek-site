"""Standard-library checks for the ZazoomTek article typography parser."""
from article_templates import rich_text,compact_prose_html,news_body,sectioned_body,paragraphs

def verify():
 # Soft source line breaks are not editorial paragraph boundaries.
 assert rich_text("Riga prima\nriga seconda")=="Riga prima riga seconda"
 assert "<br>" in rich_text("• primo punto\n• secondo punto")
 a=compact_prose_html(["<p>Frase iniziale.</p>","<p>Testo collegato.</p>",
                       "<h2>Hardware e Prestazioni</h2>",
                       "<p>Paragrafo successivo.</p>","<p>Altra frase.</p>"])
 assert a=="<p>Frase iniziale. Testo collegato.</p><h2>Hardware e Prestazioni</h2><p>Paragrafo successivo. Altra frase.</p>"
 assert compact_prose_html(["<p>Introduzione.</p>","<p>Vi interessa?</p>"])=="<p>Introduzione.</p><p>Vi interessa?</p>"
 assert "<h2>" in sectioned_body({"category":"news-tech","body":["## Titolo vero","Primo testo.","Secondo testo."]})
 assert "<p>Primo testo.</p><p>Secondo testo.</p>" in sectioned_body({"category":"news-tech","body":["## Titolo vero","Primo testo.","Secondo testo."]})
 assert "Approfondimento" not in sectioned_body({"category":"news-tech","body":["Primo testo.","Secondo testo."]})

 # Imported news with no authored headings must get thematic subdivisions.
 unstructured=sectioned_body({"category":"news-gaming","body":[
  "Novità ufficiale del gioco.", "Il gameplay permette ai giocatori nuove missioni.",
  "Dettagli aggiuntivi.", "La nuova espansione aggiunge una modalità."
 ]})
 assert unstructured.count("<h2>")==1
 assert "<h2>Tutti i dettagli</h2>" in unstructured
 assert all(unstructured.count(v)==1 for v in (
  "Novità ufficiale del gioco.","Il gameplay permette ai giocatori nuove missioni.",
  "Dettagli aggiuntivi.","La nuova espansione aggiunge una modalità."
 ))
 assert "<p>Dettagli aggiuntivi.</p>" in unstructured
 # One-paragraph notices still have a visible H2.
 brief=sectioned_body({"category":"news-tech","body":["Avviso di pubblicazione."]})
 assert brief.count("<h2>")==1 and "<p>Avviso di pubblicazione.</p>" in brief
 # Explicit source headings must not trigger any synthetic headings.
 full=sectioned_body({"category":"news-tech","headings":[{"before_paragraph":1,"title":"Dettagli ufficiali"}],
                     "body":["La notizia.", "La descrizione originale continua qui."]})
 assert full.count("<h2>")==1 and "<h2>Dettagli ufficiali</h2>" in full
 # A single source subtitle must not suppress later red-bar sections.
 mixed=sectioned_body({"category":"news-tech","body":[
  "Primo paragrafo introduttivo.",
  "Secondo paragrafo di contesto.",
  "## Dettagli ufficiali",
  "Primo paragrafo della sezione ufficiale.",
  "Secondo paragrafo che mantiene i dati.",
  "Terzo paragrafo dopo il titolo di origine.",
  "Quarto paragrafo senza titolo scritto dall'autore."
 ]})
 assert "<h2>Dettagli ufficiali</h2>" in mixed and mixed.count("<h2>")>=2
 assert mixed.index("Primo paragrafo introduttivo.") < mixed.index("Dettagli ufficiali")
 # Isolated Markdown headings embedded inside a text block become real H2s.
 merged=paragraphs({"body":["Introduzione di un testo.\n**Nuove caratteristiche**\nDescrizione della novità."]})
 assert len(merged)==3 and merged[1]=="**Nuove caratteristiche**"
 marked=sectioned_body({"category":"news-tech","body":[
  "Introduzione di un testo.\n**Nuove caratteristiche**\nDescrizione della novità."
 ]})
 assert "<h2>Nuove caratteristiche</h2>" in marked
 assert "<p>Introduzione di un testo.</p>" in marked
 assert "<p>Descrizione della novità.</p>" in marked
 # A complete unstructured article never loses or reorders source paragraphs.
 sample=[f"Paragrafo editoriale numero {i}, con informazioni confermate e testo originale." for i in range(1,9)]
 formatted=sectioned_body({"category":"extra","body":sample})
 assert formatted.count("<h2>")>=3
 assert all(formatted.count("<p>"+p+"</p>")==1 for p in sample)
 assert [formatted.index(p) for p in sample]==sorted(formatted.index(p) for p in sample)

 # Regression for the long, run-on Expeditions: Samurai-style Community post.
 # It must become several short paragraphs and multiple red-bar headings,
 # without losing/rewording any single original sentence.
 import re
 from html import unescape
 original=(
  "Expeditions: Samurai continua a espandere il proprio mondo. "
  "Il diario degli sviluppatori presenta il villaggio personale dell'Atto 3. "
  "La fase finale dell'avventura porterà un sistema di gestione diverso. "
  "I giocatori potranno costruire il villaggio e sviluppare la comunità. "
  "I dettagli del progetto descrivono la progressione del protagonista. "
  "L'ambientazione riprende il periodo Sengoku e le sue trasformazioni. "
 )*7
 output=sectioned_body({"category":"news-gaming","body":[original]})
 parts=re.findall(r"<p>(.*?)</p>",output,flags=re.S)
 assert len(parts)>=5, "Long YouTube text must be divided into readable paragraphs"
 assert output.count("<h2>")>=2, "Long news needs multiple editorial subsections"
 assert all(len(unescape(re.sub(r"<[^>]+>","",p)))<=430 for p in parts)
 joined=" ".join(unescape(re.sub(r"<[^>]+>","",p)) for p in parts)
 assert re.sub(r"\s+"," ",joined).strip()==re.sub(r"\s+"," ",original).strip()
 # Regression: real YouTube Tech reviews embed the H2 title and prose
 # in the same Community paragraph. Preserve all five canonical sections.
 tech=sectioned_body({"category":"recensioni-tech","body":[
  "Introduzione originale del microfono.",
  "Materiali e Design\\nCostruzione metallica e base stabile.",
  "Hardware e Prestazioni\\nCapsula cardioide da 16 mm.",
  "Uso Quotidiano\\nCollegamento USB semplice.",
  "Esperienza Complessiva\\nResa vocale convincente.",
  "Conclusioni\\nIl prodotto ha un buon rapporto qualità e praticità.",
  "Voto finale: 9.2/10"
 ]})
 for heading in ("Materiali e Design","Hardware e Prestazioni",
                 "Uso Quotidiano","Esperienza Complessiva","Conclusioni"):
  assert tech.count("<h2>"+heading+"</h2>")==1, ("Missing Tech heading",heading,tech)
 for phrase in ("Introduzione originale del microfono.","Costruzione metallica e base stabile.",
                "Capsula cardioide da 16 mm.","Collegamento USB semplice.",
                "Resa vocale convincente.","Il prodotto ha un buon rapporto qualità e praticità."):
  assert tech.count(phrase)==1, ("Lost Tech source prose",phrase)
 assert "<h2>Gameplay</h2>" not in tech and "<h2>Storia</h2>" not in tech
 print("Article paragraph typography tests OK",flush=True)
if __name__=="__main__":verify()
