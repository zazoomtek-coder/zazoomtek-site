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
 assert "Primo testo. Secondo testo." in sectioned_body({"category":"news-tech","body":["## Titolo vero","Primo testo.","Secondo testo."]})
 assert "Approfondimento" not in sectioned_body({"category":"news-tech","body":["Primo testo.","Secondo testo."]})
 print("Article paragraph typography tests OK",flush=True)
if __name__=="__main__":verify()
