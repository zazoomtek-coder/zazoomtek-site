"""Standard-library checks for the ZazoomTek article typography parser."""
from article_templates import rich_text,compact_prose_html,news_body,sectioned_body

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
 assert unstructured.count("<h2>")==2
 assert "<h2>Gameplay e contenuti</h2>" in unstructured
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
 print("Article paragraph typography tests OK",flush=True)
if __name__=="__main__":verify()
