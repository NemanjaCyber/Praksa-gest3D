"""
Centralna konfiguracija. Sve podesive vrednosti su ovde, da bi se sistem
mogao kalibrisati bez diranja logike.
"""

# ============================ KAMERA / DETEKCIJA ==========================
CAMERA_INDEX = 0
CAM_WIDTH = 1280
CAM_HEIGHT = 720
PROC_WIDTH = 640            # sirina na kojoj radi detekcija (manje = brze)
MIN_DET_CONF = 0.6
MIN_TRK_CONF = 0.5
SWAP_HANDS = False          # ako su leva i desna zamenjene

# ===================== PRETVARANJE NAGIBA U ROTACIJU ======================
# Nagib sake zadaje BRZINU okretanja: uspravna saka = objekat miruje.
DEAD_ZONE = 7.0             # ispod ovog nagiba objekat miruje (stepeni)
MAX_ANGLE = 70.0            # nagib preko ovoga ne ubrzava dalje
MAX_RATE = 120.0            # najveca brzina okretanja (stepeni u sekundi)
RATE_CURVE = 1.6            # >1 daje finije dotericanje pri malom nagibu

INVERT_YAW = False          # ako se objekat okrece na suprotnu stranu
INVERT_PITCH = False
CLAMP_PITCH = False         # ograniciti preklapanje na +-89 stepeni
PITCH_LIMIT = 89.0

RATE_SMOOTH = 0.20          # glacanje brzine (0 = bez, 1 = trenutno)

# Glacanje samog ugla sake pre svega ostalog
ANGLE_MIN_CUTOFF = 1.0
ANGLE_BETA = 0.02

# Posle ovoliko sekundi bez ruke u kadru rotacija se zaustavlja. Kratko
# cekanje postoji zato sto detekcija povremeno izgubi ruku na jedan frejm.
HAND_LOST_GRACE = 0.25

# ============================== PRIKAZ ====================================
WIN_W = 1280
WIN_H = 760
FOV = 45.0
CAMERA_DIST = 2.6           # udaljenost posmatraca od objekta
CAMERA_ELEV = 22.0          # koliko je posmatrac iznad objekta (stepeni)

# Pocetni polozaj modela. Blagi nagib je namerno, da se po ucitavanju odmah
# vidi da je objekat prostoran, a ne ravna silueta. Taster "r" vraca ovde.
START_YAW = -25.0
START_PITCH = 20.0
BG_COLOR = (0.06, 0.07, 0.09, 1.0)
MODEL_COLOR = (0.80, 0.82, 0.88)
SHOW_AXES = True
WIREFRAME = False
SMOOTH_SHADING = True
SHOW_GRID = True            # podloga, daje osecaj dubine i smera
UI_FPS = 60

SHOW_PREVIEW = True         # mali prikaz kamere u uglu
PREVIEW_W = 240

AUTO_SPIN_RATE = 25.0       # brzina automatskog okretanja (taster p)

# ============================= PUTANJE ====================================
SCREENSHOT_DIR = "snimci"   # folder za snimke ekrana (taster s)