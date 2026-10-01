# Manipulacija 3D objektom pokretima ruku

Projekat za predmet Praksa. Ucitava se 3D model i okrece se nagibom saka
ispred obicne web kamere:

- **desna saka** nagnuta levo ili desno okrece objekat oko **uspravne ose**
  (objekat se vrti u mestu, kao na gramofonskoj ploci);
- **leva saka** nagnuta levo ili desno **preklapa** objekat napred i nazad
  (rotacija oko vodoravne ose);
- **saka uspravno, dlanom ka kameri, objekat miruje.**

## Kljucna zamisao: nagib zadaje brzinu, ne ugao

Posto saka moze da se nagne najvise osamdesetak stepeni, a objekat treba da se
okrene za proizvoljan ugao, nagib ne zadaje polozaj objekta nego **brzinu
njegovog okretanja**. Nagni i drzi - objekat se okrece; vrati saku uspravno -
objekat stane u zatecenom polozaju. Isti princip koji ima dzojstik.

Preslikavanje nagiba u brzinu (`core/control.py`) ima tri dela, svaki resava
jedan konkretan problem:

| Deo | Vrednost | Problem koji resava |
|---|---|---|
| mrtva zona | 12° | saka nikad nije savrseno uspravna, pa bi objekat stalno plutao |
| zasicenje | 70° | nagli pokret ne sme da zavrti objekat nekontrolisano |
| kriva odziva | stepen 1.6 | mali nagibi daju fino dotericanje, veliki brzo razgledanje |

Brzina se mnozi proteklim vremenom (`dt`), pa je okretanje isto na racunaru sa
30 i sa 120 slika u sekundi.

## Struktura

```
gest3d/
├── main.py                 ulazna tacka
├── config.py               sve podesive vrednosti
├── core/
│   ├── events.py           AxisInput, Snapshot, Command
│   ├── control.py          nagib -> brzina rotacije, nagomilavanje ugla
│   ├── model.py            ucitavanje OBJ/STL, normalizacija, normale
│   ├── filters.py          One Euro, histereza, zadrzavanje
│   └── input_source.py     apstraktni izvor ulaza
├── sources/
│   └── camera_source.py    ruke -> brzine rotacije
├── tracking/
│   └── hand_tracker.py     detekcija ruku u posebnoj niti
└── ui/
    ├── renderer.py         OpenGL: projekcija, osvetljenje, pokazivaci
    └── app.py              prozor, petlja, komande
```

Obrada ulaza ide u cetiri koraka, svaki resava jedan problem: glacanje sirovog
ugla (podrhtava i kad saka miruje), pretvaranje nagiba u brzinu, glacanje same
brzine (uklanja trzaje), i citanje stiska sake za pauzu i komande.

## Pokretanje (Windows)

```
setup.bat                      jednom, pravi .venv i instalira zavisnosti
python main.py                 pokretanje
python main.py --camera 1      ako racunar ima vise kamera
python main.py --no-preview    bez prikaza kamere u uglu
```

Potreban je Python 3.10 ili 3.11, 64-bit. Novije verzije nemaju gotove pakete
za MediaPipe i NumPy ispod verzije 2.

## Model

Pri pokretanju se prikazuje ugradjeni torus, koji se pravi u kodu, pa aplikacija
radi i bez ijednog fajla. Torus je biran namerno: nije simetrican po svim osama,
pa se po njemu odmah vidi i smer i kolicina rotacije, za razliku od kocke ili
lopte.

Taster `o` otvara dijalog za ucitavanje drugog modela. Formati `.obj` i `.stl`
rade bez dodatnih biblioteka; za `.ply`, `.glb` i `.gltf` dovoljno je
`pip install trimesh`.

Svaki model se po ucitavanju centrira i skalira na jedinicnu velicinu, jer
modeli dolaze u raznim jedinicama (milimetri, metri, inci) pa bi se jedan video
kao tacka a drugi bi prekrio ceo ekran.

## Upravljanje

| Radnja | Pokret |
|---|---|
| okretanje oko uspravne ose | nagib desne sake levo ili desno |
| preklapanje napred i nazad | nagib leve sake levo ili desno |
| pauza te ose | stisnuta saka |
| pocetni polozaj | desna saka stisnuta i zadrzana |
| zicani prikaz | leva saka stisnuta i zadrzana |

Tasteri: `r` pocetni polozaj, `o` ucitaj model, `f` zicani prikaz, `x` ose,
`g` mreza, `p` automatsko okretanje, `space` zamrzni ulaz, `s` snimi sliku,
`h` pomoc, `Esc` izlaz.

Pri dnu prozora su dve skale koje pokazuju nagib svake sake. Osencen deo u
sredini je mrtva zona: dok je igla u njoj, objekat miruje. To je najbrzi nacin
da se vidi zasto se objekat ne okrece.

## Podesavanje

Sve je u `config.py`. Najcesce se menjaju:

| Parametar | Podrazumevano | Kada |
|---|---|---|
| `DEAD_ZONE` | 12.0 | objekat pluta kad saka miruje -> povecati |
| `MAX_RATE` | 120.0 | okretanje presporo ili prebrzo |
| `RATE_CURVE` | 1.6 | vece vrednosti daju finije dotericanje |
| `INVERT_YAW`, `INVERT_PITCH` | False | objekat se okrece na suprotnu stranu |
| `SWAP_HANDS` | False | leva i desna ruka zamenjene |
| `CAMERA_ELEV` | 22.0 | ugao posmatranja |
| `START_YAW`, `START_PITCH` | -25, 20 | pocetni polozaj, tu vraca taster `r` |

## Ogranicenja

- Koriste se samo dve ose. Treca (uvrtanje oko ose pogleda) mogla bi da se
  dobije iz razlike uglova dve sake.
- Nema zumiranja ni pomeranja objekta; rastojanje izmedju dve sake je prirodan
  kandidat za zum.
- Osvetljenje je prosto, bez senki; teziste je na upravljanju, a ne na prikazu.
- Sistem prati najvise dve ruke i pretpostavlja da pripadaju istoj osobi.