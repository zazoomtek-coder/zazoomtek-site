#!/usr/bin/env python3
"""One-time read-only verification of the deployed SpotNews homepage."""
import urllib.request
from urllib.error import HTTPError,URLError

url="https://zazoomtek.it/"
req=urllib.request.Request(url,headers={
 "User-Agent":"Mozilla/5.0 (compatible; ZazoomTekSiteCheck/1.0)",
 "Cache-Control":"no-cache",
 "Accept":"text/html,application/xhtml+xml"
})
try:
 with urllib.request.urlopen(req,timeout=25) as response:
  html=response.read(2_500_000).decode("utf-8","replace")
  status=response.status
  final_url=response.url
except (HTTPError,URLError,TimeoutError) as error:
 print("PRODUCTION DOMAIN NOT VERIFIED:",type(error).__name__,str(error)[:180])
 raise SystemExit(1)
print("OFFICIAL URL:",final_url,"HTTP:",status,"HTML bytes:",len(html))
checks={
 "SpotNews stylesheet": "spotnews.css" in html,
 "2026-10-28 news headline": any(s in html for s in (
   "DJI Power Auro 2000", "The Sims 4", "vivo X500 Series",
   "Sony WH-1000XM6", "Cisco Talos", "ArcheAge Chronicles"
 )),
 "ZazoomTek identity":"Zazoom" in html and "Tek" in html,
}
for k,v in checks.items():print(k, "YES" if v else "NO")
if not all(checks.values()):
 raise SystemExit("Official domain does not yet show verified new SpotNews data")
print("CONFIRMED: official site is reachable and renders new SpotNews with 28 October content.")
