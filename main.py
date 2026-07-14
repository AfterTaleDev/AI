import pygame
import sys, math, random, time, os, glob, json, subprocess, threading

# ──────────────────────────────────────────────────────
#  FOLDER STRUCTURE (auto-created)
#
#   glitch_os.py
#   log/         page_1.txt  page_2.txt ...
#   music/       song.wav / .ogg / .mp3 / .flac
#   images/      any .png / .jpg / .jpeg / .bmp / .gif
#   video/       bg.mp4 (optional background video)
# ──────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
LOG_D  = os.path.join(BASE, "log")
MUS_D  = os.path.join(BASE, "music")
IMG_D  = os.path.join(BASE, "images")
VID_D  = os.path.join(BASE, "video")
CFG_F  = os.path.join(BASE, "desktop_config.json")   # icon positions + settings
SND_D  = os.path.join(BASE, "sounds")
for d in (LOG_D, MUS_D, IMG_D, VID_D, SND_D):
    os.makedirs(d, exist_ok=True)

# seed demo log pages
for i, txt in enumerate([
    "You have entered the Glitched Biome. Luck is fluctuating...",
    "The Biome Selector is now active. Choose your path wisely.",
    "Warning: Unknown entity detected in the current layer.",
    "System update complete. All modules nominal.",
], 1):
    p = os.path.join(LOG_D, f"page_{i}.txt")
    if not os.path.exists(p):
        open(p, "w").write(txt)


# ──────────────────────────────────────────────────────
#  SOUND MANAGER
#  Drop these files into the  sounds/  folder:
#    open.wav      – played when any window opens
#    close.wav     – played when any window closes / glitch-closes
#    click.wav     – UI button click (poly_btn hover)
#    glitch.wav    – glitch burst during close animation
#    notify.wav    – terminal output / system event
#    boot.wav      – played once on startup
#  Any .wav / .ogg / .mp3 / .flac works.
# ──────────────────────────────────────────────────────
class SoundManager:
    SLOTS = ("open","close","click","glitch","notify","boot")
    def __init__(self):
        self._sounds = {}
        for name in self.SLOTS:
            for ext in (".wav",".ogg",".mp3",".flac"):
                p = os.path.join(SND_D, name+ext)
                if os.path.exists(p):
                    try:
                        s = pygame.mixer.Sound(p)
                        s.set_volume(0.55)
                        self._sounds[name] = s
                        break
                    except Exception as ex:
                        print(f"[SFX] could not load {p}: {ex}")
    def play(self, name):
        s = self._sounds.get(name)
        if s:
            try: s.play()
            except: pass
    def set_volume(self, v):
        for s in self._sounds.values(): s.set_volume(v)

sfx = SoundManager()

# ──────────────────────────────────────────────────────
#  COLOURS
# ──────────────────────────────────────────────────────
BLK       = (0,   0,   0)
CYN       = (0,   255, 200)
CYN_MID   = (0,   160, 120)
CYN_DIM   = (0,    80,  60)
CYN_FAINT = (0,    28,  20)
CYN_DEEP  = (0,     8,  16)
TXT       = (150, 255, 210)
BTN_FILL  = (0,   255, 200)
BTN_TXT   = (0,    10,   8)
DESK_BG   = (2,    6,  14)
SEL_ROW   = (0,   35,  25)
CALC_BG   = (0,    5,  12)

# ──────────────────────────────────────────────────────
#  INIT
# ──────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

_info   = pygame.display.Info()
SW, SH  = _info.current_w, _info.current_h
screen  = pygame.display.set_mode((SW, SH),
            pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("GLITCH_OS // v4.1")
clock   = pygame.time.Clock()

# fonts
fMono   = lambda sz, bold=False: pygame.font.SysFont("Courier New", sz, bold=bold)
fMain   = fMono(15);  fLabel = fMono(11);  fBtn  = fMono(13, True)
fStat   = fMono(10);  fIcon  = fMono(10, True); fTitle = fMono(22, True)
fTrack  = fMono(13);  fClock = fMono(11);  fCalc = fMono(20, True)
fCalcSm = fMono(13);  fBig   = fMono(28, True)
fCtxMenu = fMono(12); fTerm  = fMono(13)
_BOOT_T = time.time()   # for uptime command

# ──────────────────────────────────────────────────────
#  DESKTOP CONFIG  (save / load icon positions etc.)
# ──────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CFG_F):
        try:
            with open(CFG_F) as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}

def save_config(data):
    try:
        with open(CFG_F, "w") as fh:
            json.dump(data, fh, indent=2)
    except Exception as ex:
        print(f"[CFG] save error: {ex}")

_cfg = load_config()

# ──────────────────────────────────────────────────────
#  GLOW TEXT HELPER
# ──────────────────────────────────────────────────────
def render_glow(surf, font, text, col, pos, glow_radius=2, glow_alpha=35):
    """Crisp sci-fi glow: tight 1-px offset ring only — no blur."""
    base = font.render(text, True, col)
    halo = font.render(text, True, col)
    halo.set_alpha(glow_alpha)
    for dx, dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
        surf.blit(halo, (pos[0]+dx, pos[1]+dy))
    surf.blit(base, pos)

def glow_line(surf, col, a_col, pt1, pt2, width=1, glow_alpha=30):
    glow_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
    for w in range(width+4, width, -1):
        alpha = int(glow_alpha * (width / (w+1)))
        pygame.draw.line(glow_surf, (*col, alpha), pt1, pt2, w)
    pygame.draw.line(glow_surf, (*col, 200), pt1, pt2, width)
    surf.blit(glow_surf, (0,0))

# ──────────────────────────────────────────────────────
#  BACKGROUND MANAGER  — cyber perspective grid
# ──────────────────────────────────────────────────────
BG_MODE_GRID  = "grid"
BG_MODE_BLACK = "black"
BG_MODE_VIDEO = "video"
BG_MODE_LITE  = "lite"    # static dot-grid, no rain, no perspective

class BgManager:
    # ── data-stream rain ─────────────────────────────
    _STREAM_CHARS = "01アイウエオカキクケコサシスセソタチツテトナニヌネノ<>{}[]|/\\"
    _N_STREAMS = 55

    def __init__(self):
        self.mode = BG_MODE_GRID
        self._static_black = pygame.Surface((SW, SH)); self._static_black.fill((0,0,0))
        self._static_lite  = self._make_lite_grid()
        # perspective grid state
        self._grid_scroll = 0.0          # 0..1 continuous offset (forward motion)
        self._grid_speed  = 0.18         # grid cells per second
        # hex data streams
        self._streams = self._init_streams()
        self._stream_tick = 0
        # video
        self._video_cap = None
        self._video_surf = None
        self._video_path = None
        self._video_fps = 30.0
        self._last_frame_t = 0.0
        self._cv2_ok = False
        try:
            import cv2 as _cv2
            self._cv2 = _cv2
            self._cv2_ok = True
        except ImportError:
            self._cv2 = None
        # pre-render static layer (stars + deep bg)
        self._static_layer = self._make_static()

    # ── lite static dot-grid (original style, zero cost) ──────────
    def _make_lite_grid(self):
        s = pygame.Surface((SW, SH))
        s.fill(DESK_BG)
        GS = 36
        for gy in range(0, SH+GS, GS):
            off = GS//2 if (gy//GS)%2 else 0
            for gx in range(-GS+off, SW+GS, GS):
                pygame.draw.circle(s, (0,16,12), (gx, gy), 1)
        return s

    # ── static starfield ─────────────────────────────
    def _make_static(self):
        s = pygame.Surface((SW, SH))
        s.fill((1, 3, 10))
        # deep stars
        for _ in range(220):
            bri = random.randint(8, 60)
            pygame.draw.circle(s, (bri, int(bri*1.4), bri),
                               (random.randint(0,SW), random.randint(0,SH//2)), 1)
        return s

    # ── data streams ─────────────────────────────────
    def _init_streams(self):
        streams = []
        for _ in range(self._N_STREAMS):
            streams.append(self._new_stream())
        return streams

    def _new_stream(self, x=None):
        col_x = x if x is not None else random.randint(0, SW)
        return {
            "x": col_x,
            "y": random.uniform(-SH, 0),
            "speed": random.uniform(60, 200),
            "len": random.randint(6, 22),
            "chars": [random.choice(self._STREAM_CHARS) for _ in range(28)],
            "alpha": random.randint(60, 180),
            "bright": random.random() < 0.15,   # occasional bright head
        }

    def _update_streams(self, dt):
        fStream = pygame.font.SysFont("Courier New", 12)
        for st in self._streams:
            st["y"] += st["speed"] * dt
            # scramble a random char
            if random.random() < 0.3:
                idx = random.randint(0, len(st["chars"])-1)
                st["chars"][idx] = random.choice(self._STREAM_CHARS)
            if st["y"] - st["len"]*13 > SH:
                # respawn
                i = self._streams.index(st)
                self._streams[i] = self._new_stream()

    def _draw_streams(self, surf):
        fStream = pygame.font.SysFont("Courier New", 12)
        for st in self._streams:
            for i in range(st["len"]):
                gy = int(st["y"]) - i * 13
                if gy < 0 or gy > SH: continue
                fade = max(0, 1 - i / st["len"])
                if i == 0 and st["bright"]:
                    col = (180, 255, 230)
                    a = 255
                elif i == 0:
                    col = CYN
                    a = 230
                else:
                    g = int(fade * 160)
                    col = (0, g, int(g*0.75))
                    a = int(st["alpha"] * fade)
                ch = st["chars"][i % len(st["chars"])]
                cs = fStream.render(ch, True, col)
                cs.set_alpha(a)
                surf.blit(cs, (st["x"], gy))

    # ── perspective grid ─────────────────────────────
    def _draw_cyber_grid(self, surf, now_s):
        # Horizon sits at 42% height for a dramatic low-angle view
        HY = int(SH * 0.42)
        VX = SW // 2           # vanishing point x

        # ─ sky gradient (dark -> slightly lighter near horizon)
        sky = pygame.Surface((SW, HY), pygame.SRCALPHA)
        for row in range(HY):
            t = row / HY
            r_ = int(0 + t * 2)
            g_ = int(2 + t * 8)
            b_ = int(10 + t * 30)
            pygame.draw.line(sky, (r_, g_, b_, 255), (0, row), (SW, row))
        surf.blit(sky, (0, 0))

        # ─ floor gradient (dark at horizon -> very dark at bottom)
        floor = pygame.Surface((SW, SH - HY), pygame.SRCALPHA)
        for row in range(SH - HY):
            t = 1 - row / (SH - HY)
            r_ = int(t * 1)
            g_ = int(t * 6)
            b_ = int(4 + t * 18)
            pygame.draw.line(floor, (r_, g_, b_, 255), (0, row), (SW, row))
        surf.blit(floor, (0, HY))

        # ─ horizon glow band
        glow_h = 90
        gband = pygame.Surface((SW, glow_h), pygame.SRCALPHA)
        for row in range(glow_h):
            d = abs(row - glow_h//2) / (glow_h//2)
            a = int((1 - d**2) * 90)
            pygame.draw.line(gband, (0, 200, 160, a), (0, row), (SW, row))
        surf.blit(gband, (0, HY - glow_h//2))

        # ─ horizontal perspective lines (floor)
        N_H = 28
        scroll_frac = (now_s * self._grid_speed) % 1.0
        grid_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)

        for i in range(N_H + 1):
            t = ((i + scroll_frac) / N_H) ** 2.2   # exponential crowding near horizon
            screen_y = int(HY + t * (SH - HY))
            dist_fade = 1 - t
            a = int(dist_fade * 140)
            col_line = (0, int(dist_fade*200+40), int(dist_fade*155+30), a)
            if screen_y > HY and screen_y <= SH:
                pygame.draw.line(grid_surf, col_line, (0, screen_y), (SW, screen_y), 1)

        # ─ vertical perspective lines (floor) — fan out from vanishing point
        N_V = 26
        spread = SW * 2.2
        for i in range(N_V + 1):
            frac = i / N_V
            base_x = int(-spread/2 + frac * spread)
            # perspective: line from vanishing point to base_x at bottom
            a = int((1 - abs(frac - 0.5)*1.8) * 100)
            a = max(0, min(255, a))
            col_line = (0, 120, 90, a)
            pygame.draw.line(grid_surf, col_line, (VX, HY), (base_x, SH), 1)

        surf.blit(grid_surf, (0, 0))

        # ─ horizon line with strong glow
        for w_ in range(6, 0, -1):
            a_ = int(30 * (w_/6))
            pygame.draw.line(surf, (0, 255, 200, a_), (0, HY), (SW, HY), w_*2)
        pygame.draw.line(surf, (0, 255, 200), (0, HY), (SW, HY), 1)

        # ─ city silhouette (static random skyline)
        if not hasattr(self, "_skyline"):
            self._skyline = []
            x_ = 0
            while x_ < SW:
                w_ = random.randint(18, 60)
                h_ = random.randint(20, 110)
                self._skyline.append((x_, HY - h_, w_, h_))
                x_ += w_ + random.randint(2, 12)
        sky_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
        for bx_, by_, bw_, bh_ in self._skyline:
            # dark building
            pygame.draw.rect(sky_surf, (0, 8, 6, 200), (bx_, by_, bw_, bh_))
            pygame.draw.rect(sky_surf, (0, 40, 30, 120), (bx_, by_, bw_, bh_), 1)
            # random lit windows
            for wy in range(by_+4, by_+bh_-4, 8):
                for wx in range(bx_+3, bx_+bw_-3, 7):
                    if random.random() < 0.25:
                        wc = (0, random.randint(120,255), random.randint(80,180), 160)
                        pygame.draw.rect(sky_surf, wc, (wx, wy, 3, 4))
        surf.blit(sky_surf, (0, 0))

        # ─ far grid lines on floor surface  (bright accent)
        for i in range(0, SW, IGRID):
            a_ = 18
            pygame.draw.line(surf, (0, 60, 45, a_), (i, HY), (i + (VX-i)//2, SH), 1)

    # ─────────────────────────────────────────────────
    def set_mode(self, mode, path=None):
        if mode == BG_MODE_VIDEO:
            if not self._cv2_ok:
                print("[BG] OpenCV not installed – pip install opencv-python"); return
            if path is None:
                mp4s = sorted([f for f in os.listdir(VID_D) if f.lower().endswith((".mp4",".avi",".mov",".mkv"))])
                if not mp4s: print("[BG] No video files in video/"); return
                path = os.path.join(VID_D, mp4s[0])
            if self._video_cap: self._video_cap.release()
            cap = self._cv2.VideoCapture(path)
            if not cap.isOpened(): print(f"[BG] Can't open: {path}"); return
            self._video_cap = cap
            fps = cap.get(self._cv2.CAP_PROP_FPS)
            self._video_fps = fps if fps > 0 else 30.0
            self._last_frame_t = time.time()
            self.mode = BG_MODE_VIDEO
        else:
            if self._video_cap: self._video_cap.release(); self._video_cap = None
            self.mode = mode
            if mode == BG_MODE_LITE:
                pass  # no extra setup needed

    def pick_video(self):
        try:
            import tkinter as tk; from tkinter import filedialog
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            path = filedialog.askopenfilename(initialdir=VID_D, title="Select background video",
                filetypes=[("Video files","*.mp4 *.avi *.mov *.mkv"),("All","*.*")])
            root.destroy()
            if path: self.set_mode(BG_MODE_VIDEO, path)
        except Exception as ex: print(f"[BG] picker: {ex}")

    def update(self, now_s, dt):
        if self.mode != BG_MODE_LITE:
            self._update_streams(dt)
        if self.mode != BG_MODE_VIDEO or not self._video_cap: return
        interval = 1.0 / self._video_fps
        if now_s - self._last_frame_t < interval: return
        self._last_frame_t = now_s
        ret, frame = self._video_cap.read()
        if not ret:
            self._video_cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._video_cap.read()
        if ret:
            frame = self._cv2.resize(frame, (SW, SH))
            frame = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
            frame = (frame * 0.22).astype("uint8")
            frame[:,:,1] = (frame[:,:,1].astype(int) + 12).clip(0,255).astype("uint8")
            self._video_surf = pygame.surfarray.make_surface(frame.swapaxes(0,1))

    def draw(self, surf, now_s):
        if self.mode == BG_MODE_GRID:
            surf.blit(self._static_layer, (0, 0))
            self._draw_cyber_grid(surf, now_s)
            # data rain on top (subtle)
            rain_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            self._draw_streams(rain_surf)
            surf.blit(rain_surf, (0, 0))
        elif self.mode == BG_MODE_BLACK:
            surf.blit(self._static_black, (0, 0))
            # still draw rain on black
            rain_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            self._draw_streams(rain_surf)
            surf.blit(rain_surf, (0, 0))
        elif self.mode == BG_MODE_LITE:
            surf.blit(self._static_lite, (0, 0))  # zero-cost static grid
        elif self.mode == BG_MODE_VIDEO:
            if self._video_surf:
                surf.blit(self._video_surf, (0, 0))
            else:
                surf.blit(self._static_black, (0, 0))

bg_mgr = BgManager()

# ──────────────────────────────────────────────────────
#  CONTEXT MENU
# ──────────────────────────────────────────────────────
class ContextMenu:
    ITH = 24
    PAD = 8

    def __init__(self):
        self.visible = False
        self.x = 0; self.y = 0
        self.items = []

    def show(self, x, y, items):
        self.visible = True
        self.x = x; self.y = y
        self.items = items
        w = self._width(); h = self._height()
        if self.x + w > SW: self.x = SW - w - 4
        if self.y + h > SH - TASKBAR_H: self.y = SH - TASKBAR_H - h - 4

    def hide(self): self.visible = False

    def _is_sep(self, it): return it is None or it[0] is None

    def _width(self):
        mx = max((fCtxMenu.size(it[0])[0] for it in self.items if not self._is_sep(it)), default=80)
        return mx + self.PAD*4

    def _height(self):
        return sum(self.ITH if not self._is_sep(it) else 6 for it in self.items) + self.PAD*2

    def _item_rects(self):
        rects = []
        cy = self.y + self.PAD
        for it in self.items:
            if self._is_sep(it):
                rects.append(None)
                cy += 6
            else:
                rects.append(pygame.Rect(self.x + self.PAD, cy, self._width() - self.PAD*2, self.ITH))
                cy += self.ITH
        return rects

    def handle(self, event):
        if not self.visible: return False
        mx, my = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                rects = self._item_rects()
                for i, r in enumerate(rects):
                    if r and not self._is_sep(self.items[i]) and r.collidepoint(mx, my):
                        cb = self.items[i][1]
                        self.hide()
                        if cb: cb()
                        return True
                self.hide()
                return True
            elif event.button == 3:
                self.hide()
                return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        return False

    def draw(self, surf):
        if not self.visible: return
        mx, my = pygame.mouse.get_pos()
        w = self._width(); h = self._height()
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((0, 6, 18, 230))
        surf.blit(bg, (self.x, self.y))
        r = pygame.Rect(self.x, self.y, w, h)
        pygame.draw.rect(surf, CYN_MID, r, 1)
        for off in range(1, 3):
            gr = r.inflate(off*2, off*2)
            gsurf = pygame.Surface((gr.w, gr.h), pygame.SRCALPHA)
            pygame.draw.rect(gsurf, (0, 255, 200, 18 - off*6), gsurf.get_rect(), 1)
            surf.blit(gsurf, (gr.x, gr.y))

        rects = self._item_rects()
        for i, (it, r2) in enumerate(zip(self.items, rects)):
            if self._is_sep(it):
                sy = self.y + self.PAD + sum(
                    (self.ITH if not self._is_sep(self.items[j]) else 6) for j in range(i))
                pygame.draw.line(surf, CYN_FAINT,
                    (self.x + self.PAD, sy + 3), (self.x + w - self.PAD, sy + 3))
            else:
                hov = r2.collidepoint(mx, my)
                if hov:
                    hov_s = pygame.Surface((r2.w, r2.h), pygame.SRCALPHA)
                    hov_s.fill((0, 255, 200, 28))
                    surf.blit(hov_s, (r2.x, r2.y))
                col = CYN if hov else CYN_DIM
                render_glow(surf, fCtxMenu, it[0], col,
                            (r2.x + 6, r2.y + r2.h//2 - fCtxMenu.get_height()//2),
                            glow_radius=2, glow_alpha=40 if hov else 15)

ctx_menu = ContextMenu()

# ──────────────────────────────────────────────────────
#  PARTICLES
# ──────────────────────────────────────────────────────
NUM_P = 38; CONN = 90
pts = [{"x":random.uniform(0,SW),"y":random.uniform(0,SH),
        "vx":random.uniform(-.22,.22),"vy":random.uniform(-.22,.22),
        "r":random.uniform(.8,2.),"b":random.randint(70,190)} for _ in range(NUM_P)]
PSURF = pygame.Surface((SW, SH), pygame.SRCALPHA)

TASKBAR_H = 36
STATUS_H  = 26
MIN_W, MIN_H = 300, 220
RESIZE_M  = 14
ANIM_SPD  = 14.0

# ──────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────
def make_box(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 4, 14, 250))
    # scanlines
    for ly in range(0, h, 4):
        pygame.draw.line(s, (0,255,200,3), (0,ly), (w,ly))
    # hex grid overlay (subtle)
    HEX = 22
    for row in range(h // HEX + 2):
        for col in range(w // HEX + 2):
            cx = col * HEX*2 + (HEX if row%2 else 0)
            cy = row * int(HEX*1.73)
            pts = [(cx+HEX*math.cos(math.radians(60*i)),
                    cy+HEX*math.sin(math.radians(60*i))) for i in range(6)]
            pts_i = [(int(p[0]),int(p[1])) for p in pts]
            try: pygame.draw.polygon(s,(0,255,200,4),pts_i,1)
            except: pass
    # footer bar
    pygame.draw.rect(s, (0,5,16,235), (0, h-52, w, 52))
    pygame.draw.line(s,(0,255,200,30),(0,h-52),(w,h-52))
    # side edge glow strips
    for i in range(4):
        a = 12-i*2
        pygame.draw.line(s,(0,255,200,a),(i,0),(i,h))
        pygame.draw.line(s,(0,255,200,a),(w-1-i,0),(w-1-i,h))
    # top edge accent
    pygame.draw.line(s,(0,255,200,40),(0,0),(w,0),1)
    return s

def draw_corners(s, r, col, L=40, t=2):
    lx,ty,rx,by_ = r.left,r.top,r.right,r.bottom
    for seg in [[(lx,ty+L),(lx,ty),(lx+L,ty)],[(rx-L,ty),(rx,ty),(rx,ty+L)],
                [(lx,by_-L),(lx,by_),(lx+L,by_)],[(rx-L,by_),(rx,by_),(rx,by_-L)]]:
        pygame.draw.lines(s,col,False,seg,t)
    gsurf = pygame.Surface((r.w+10, r.h+10), pygame.SRCALPHA)
    for seg in [[(lx,ty+L),(lx,ty),(lx+L,ty)],[(rx-L,ty),(rx,ty),(rx,ty+L)],
                [(lx,by_-L),(lx,by_),(lx+L,by_)],[(rx-L,by_),(rx,by_),(rx,by_-L)]]:
        adj = [(p[0]-r.left+5, p[1]-r.top+5) for p in seg]
        pygame.draw.lines(gsurf,(col[0],col[1],col[2],35),False,adj,4)
    s.blit(gsurf,(r.left-5,r.top-5))
    for a,b_ in [((lx+L,ty),(rx-L,ty)),((lx+L,by_),(rx-L,by_)),
                 ((lx,ty+L),(lx,by_-L)),((rx,ty+L),(rx,by_-L))]:
        pygame.draw.line(s,CYN_FAINT,a,b_)
    cx=r.centerx
    pygame.draw.line(s,CYN_DIM,(cx-8,ty),(cx+8,ty))
    pygame.draw.line(s,CYN_DIM,(cx-8,by_),(cx+8,by_))

def edge_at(mx,my,bx,by,bw,bh):
    nr=abs(mx-(bx+bw))<RESIZE_M and by<=my<=by+bh
    nb=abs(my-(by+bh))<RESIZE_M and bx<=mx<=bx+bw
    if nr and nb: return "corner"
    if nr: return "right"
    if nb: return "bottom"
    return None

def close_r(bx,by,bw):   return pygame.Rect(bx+bw-46,by+5,18,16)
def min_r(bx,by,bw):     return pygame.Rect(bx+bw-70,by+5,18,16)

def draw_title_btns(surf,bx,by,bw,mx,my):
    for r,lbl in [(close_r(bx,by,bw),"X"),(min_r(bx,by,bw),"_")]:
        hov = r.collidepoint(mx,my)
        col = CYN if hov else CYN_DIM
        pygame.draw.rect(surf,col,r,1)
        if hov:
            g = pygame.Surface((r.w+4,r.h+4), pygame.SRCALPHA)
            pygame.draw.rect(g,(col[0],col[1],col[2],40),(0,0,r.w+4,r.h+4),2)
            surf.blit(g,(r.x-2,r.y-2))
        s = fStat.render(lbl,True,col)
        surf.blit(s,(r.x+r.w//2-s.get_width()//2, r.y+r.h//2-s.get_height()//2))

_poly_btn_hov = set()  # track hover state for click sfx
def poly_btn(surf, r, t, col, label, lift=True):
    dr = r.move(0,-int(t*3)) if lift else r
    rid = (r.x,r.y,r.w,r.h)
    mx_,my_ = pygame.mouse.get_pos()
    hov_now = r.collidepoint(mx_,my_)
    if hov_now and rid not in _poly_btn_hov:
        sfx.play("click")
    if hov_now: _poly_btn_hov.add(rid)
    else:        _poly_btn_hov.discard(rid)
    if t>0:
        pygame.draw.rect(surf,BTN_FILL,(dr.x,dr.y,int(dr.w*t),dr.h))
    c=5; bx,by,bw,bh=dr.x,dr.y,dr.w,dr.h
    poly=[(bx+c,by),(bx+bw-c,by),(bx+bw,by+c),(bx+bw,by+bh-c),
          (bx+bw-c,by+bh),(bx+c,by+bh),(bx,by+bh-c),(bx,by+c)]
    pygame.draw.polygon(surf,col,poly,1)
    if t > 0.1:
        g = pygame.Surface((bw+8,bh+8),pygame.SRCALPHA)
        gpoly = [(p[0]-bx+4, p[1]-by+4) for p in poly]
        pygame.draw.polygon(g,(col[0],col[1],col[2],int(40*t)),gpoly,2)
        surf.blit(g,(bx-4,by-4))
    for px,py in [(bx+c,by),(bx+bw-c,by),(bx+c,by+bh),(bx+bw-c,by+bh)]:
        pygame.draw.circle(surf,col,(px,py),2)
    tc = BTN_TXT if t>.5 else col
    ls = fBtn.render(label,True,tc)
    surf.blit(ls,(dr.x+dr.w//2-ls.get_width()//2, dr.y+dr.h//2-ls.get_height()//2))

def wrap(text, font, maxw):
    result = []
    for paragraph in text.split("\n"):
        if not paragraph:
            result.append("")
            continue
        words = paragraph.split(" ")
        line = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] <= maxw:
                line = test
            else:
                if line:
                    result.append(line.rstrip())
                while font.size(w)[0] > maxw:
                    for cut in range(len(w), 0, -1):
                        if font.size(w[:cut])[0] <= maxw:
                            result.append(w[:cut])
                            w = w[cut:]
                            break
                line = w + " "
        if line:
            result.append(line.rstrip())
    return result or [""]

def ease_out(t): return 1-(1-t)**3
def ease_in(t):  return t*t*t

# ──────────────────────────────────────────────────────
#  BASE WINDOW
# ──────────────────────────────────────────────────────
class Window:
    Z = 0
    def __init__(self, wid, label, x, y, w, h):
        self.wid    = wid
        self.label  = label
        self.x = x; self.y = y; self.W = w; self.H = h
        self._surf  = make_box(w, h); self._sz = (w, h)
        self.anim   = 0.0
        self.state  = "closed"
        self.scan_y = 0.0
        self.glitch = []
        self.drag   = False; self.dox=0; self.doy=0
        self.resize = False; self.re=None; self.rs=(0,0); self.ro=(0,0)
        Window.Z += 1; self.z = Window.Z
        # glitch-close
        self._gc_active = False   # glitch-close in progress
        self._gc_t      = 0.0     # 0..1 progress
        self._gc_dur    = 0.45    # seconds
        self._gc_slices = []      # list of (y,h,dx,col) displacement slices
        self._open_t    = 0.0     # 0..1 open-glitch progress (title scramble)

    def bring_to_front(self):
        Window.Z += 1; self.z = Window.Z

    @property
    def visible(self): return self.state not in ("closed",)

    def open(self):
        if self.state in ("closed","closing"):
            self.state = "opening"; self.bring_to_front()
            sfx.play("open")
            self._open_t = 0.0

    def close(self):
        if self.state not in ("closed","closing"):
            self._gc_active = True
            self._gc_t      = 0.0
            self._gc_slices = []
            sfx.play("close")
            self.state = "closing"

    def hide(self):
        if self.state == "open":
            self.state = "hidden"

    def show(self):
        if self.state == "hidden":
            self.state = "open"; self.bring_to_front()
        elif self.state == "closed":
            self.open()

    def toggle(self):
        if self.state == "open": self.hide()
        elif self.state == "hidden": self.show()
        elif self.state == "closed": self.open()

    def _rebuild(self):
        if (self.W,self.H)!=self._sz:
            self._surf=make_box(self.W,self.H); self._sz=(self.W,self.H)

    def update_anim(self, dt):
        spd = ANIM_SPD * dt
        if self.state == "opening":
            self.anim = min(1.0, self.anim + spd)
            self._open_t = min(1.0, self._open_t + dt * 3.5)
            if self.anim >= 1.0: self.state = "open"
        elif self.state == "closing":
            # drive glitch-close
            if self._gc_active:
                self._gc_t = min(1.0, self._gc_t + dt / self._gc_dur)
                # regenerate displacement slices at high frequency
                if random.random() < 0.6:
                    self._gc_slices = []
                    n = int(6 + self._gc_t * 18)
                    for _ in range(n):
                        gy   = random.uniform(0, 1)
                        gh   = random.uniform(0.01, 0.06 + self._gc_t * 0.12)
                        dx   = random.randint(-int(self.W*0.25*self._gc_t),
                                              int(self.W*0.25*self._gc_t))
                        cidx = random.randint(0,2)
                        col  = [(0,255,200,180),(255,0,80,160),(0,80,255,140)][cidx]
                        self._gc_slices.append((gy, gh, dx, col))
                # play glitch sfx at ~30% progress
                if 0.28 < self._gc_t < 0.35:
                    sfx.play("glitch")
                # start collapsing anim after 55% of glitch sequence
                if self._gc_t >= 0.55:
                    self.anim = max(0.0, self.anim - spd * 2.2)
                if self._gc_t >= 1.0:
                    self._gc_active = False
            else:
                self.anim = max(0.0, self.anim - spd)
            if self.anim <= 0.0: self.state = "closed"

    def update_fx(self, dt_ms, now_ms):
        self.scan_y=(self.scan_y+dt_ms/2800.)%1.
        if random.random()<.018:
            self.glitch.append({"y":random.uniform(0,1),"h":random.uniform(1,4),
                "a":random.randint(8,28),"exp":now_ms+random.randint(50,140)})
        self.glitch=[g for g in self.glitch if g["exp"]>now_ms]

    def handle_base(self, event, now_ms):
        mx,my = pygame.mouse.get_pos()
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            bx,by,bw,bh = self.x,self.y,self.W,self.H
            if not pygame.Rect(bx,by,bw,bh).collidepoint(mx,my): return None
            self.bring_to_front()
            if close_r(bx,by,bw).collidepoint(mx,my): return "close"
            if min_r(bx,by,bw).collidepoint(mx,my):   return "minimize"
            e=edge_at(mx,my,bx,by,bw,bh)
            if e:
                self.resize=True;self.re=e;self.rs=(mx,my);self.ro=(bw,bh)
            elif pygame.Rect(bx,by,bw,STATUS_H).collidepoint(mx,my):
                self.drag=True;self.dox=mx-bx;self.doy=my-by
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self.drag=self.resize=False;self.re=None
        if event.type==pygame.MOUSEMOTION:
            if self.drag: self.x=mx-self.dox;self.y=my-self.doy
            if self.resize:
                dx,dy=mx-self.rs[0],my-self.rs[1]
                if self.re in("right","corner"):  self.W=max(MIN_W,self.ro[0]+dx)
                if self.re in("bottom","corner"): self.H=max(MIN_H,self.ro[1]+dy)
                self._rebuild()
        return None

    def draw_frame(self, surf, mx, my, title=""):
        if self.state not in ("open","opening","closing"): return False
        t = ease_out(self.anim)
        bx,by,bw,bh = self.x,self.y,self.W,self.H
        vis_h = max(2, int(bh * t))
        clip  = pygame.Rect(bx, by, bw, vis_h)
        surf.set_clip(clip)
        self._rebuild()
        surf.blit(self._surf,(bx,by))
        for g in self.glitch:
            gy=by+int(g["y"]*bh); gh=max(1,int(g["h"]))
            gs=pygame.Surface((bw,gh));gs.set_alpha(g["a"]);gs.fill(CYN)
            surf.blit(gs,(bx,gy))
        sy=by+int(self.scan_y*bh)
        pygame.draw.line(surf,(0,60,46),(bx,sy),(bx+bw,sy),2)
        pygame.draw.line(surf,CYN_FAINT,(bx,by+STATUS_H),(bx+bw,by+STATUS_H))
        ts=fStat.render(time.strftime("%H:%M:%S"),True,CYN_DIM)
        # glitch-scramble title on open
        if self._open_t < 1.0:
            _GC = "!@#$%^&*░▒▓<>{}[]|01アイウエオ"
            full = f"SYS :: {title}"
            reveal = int(self._open_t * len(full))
            scrambled = full[:reveal] + "".join(random.choice(_GC) for _ in range(len(full)-reveal))
            render_glow(surf, fStat, scrambled, CYN_MID, (bx+12,by+7), glow_radius=2, glow_alpha=35)
        else:
            render_glow(surf, fStat, f"SYS :: {title}", CYN_DIM, (bx+12,by+7), glow_radius=2, glow_alpha=35)
        surf.blit(ts,(bx+bw-ts.get_width()-50,by+7))
        draw_title_btns(surf,bx,by,bw,mx,my)
        # glitch-close slices
        if self._gc_active and self._gc_slices:
            gsurf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            for (gy_f, gh_f, dx, col) in self._gc_slices:
                gy_px = int(gy_f * bh)
                gh_px = max(1, int(gh_f * bh))
                # copy strip and displace
                strip_y = max(0, gy_px)
                strip_h = min(gh_px, bh - strip_y)
                if strip_h <= 0: continue
                try:
                    strip = self._surf.subsurface(pygame.Rect(0, strip_y, bw, strip_h)).copy()
                    strip.fill((*col[:3], col[3]), special_flags=pygame.BLEND_RGBA_MULT)
                    gsurf.blit(strip, (dx, strip_y))
                    # chromatic offset
                    strip2 = strip.copy()
                    strip2.set_alpha(80)
                    gsurf.blit(strip2, (dx+4, strip_y))
                except Exception:
                    pass
            # flicker whole window
            if random.random() < self._gc_t * 0.5:
                gsurf.set_alpha(int(180 * self._gc_t))
            screen_clip = pygame.Rect(bx, by, bw, vis_h)
            surf.set_clip(screen_clip)
            surf.blit(gsurf, (bx, by))
        surf.set_clip(None)
        draw_corners(surf,pygame.Rect(bx,by,bw,bh),CYN)
        return True

    def cursor_check(self):
        if self.state!="open": return False
        mx,my=pygame.mouse.get_pos()
        e=self.re or edge_at(mx,my,self.x,self.y,self.W,self.H)
        if   e=="corner": pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENWSE);return True
        elif e=="right":  pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE);  return True
        elif e=="bottom": pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENS);  return True
        elif self.drag or pygame.Rect(self.x,self.y,self.W,STATUS_H).collidepoint(mx,my):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL);return True
        return False


# ══════════════════════════════════════════════════════
#  LOG WINDOW
# ══════════════════════════════════════════════════════
class LogWin(Window):
    LINE_H = 22
    SCROLL_SPD = 3

    def __init__(self, x=None, y=None):
        sx = SW//2-260 if x is None else x
        sy = SH//2-175 if y is None else y
        super().__init__("log","LOG", sx, sy, 520, 350)
        self.pages   = self._load()
        self.total   = len(self.pages)
        self.cur=0; self.tgt=0
        self.disp=""; self.ci=0; self.erasing=False; self.tick=0
        self.bt={"last":0.,"next":0.,"edit":0.,"new":0.,"save":0.,"del":0.}
        self.editing  = False
        self.edit_buf = ""
        self.repeat_key=None; self.repeat_t=0; self.repeat_d=0
        self.scroll_line = 0

    def _load(self):
        fs=sorted([f for f in os.listdir(LOG_D) if f.startswith("page_") and f.endswith(".txt")],
                  key=lambda f:int(f.split("_")[1].split(".")[0]))
        pages=[]
        for fn in fs:
            with open(os.path.join(LOG_D,fn)) as fh: pages.append(fh.read().strip())
        return pages or ["No pages found."]

    def _save_cur(self):
        for i,txt in enumerate(self.pages,1):
            with open(os.path.join(LOG_D,f"page_{i}.txt"),"w") as fh: fh.write(txt)
        i=len(self.pages)+1
        while os.path.exists(os.path.join(LOG_D,f"page_{i}.txt")):
            os.remove(os.path.join(LOG_D,f"page_{i}.txt")); i+=1

    def _new_page(self):
        self.pages.append(""); self.total=len(self.pages)
        self.cur=self.total-1
        self.disp=""; self.ci=0; self.erasing=False
        self.editing=True; self.edit_buf=""
        self.scroll_line=0
        self._save_cur()

    def _del_page(self):
        if self.total<=1: self.pages=[""]; self.total=1; self.cur=0
        else:
            self.pages.pop(self.cur)
            self.total=len(self.pages)
            self.cur=min(self.cur,self.total-1)
        self._save_cur()
        self.disp=""; self.ci=0; self.erasing=False
        self.editing=False; self.scroll_line=0

    def _content_rect(self):
        return pygame.Rect(self.x+14, self.y+STATUS_H+28, self.W-28, self.H-STATUS_H-80)

    def _visible_lines(self):
        cr = self._content_rect()
        return max(1, cr.h // self.LINE_H)

    def _brs(self):
        by_=self.y+self.H-52
        return pygame.Rect(self.x+14,by_+11,72,26), pygame.Rect(self.x+self.W-86,by_+11,72,26)

    def _toolbar(self):
        tx=self.x+self.W-220; ty=self.y+STATUS_H+6
        return {
            "edit": pygame.Rect(tx,    ty, 46, 18),
            "new":  pygame.Rect(tx+52, ty, 46, 18),
            "save": pygame.Rect(tx+104,ty, 46, 18),
            "del":  pygame.Rect(tx+156,ty, 46, 18),
        }

    def handle(self,event,now_ms):
        # process end-of-track event even when hidden
        if event.type==pygame.USEREVENT and self.state in ("open","hidden"):
            if self.looping: self._play(self.cur)
            else: self._next()
            return
        if self.state!="open": return
        act=self.handle_base(event,now_ms)
        if act=="close":
            if self.editing: self._commit(); self.editing=False
            self.close()
        elif act=="minimize": self.hide()

        mx,my=pygame.mouse.get_pos()
        tb=self._toolbar()
        cr=self._content_rect()

        if event.type==pygame.MOUSEWHEEL:
            if cr.collidepoint(*pygame.mouse.get_pos()):
                text = self.edit_buf if self.editing else self.disp
                lines = wrap(text, fMain, cr.w-12)
                max_scroll = max(0, len(lines) - self._visible_lines())
                self.scroll_line = max(0, min(max_scroll, self.scroll_line - event.y * self.SCROLL_SPD))

        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            lb,nb=self._brs()
            if tb["edit"].collidepoint(mx,my):
                if not self.editing:
                    self.editing=True; self.edit_buf=self.pages[self.cur]; self.scroll_line=0
                else:
                    self._commit(); self.editing=False
            elif tb["new"].collidepoint(mx,my):  self._new_page()
            elif tb["save"].collidepoint(mx,my):
                if self.editing: self._commit()
                else: self._save_cur()
            elif tb["del"].collidepoint(mx,my):  self._del_page()
            elif nb.collidepoint(mx,my) and not self.erasing and not self.editing:
                if self.cur<self.total-1:
                    self.tgt=self.cur+1; self.erasing=True; self.scroll_line=0
            elif lb.collidepoint(mx,my) and not self.erasing and not self.editing:
                if self.cur>0:
                    self.tgt=self.cur-1; self.erasing=True; self.scroll_line=0
            if cr.collidepoint(mx,my) and not self.editing:
                self.editing=True; self.edit_buf=self.pages[self.cur]; self.scroll_line=0

        if self.editing:
            if event.type==pygame.KEYDOWN:
                k=event.key; uni=event.unicode
                if k==pygame.K_ESCAPE:   self.editing=False; self.scroll_line=0
                elif k==pygame.K_RETURN: self.edit_buf+="\n"; self.scroll_line=9999
                elif k==pygame.K_BACKSPACE:
                    self.edit_buf=self.edit_buf[:-1]
                    self.repeat_key=k; self.repeat_t=now_ms+420; self.repeat_d=40
                elif uni and uni.isprintable():
                    self.edit_buf+=uni
                    self.repeat_key=k; self.repeat_t=now_ms+420; self.repeat_d=40
                else: self.repeat_key=None
            if event.type==pygame.KEYUP: self.repeat_key=None

    def _commit(self):
        self.pages[self.cur]=self.edit_buf.strip()
        self._save_cur()
        self.disp=""; self.ci=0; self.erasing=False

    def update(self,dt_ms,now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in("open","opening","closing"): return
        self.update_fx(dt_ms,now_ms)
        if self.editing and self.repeat_key==pygame.K_BACKSPACE:
            if now_ms>=self.repeat_t:
                self.edit_buf=self.edit_buf[:-1]; self.repeat_t=now_ms+self.repeat_d
        if not self.editing:
            iv=16 if self.erasing else 30
            if now_ms-self.tick>=iv:
                self.tick=now_ms
                if self.erasing:
                    if self.disp: self.disp=self.disp[:-1]
                    else: self.erasing=False;self.cur=self.tgt;self.ci=0
                else:
                    full=self.pages[self.cur]
                    if self.ci<len(full): self.disp+=full[self.ci];self.ci+=1
        if self.editing:
            cr = self._content_rect()
            lines = wrap(self.edit_buf, fMain, cr.w-12)
            vis = self._visible_lines()
            max_s = max(0, len(lines) - vis)
            self.scroll_line = min(self.scroll_line, max_s)
            if self.scroll_line == 9999:
                self.scroll_line = max_s

    def draw(self,surf,dt_ms,now_ms):
        mx,my=pygame.mouse.get_pos()
        if not self.draw_frame(surf,mx,my,"LOG_MODULE"): return
        t_anim=ease_out(self.anim)
        bx,by,bw,bh=self.x,self.y,self.W,self.H
        vis_h=int(bh*t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        render_glow(surf, fLabel, f"PAGE_{self.cur+1:02d}/{self.total:02d}",
                    CYN_DIM, (bx+26, by+STATUS_H+9), glow_radius=2, glow_alpha=30)

        tb=self._toolbar()
        tb_labels={"edit":"EDIT" if not self.editing else "DONE",
                   "new":"NEW","save":"SAVE","del":"DEL"}
        for k,r in tb.items():
            hov=r.collidepoint(mx,my)
            col=CYN if (hov or (k=="edit" and self.editing)) else CYN_DIM
            pygame.draw.rect(surf,(0,30,20) if (k=="edit" and self.editing) else (0,0,0),r)
            pygame.draw.rect(surf,col,r,1)
            if hov:
                g=pygame.Surface((r.w+4,r.h+4),pygame.SRCALPHA)
                pygame.draw.rect(g,(col[0],col[1],col[2],35),(0,0,r.w+4,r.h+4),1)
                surf.blit(g,(r.x-2,r.y-2))
            ls=fStat.render(tb_labels[k],True,col)
            surf.blit(ls,(r.x+r.w//2-ls.get_width()//2,r.y+r.h//2-ls.get_height()//2))

        cr = self._content_rect()
        vis = self._visible_lines()

        if self.editing:
            edit_bg=pygame.Surface((cr.w,cr.h),pygame.SRCALPHA)
            edit_bg.fill((0,20,14,120)); surf.blit(edit_bg,(cr.x,cr.y))
            pygame.draw.rect(surf,CYN_DIM,cr,1)

            display_text=self.edit_buf+"▌" if (now_ms//530)%2==0 else self.edit_buf
            lines=wrap(display_text if display_text else " ",fMain,cr.w-16)

            for i in range(vis):
                li = i + self.scroll_line
                if li >= len(lines): break
                y_ = cr.y + 4 + i * self.LINE_H
                surf.blit(fMain.render(lines[li],True,TXT),(cr.x+8,y_))

            if len(lines) > vis:
                sb_x = cr.x + cr.w - 6
                sb_h = cr.h
                th = max(16, int(sb_h * vis / len(lines)))
                ty_ = cr.y + int(sb_h * self.scroll_line / len(lines))
                pygame.draw.rect(surf, CYN_FAINT, (sb_x, cr.y, 4, sb_h))
                pygame.draw.rect(surf, CYN_DIM,   (sb_x, ty_, 4, th))

            hint=fStat.render("ESC=cancel  ENTER=newline  scroll=navigate",True,CYN_FAINT)
            surf.blit(hint,(bx+14,cr.y+cr.h+3))
        else:
            lines=wrap(self.disp,fMain,cr.w-16)
            for i in range(vis):
                li = i + self.scroll_line
                if li >= len(lines): break
                y_ = cr.y + 6 + i * self.LINE_H
                surf.blit(fMain.render(lines[li],True,TXT),(cr.x+8,y_))

            if len(lines) > vis:
                sb_x = cr.x + cr.w - 6
                sb_h = cr.h
                th = max(16, int(sb_h * vis / len(lines)))
                ty_ = cr.y + int(sb_h * self.scroll_line / len(lines))
                pygame.draw.rect(surf, CYN_FAINT, (sb_x, cr.y, 4, sb_h))
                pygame.draw.rect(surf, CYN_DIM,   (sb_x, ty_, 4, th))

            vis_lines = lines[self.scroll_line:self.scroll_line+vis]
            if (now_ms//650)%2==0 and self.ci<len(self.pages[self.cur]) and vis_lines:
                lw=fMain.size(vis_lines[-1])[0]
                row_idx=min(len(vis_lines)-1, len(vis_lines)-1)
                pygame.draw.rect(surf,CYN,(cr.x+8+lw+2,cr.y+6+row_idx*self.LINE_H+3,8,14))

        BAR=by+bh-52
        pygame.draw.line(surf,CYN_FAINT,(bx,BAR),(bx+bw,BAR))
        render_glow(surf, fStat, "v4.1 // GLITCH_OS", CYN_FAINT,
                    (bx+bw//2 - fStat.size("v4.1 // GLITCH_OS")[0]//2, BAR-fStat.get_height()-2),
                    glow_radius=2, glow_alpha=25)

        lb,nb=self._brs()
        for key,btn,en in[("last",lb,self.cur>0 and not self.erasing and not self.editing),
                          ("next",nb,self.cur<self.total-1 and not self.erasing and not self.editing)]:
            hov=btn.collidepoint(mx,my) and en
            self.bt[key]=max(0.,min(1.,self.bt[key]+(9 if hov else -9)*dt_ms/1000.))
            col=CYN if en else CYN_FAINT
            poly_btn(surf,btn,self.bt[key],col,"LAST" if key=="last" else "NEXT")

        dg=14; tot=self.total*dg; dx0=bx+bw//2-tot//2; dy0=BAR+19
        for i in range(min(self.total,30)):
            sz=4 if i==self.cur else 2
            pygame.draw.rect(surf,CYN if i==self.cur else CYN_DIM,(dx0+i*dg,dy0,sz*2,sz*2))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  MUSIC PLAYER
# ══════════════════════════════════════════════════════
class MusicWin(Window):
    def __init__(self):
        super().__init__("music","MUSIC",SW//2-230+50,SH//2-190+40,460,400)
        self.tracks   = self._load()
        self.cur=0; self.playing=False; self.looping=False
        self.progress=0.; self.tlen=0.; self.pstart=0.; self.ppos=0.
        self.scroll=0; self.TH=34; self.VT=6
        self.scrub=False
        self.bt={k:0. for k in("prev","play","next","loop")}
        self.bars=[random.uniform(.1,.9) for _ in range(20)]
        self.btgt=[random.uniform(.1,.9) for _ in range(20)]

    def _load(self):
        exts=(".wav",".ogg",".mp3",".flac")
        fs=sorted([f for f in os.listdir(MUS_D) if f.lower().endswith(exts)])
        if not fs: return[{"n":"NO TRACKS FOUND","p":None}]
        return[{"n":os.path.splitext(f)[0].upper(),"p":os.path.join(MUS_D,f)} for f in fs]

    @staticmethod
    def _probe_length(path):
        try:
            from mutagen import File as MFile
            mf = MFile(path)
            if mf is not None and hasattr(mf, "info") and mf.info:
                return float(mf.info.length)
        except Exception:
            pass
        if path.lower().endswith(".wav"):
            try:
                snd = pygame.mixer.Sound(path)
                l = snd.get_length(); del snd; return l
            except Exception:
                pass
        return 0.

    def _play(self,idx):
        if not 0<=idx<len(self.tracks): return
        t=self.tracks[idx]
        if not t["p"]: return
        self.cur=idx; pygame.mixer.music.stop()
        try:
            pygame.mixer.music.load(t["p"]); pygame.mixer.music.play()
            self.playing=True; self.pstart=time.time(); self.ppos=0.
            self.tlen = self._probe_length(t["p"])
        except Exception as ex: print(f"[MUSIC]{ex}");self.playing=False

    def _toggle(self):
        if not self.playing:
            if self.tracks[self.cur]["p"]: self._play(self.cur)
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause();self.ppos=time.time()-self.pstart;self.playing=False
        else:
            pygame.mixer.music.unpause();self.pstart=time.time()-self.ppos;self.playing=True

    def _next(self): self._play((self.cur+1)%len(self.tracks))
    def _prev(self): self._play((self.cur-1)%len(self.tracks))

    def _ctrls(self):
        cy=self.y+self.H-90; cx=self.x+self.W//2
        return{"prev":pygame.Rect(cx-116,cy,50,26),"play":pygame.Rect(cx-28,cy,56,26),
               "next":pygame.Rect(cx+36,cy,50,26),"loop":pygame.Rect(cx+94,cy,50,26)}

    def _prog(self): return pygame.Rect(self.x+18,self.y+self.H-54,self.W-36,6)

    def _tlr(self): return pygame.Rect(self.x+10,self.y+STATUS_H+36,self.W-20,self.TH*self.VT)

    def handle(self,event,now_ms):
        # process end-of-track event even when hidden
        if event.type==pygame.USEREVENT and self.state in ("open","hidden"):
            if self.looping: self._play(self.cur)
            else: self._next()
            return
        if self.state!="open": return
        act=self.handle_base(event,now_ms)
        if act=="close": self._stop();self.close()
        elif act=="minimize": self.hide()
        mx,my=pygame.mouse.get_pos()
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            cs=self._ctrls();pr=self._prog();tlr=self._tlr()
            if cs["play"].collidepoint(mx,my): self._toggle()
            elif cs["next"].collidepoint(mx,my): self._next()
            elif cs["prev"].collidepoint(mx,my): self._prev()
            elif cs["loop"].collidepoint(mx,my): self.looping=not self.looping
            elif pr.collidepoint(mx,my):
                self.scrub=True
                f=max(0.,min(1.,(mx-pr.x)/pr.w))
                if self.tlen>0:
                    pygame.mixer.music.set_pos(f*self.tlen)
                    self.pstart=time.time()-f*self.tlen;self.ppos=f*self.tlen
            elif tlr.collidepoint(mx,my):
                row=(my-tlr.y)//self.TH+self.scroll
                if 0<=row<len(self.tracks):
                    if row==self.cur and self.playing: self._toggle()
                    else: self._play(row)
        if event.type==pygame.MOUSEBUTTONUP and event.button==1: self.scrub=False
        if event.type==pygame.MOUSEWHEEL:
            if self._tlr().collidepoint(*pygame.mouse.get_pos()):
                self.scroll=max(0,min(len(self.tracks)-self.VT,self.scroll-event.y))
        if event.type==pygame.MOUSEMOTION and self.scrub:
            pr=self._prog(); f=max(0.,min(1.,(mx-pr.x)/pr.w))
            if self.tlen>0:
                pygame.mixer.music.set_pos(f*self.tlen)
                self.pstart=time.time()-f*self.tlen
        # (end-of-track handled at top of handle())

    def _stop(self): pygame.mixer.music.stop();self.playing=False;self.progress=0.;self.ppos=0.

    def update(self,dt_ms,now_ms):
        self.update_anim(dt_ms/1000.)
        # always keep endevent set and progress ticking, even when hidden
        pygame.mixer.music.set_endevent(pygame.USEREVENT)
        if self.playing and self.tlen>0:
            self.progress=min(1.,(time.time()-self.pstart)/self.tlen)
        if self.state not in("open","opening","closing"): return
        self.update_fx(dt_ms,now_ms)
        if self.playing:
            for i in range(len(self.bars)):
                self.bars[i]+=(self.btgt[i]-self.bars[i])*.12
                if abs(self.bars[i]-self.btgt[i])<.03: self.btgt[i]=random.uniform(.05,1.)
        else:
            for i in range(len(self.bars)): self.bars[i]+=(0.04-self.bars[i])*.05

    def draw(self,surf,dt_ms,now_ms):
        mx,my=pygame.mouse.get_pos()
        if not self.draw_frame(surf,mx,my,"MUSIC_MODULE"): return
        bx,by,bw,bh=self.x,self.y,self.W,self.H
        t_anim=ease_out(self.anim); vis_h=int(bh*t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        render_glow(surf, fLabel, "AUDIO_PLAYER", CYN_DIM,
                    (bx+26, by+STATUS_H+8), glow_radius=2, glow_alpha=30)

        tlr=self._tlr()
        pygame.draw.rect(surf,(0,7,16),tlr)
        pygame.draw.rect(surf,CYN_FAINT,tlr,1)
        for i in range(self.VT):
            ti=i+self.scroll
            if ti>=len(self.tracks): break
            ry=tlr.y+i*self.TH; tr=self.tracks[ti]; ic=ti==self.cur
            if ic: pygame.draw.rect(surf,SEL_ROW,(tlr.x+1,ry,tlr.w-2,self.TH-1))
            pygame.draw.line(surf,CYN_FAINT,(tlr.x,ry+self.TH-1),(tlr.x+tlr.w,ry+self.TH-1))
            nc=CYN if ic else CYN_DIM
            surf.blit(fLabel.render(f"{ti+1:02d}",True,nc),(tlr.x+7,ry+self.TH//2-6))
            name=tr["n"]; ns=fTrack.render(name,True,TXT if ic else CYN_DIM)
            mw=tlr.w-60
            if ns.get_width()>mw:
                while fTrack.size(name+"...")[0]>mw and name: name=name[:-1]
                ns=fTrack.render(name+"...",True,TXT if ic else CYN_DIM)
            surf.blit(ns,(tlr.x+36,ry+self.TH//2-ns.get_height()//2))
            if ic and self.playing:
                px_=tlr.x+tlr.w-18; py_=ry+self.TH//2
                pygame.draw.polygon(surf,CYN,[(px_,py_-5),(px_,py_+5),(px_+8,py_)])
        if len(self.tracks)>self.VT:
            bh_=int(tlr.h*self.VT/len(self.tracks))
            by_=tlr.y+int(tlr.h*self.scroll/len(self.tracks))
            pygame.draw.rect(surf,CYN_DIM,(tlr.x+tlr.w+2,by_,3,bh_))

        VY=tlr.y+tlr.h+8; VH=26; bw_=(bw-36)//len(self.bars)-2
        for i,v in enumerate(self.bars):
            bh_=max(2,int(v*VH)); c=(0,int(70+v*180),int(50+v*120))
            pygame.draw.rect(surf,c,(bx+18+i*(bw_+2),VY+VH-bh_,bw_,bh_))

        render_glow(surf, fLabel, f">> {self.tracks[self.cur]['n']}", CYN_MID,
                    (bx+18, VY+VH+5), glow_radius=2, glow_alpha=40)

        cs=self._ctrls()
        lbls={"prev":"PREV","play":"PAUSE" if self.playing else "PLAY","next":"NEXT",
              "loop":"LOOP*" if self.looping else "LOOP"}
        for k,btn in cs.items():
            hov=btn.collidepoint(mx,my)
            self.bt[k]=max(0.,min(1.,self.bt[k]+(9 if hov else -9)*dt_ms/1000.))
            poly_btn(surf,btn,self.bt[k],CYN,lbls[k])

        pr=self._prog()
        pygame.draw.rect(surf,CYN_FAINT,pr)
        fw=int(pr.w*self.progress)
        if fw>0: pygame.draw.rect(surf,CYN_MID,(pr.x,pr.y,fw,pr.h))
        pygame.draw.rect(surf,CYN,(pr.x+fw-2,pr.y-3,4,pr.h+6))
        if self.tlen>0:
            el=self.progress*self.tlen
            tc=fClock.render(f"{int(el)//60:02d}:{int(el)%60:02d}",True,CYN_DIM)
            tt=fClock.render(f"{int(self.tlen)//60:02d}:{int(self.tlen)%60:02d}",True,CYN_DIM)
            surf.blit(tc,(pr.x,pr.y+pr.h+4)); surf.blit(tt,(pr.x+pr.w-tt.get_width(),pr.y+pr.h+4))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  CALCULATOR
# ══════════════════════════════════════════════════════
class CalcWin(Window):
    def __init__(self):
        super().__init__("calc","CALC",SW//2-170,SH//2-220,340,440)
        self.expr=""; self.result=""; self.history=[]; self.err=False
        self.bt={i:0. for i in range(20)}
        self.grid=[
            ["C","(",")","/"],
            ["7","8","9","*"],
            ["4","5","6","-"],
            ["1","2","3","+"],
            ["00","0",".","="],
        ]

    def _eval(self):
        try:
            safe=self.expr.replace("^","**")
            r=eval(safe,{"__builtins__":{}},{"abs":abs,"round":round})
            res=str(round(r,10)).rstrip("0").rstrip(".") if "." in str(r) else str(r)
            self.history.append(f"{self.expr} = {res}")
            if len(self.history)>5: self.history.pop(0)
            self.result=res; self.expr=res; self.err=False
        except:
            self.result="ERROR"; self.err=True

    def handle(self,event,now_ms):
        # process end-of-track event even when hidden
        if event.type==pygame.USEREVENT and self.state in ("open","hidden"):
            if self.looping: self._play(self.cur)
            else: self._next()
            return
        if self.state!="open": return
        act=self.handle_base(event,now_ms)
        if act=="close": self.close()
        elif act=="minimize": self.hide()
        mx,my=pygame.mouse.get_pos()
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for ri,row in enumerate(self.grid):
                for ci,lbl in enumerate(row):
                    r=self._btn_rect(ri,ci)
                    if r.collidepoint(mx,my): self._press(lbl)
        if event.type==pygame.KEYDOWN:
            if not pygame.Rect(self.x,self.y,self.W,self.H).collidepoint(mx,my): return
            k=event.unicode
            if k in "0123456789.+-*/()": self.expr+=k;self.err=False
            elif event.key==pygame.K_RETURN: self._eval()
            elif event.key==pygame.K_BACKSPACE:
                self.expr=self.expr[:-1];self.err=False
            elif event.key==pygame.K_ESCAPE: self.expr="";self.result="";self.err=False

    def _press(self,lbl):
        if lbl=="C": self.expr="";self.result="";self.err=False
        elif lbl=="=": self._eval()
        else: self.expr+=lbl;self.err=False

    def _btn_rect(self,ri,ci):
        pad=10; bw=(self.W-pad*2)//4; bh=46
        top=self.y+STATUS_H+80
        return pygame.Rect(self.x+pad+ci*bw, top+ri*bh, bw-4, bh-4)

    def update(self,dt_ms,now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in("open","opening","closing"): return
        self.update_fx(dt_ms,now_ms)

    def draw(self,surf,dt_ms,now_ms):
        mx,my=pygame.mouse.get_pos()
        if not self.draw_frame(surf,mx,my,"CALC_MODULE"): return
        bx,by,bw,bh=self.x,self.y,self.W,self.H
        t_anim=ease_out(self.anim); vis_h=int(bh*t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        DR=pygame.Rect(bx+10,by+STATUS_H+8,bw-20,66)
        pygame.draw.rect(surf,(0,3,10),DR)
        pygame.draw.rect(surf,CYN_FAINT,DR,1)

        for i,h in enumerate(self.history[-3:]):
            hs=fStat.render(h,True,CYN_FAINT)
            surf.blit(hs,(DR.x+8,DR.y+4+i*14))

        disp_e=self.expr[-22:] if len(self.expr)>22 else self.expr
        es=fCalc.render(disp_e if disp_e else "0",True,TXT if not self.err else (200,60,40))
        surf.blit(es,(DR.x+DR.w-es.get_width()-8,DR.y+DR.h-es.get_height()-6))
        if (now_ms//600)%2==0 and not self.err:
            cx_=DR.x+DR.w-8; cy_=DR.y+DR.h-es.get_height()-4
            pygame.draw.rect(surf,CYN,(cx_,cy_,3,es.get_height()))

        for ri,row in enumerate(self.grid):
            for ci,lbl in enumerate(row):
                r=self._btn_rect(ri,ci)
                hov=r.collidepoint(mx,my)
                is_eq=(lbl=="="); is_op=(lbl in"+-*/")
                col=CYN if is_eq else (CYN_MID if is_op else CYN_DIM)
                if hov: pygame.draw.rect(surf,(0,40,30),r)
                pygame.draw.rect(surf,col,r,1)
                ls=fCalcSm.render(lbl,True,CYN if hov else col)
                surf.blit(ls,(r.x+r.w//2-ls.get_width()//2,r.y+r.h//2-ls.get_height()//2))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  IMAGE VIEWER
# ══════════════════════════════════════════════════════
class ImageWin(Window):
    DRAW_COLS=[(0,255,200),(255,80,80),(80,200,255),(255,200,0),(180,80,255),(255,255,255),(0,180,100)]
    MAX_CACHE = 6

    def __init__(self):
        super().__init__("images","IMGS",SW//2-290,SH//2-210,580,440)
        self.folder   = IMG_D
        self.imgs     = self._scan()
        self.cur      = 0
        self._cache   = {}
        self._cache_order = []
        self._fitted  = None
        self._fit_key = None
        self.bt       = {k:0. for k in("prev","next","folder","draw")}
        self.zoom     = 1.0
        self.pan_x=0; self.pan_y=0
        self.panning  = False; self.px0=0; self.py0=0
        self.draw_mode   = False
        self.draw_col_i  = 0
        self.draw_size   = 4
        self.drawing     = False
        self.last_draw   = None
        self.strokes     = []
        self._draw_surf  = None
        self._draw_dirty = True
        self._area_size  = (0,0)

    def _scan(self):
        exts=(".png",".jpg",".jpeg",".bmp",".gif",".webp")
        fs=sorted([f for f in os.listdir(self.folder) if f.lower().endswith(exts)])
        return [os.path.join(self.folder,f) for f in fs]

    def _get_img(self,path):
        if path in self._cache:
            if path in self._cache_order: self._cache_order.remove(path)
            self._cache_order.append(path)
            return self._cache[path]
        try: img=pygame.image.load(path).convert()
        except: img=None
        self._cache[path]=img
        self._cache_order.append(path)
        while len(self._cache_order)>self.MAX_CACHE:
            old=self._cache_order.pop(0)
            self._cache.pop(old,None)
        return img

    def _get_fitted(self, img, aw, ah):
        key=(id(img),round(self.zoom,2),aw,ah)
        if key==self._fit_key: return self._fitted
        iw,ih=img.get_size()
        scale=min(aw/iw,ah/ih)*self.zoom
        nw,nh=max(1,int(iw*scale)),max(1,int(ih*scale))
        self._fitted=pygame.transform.smoothscale(img,(nw,nh))
        self._fit_key=key
        return self._fitted

    def _area(self):
        return pygame.Rect(self.x+8,self.y+STATUS_H+28,self.W-16,self.H-STATUS_H-66)

    def _brs(self):
        by_=self.y+self.H-46
        return pygame.Rect(self.x+14,by_+9,62,24),pygame.Rect(self.x+self.W-76,by_+9,62,24)

    def _toolbar(self):
        ty=self.y+STATUS_H+6; tx=self.x+self.W-260
        return {
            "folder": pygame.Rect(tx,    ty,72,18),
            "draw":   pygame.Rect(tx+80, ty,62,18),
        }

    def _change_folder(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root=tk.Tk(); root.withdraw(); root.attributes("-topmost",True)
            folder=filedialog.askdirectory(initialdir=self.folder,title="Select image folder")
            root.destroy()
            if folder:
                self.folder=folder; self.imgs=self._scan()
                self.cur=0; self._cache={}; self._cache_order=[]
                self._fitted=None; self._fit_key=None
                self.zoom=1.; self.pan_x=self.pan_y=0
                self.strokes=[]; self._draw_surf=None; self._draw_dirty=True
        except Exception as ex:
            print(f"[IMGS] folder picker error: {ex}")

    def _ensure_draw_surf(self, aw, ah):
        if self._draw_surf is None or self._area_size!=(aw,ah):
            self._draw_surf=pygame.Surface((aw,ah),pygame.SRCALPHA)
            self._draw_surf.fill((0,0,0,0))
            self._area_size=(aw,ah)
            self._draw_dirty=True
        if self._draw_dirty:
            self._draw_surf.fill((0,0,0,0))
            for i in range(1,len(self.strokes)):
                p0=self.strokes[i-1]; p1=self.strokes[i]
                if p0 and p1:
                    pygame.draw.line(self._draw_surf,p1[2],(p0[0],p0[1]),(p1[0],p1[1]),p1[3])
                    pygame.draw.circle(self._draw_surf,p1[2],(p1[0],p1[1]),p1[3]//2)
            self._draw_dirty=False

    def handle(self,event,now_ms):
        # process end-of-track event even when hidden
        if event.type==pygame.USEREVENT and self.state in ("open","hidden"):
            if self.looping: self._play(self.cur)
            else: self._next()
            return
        if self.state!="open": return
        act=self.handle_base(event,now_ms)
        if act=="close": self.close()
        elif act=="minimize": self.hide()
        mx,my=pygame.mouse.get_pos()
        lb,nb=self._brs(); area=self._area(); tb=self._toolbar()
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if tb["folder"].collidepoint(mx,my): self._change_folder()
            elif tb["draw"].collidepoint(mx,my):
                self.draw_mode=not self.draw_mode
                if not self.draw_mode: self.drawing=False
            elif lb.collidepoint(mx,my):
                self.cur=max(0,self.cur-1); self.zoom=1.; self.pan_x=self.pan_y=0
                self.strokes=[]; self._draw_surf=None; self._draw_dirty=True
            elif nb.collidepoint(mx,my):
                self.cur=min(len(self.imgs)-1,self.cur+1); self.zoom=1.; self.pan_x=self.pan_y=0
                self.strokes=[]; self._draw_surf=None; self._draw_dirty=True
            elif area.collidepoint(mx,my):
                if self.draw_mode:
                    self.drawing=True
                    lx,ly=mx-area.x,my-area.y
                    self.strokes.append((lx,ly,self.DRAW_COLS[self.draw_col_i],self.draw_size))
                    self.last_draw=(lx,ly)
                    self._draw_dirty=True
                else:
                    self.panning=True; self.px0=mx-self.pan_x; self.py0=my-self.pan_y
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==3 and self.draw_mode:
            self.draw_col_i=(self.draw_col_i+1)%len(self.DRAW_COLS)
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self.panning=False
            if self.drawing: self.drawing=False; self.strokes.append(None)
        if event.type==pygame.MOUSEMOTION:
            if self.panning: self.pan_x=mx-self.px0; self.pan_y=my-self.py0
            if self.drawing and area.collidepoint(mx,my):
                lx,ly=mx-area.x,my-area.y
                self.strokes.append((lx,ly,self.DRAW_COLS[self.draw_col_i],self.draw_size))
                self._draw_dirty=True
        if event.type==pygame.MOUSEWHEEL:
            if area.collidepoint(*pygame.mouse.get_pos()):
                if self.draw_mode:
                    self.draw_size=max(1,min(30,self.draw_size+event.y))
                else:
                    self.zoom=max(0.15,min(10.,self.zoom+event.y*0.15))
        if event.type==pygame.KEYDOWN and pygame.Rect(self.x,self.y,self.W,self.H).collidepoint(mx,my):
            if event.key==pygame.K_c and self.draw_mode:
                self.strokes=[]; self._draw_surf=None; self._draw_dirty=True
            elif event.key==pygame.K_z and self.draw_mode and len(self.strokes)>0:
                while self.strokes and self.strokes[-1] is not None: self.strokes.pop()
                if self.strokes: self.strokes.pop()
                self._draw_dirty=True

    def update(self,dt_ms,now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in("open","opening","closing"): return
        self.update_fx(dt_ms,now_ms)

    def draw(self,surf,dt_ms,now_ms):
        mx,my=pygame.mouse.get_pos()
        if not self.draw_frame(surf,mx,my,"IMAGE_MODULE"): return
        bx,by,bw,bh=self.x,self.y,self.W,self.H
        t_anim=ease_out(self.anim); vis_h=int(bh*t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        area=self._area()
        pygame.draw.rect(surf,(0,4,10),area)
        pygame.draw.rect(surf,CYN_FAINT,area,1)

        tb=self._toolbar()
        for k,r in tb.items():
            hov=r.collidepoint(mx,my)
            active=(k=="draw" and self.draw_mode)
            col=CYN if (hov or active) else CYN_DIM
            pygame.draw.rect(surf,(0,35,22) if active else (0,0,0),r)
            pygame.draw.rect(surf,col,r,1)
            lbl={"folder":"FOLDER","draw":"DRAW*" if self.draw_mode else "DRAW"}[k]
            ls=fStat.render(lbl,True,col)
            surf.blit(ls,(r.x+r.w//2-ls.get_width()//2,r.y+r.h//2-ls.get_height()//2))

        surf.set_clip(area)
        if not self.imgs:
            msg=fLabel.render("NO IMAGES — pick a folder or add files to images/",True,CYN_DIM)
            surf.blit(msg,(area.x+area.w//2-msg.get_width()//2,area.y+area.h//2-8))
        else:
            path=self.imgs[self.cur]
            img=self._get_img(path)
            if img:
                fitted=self._get_fitted(img,area.w-4,area.h-4)
                ix=area.x+(area.w-fitted.get_width())//2+self.pan_x
                iy=area.y+(area.h-fitted.get_height())//2+self.pan_y
                surf.blit(fitted,(ix,iy))
            self._ensure_draw_surf(area.w,area.h)
            surf.blit(self._draw_surf,(area.x,area.y))

            surf.set_clip(pygame.Rect(bx,by,bw,vis_h))
            fn=fStat.render(os.path.basename(path),True,CYN_DIM)
            surf.blit(fn,(area.x+4,area.y+area.h-fn.get_height()-4))
            if self.draw_mode:
                col_dot=self.DRAW_COLS[self.draw_col_i]
                pygame.draw.circle(surf,col_dot,(area.x+area.w-20,area.y+area.h-10),5)
                dsz=fStat.render(f"sz:{self.draw_size}  C=clear  Z=undo  RMB=colour",True,CYN_FAINT)
                surf.blit(dsz,(area.x+4,area.y+area.h-dsz.get_height()-16))
            else:
                zs=fStat.render(f"zoom:{self.zoom:.1f}x  scroll=zoom  drag=pan",True,CYN_FAINT)
                surf.blit(zs,(area.x+area.w-zs.get_width()-4,area.y+area.h-zs.get_height()-4))
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        if self.draw_mode and area.collidepoint(mx,my):
            pygame.draw.circle(surf,self.DRAW_COLS[self.draw_col_i],(mx,my),self.draw_size//2,1)

        BAR=by+bh-46
        pygame.draw.line(surf,CYN_FAINT,(bx,BAR),(bx+bw,BAR))
        lb,nb=self._brs()
        for key,btn,en in[("prev",lb,self.cur>0 and not self.draw_mode),
                          ("next",nb,self.cur<len(self.imgs)-1 and not self.draw_mode)]:
            hov=btn.collidepoint(mx,my) and en
            self.bt[key]=max(0.,min(1.,self.bt[key]+(9 if hov else -9)*dt_ms/1000.))
            col=CYN if en else CYN_FAINT
            poly_btn(surf,btn,self.bt[key],col,"PREV" if key=="prev" else "NEXT")

        if self.imgs:
            ctr=fLabel.render(f"{self.cur+1}/{len(self.imgs)}  [{os.path.basename(self.folder)}]",True,CYN_DIM)
            surf.blit(ctr,(bx+bw//2-ctr.get_width()//2,BAR+12))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  PAINT WINDOW
# ══════════════════════════════════════════════════════
class PaintWin(Window):
    PALETTE = [
        (0,255,200),(0,160,120),(0,80,60),        # teal spectrum
        (255,255,255),(180,180,180),(80,80,80),    # grays
        (255,80,80),(255,160,0),(255,220,0),       # warm
        (80,160,255),(120,80,255),(200,60,200),    # cool
        (0,200,80),(120,255,80),(0,0,0),           # green + black
    ]
    TOOLS = ["PEN","LINE","RECT","CIRCLE","FILL","ERASER"]

    def __init__(self):
        super().__init__("paint","PAINT", SW//2-320, SH//2-240, 640, 480)
        self.tool = "PEN"
        self.col_idx = 0
        self.brush_size = 4
        self.drawing = False
        self.start_pos = None
        self.canvas = None           # created on first draw
        self.canvas_size = (0, 0)
        self.strokes = []            # for PEN undo
        self.preview_surf = None     # temp surface for shapes
        self.undo_stack = []         # list of canvas snapshots
        self.MAX_UNDO = 20

    def _canvas_rect(self):
        PAL_H = 28
        TOOL_W = 70
        return pygame.Rect(
            self.x + 8 + TOOL_W,
            self.y + STATUS_H + PAL_H + 10,
            self.W - 16 - TOOL_W,
            self.H - STATUS_H - PAL_H - 54
        )

    def _ensure_canvas(self):
        cr = self._canvas_rect()
        w, h = cr.w, cr.h
        if self.canvas is None or self.canvas_size != (w, h):
            new = pygame.Surface((w, h))
            new.fill((0, 6, 18))
            if self.canvas is not None:
                ow, oh = self.canvas_size
                new.blit(self.canvas, (0, 0))
            self.canvas = new
            self.canvas_size = (w, h)
            self.preview_surf = pygame.Surface((w, h), pygame.SRCALPHA)

    def _push_undo(self):
        snap = self.canvas.copy()
        self.undo_stack.append(snap)
        if len(self.undo_stack) > self.MAX_UNDO:
            self.undo_stack.pop(0)

    def _flood_fill(self, surf, x, y, new_col):
        """Simple iterative flood fill."""
        if x < 0 or y < 0 or x >= surf.get_width() or y >= surf.get_height():
            return
        target = surf.get_at((x, y))[:3]
        if target == new_col[:3]:
            return
        stack = [(x, y)]
        visited = set()
        w, h = surf.get_width(), surf.get_height()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited: continue
            if cx < 0 or cy < 0 or cx >= w or cy >= h: continue
            if surf.get_at((cx, cy))[:3] != target: continue
            visited.add((cx, cy))
            surf.set_at((cx, cy), new_col)
            stack.extend([(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)])

    def _palette_rects(self):
        PAL_H = 28; TOOL_W = 70
        px = self.x + 8 + TOOL_W
        py = self.y + STATUS_H + 6
        sw = (self.W - 16 - TOOL_W) // len(self.PALETTE)
        return [pygame.Rect(px + i*sw, py, sw-2, PAL_H-4) for i in range(len(self.PALETTE))]

    def _tool_rects(self):
        tx = self.x + 8
        ty = self.y + STATUS_H + 10
        return {t: pygame.Rect(tx, ty + i*28, 64, 24) for i, t in enumerate(self.TOOLS)}

    def _brush_rects(self):
        # size buttons bottom left of canvas
        cr = self._canvas_rect()
        by = self.y + self.H - 46
        return [pygame.Rect(self.x + 8 + 70 + i*28, by + 8, 24, 22) for i in range(5)]

    def handle(self, event, now_ms):
        if self.state != "open": return
        act = self.handle_base(event, now_ms)
        if act == "close": self.close()
        elif act == "minimize": self.hide()
        mx, my = pygame.mouse.get_pos()
        self._ensure_canvas()
        cr = self._canvas_rect()

        # palette click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._palette_rects()):
                if r.collidepoint(mx, my):
                    self.col_idx = i; return

            # tool click
            for t, r in self._tool_rects().items():
                if r.collidepoint(mx, my):
                    self.tool = t; return

            # brush size
            sizes = [1, 2, 4, 8, 16]
            for i, r in enumerate(self._brush_rects()):
                if r.collidepoint(mx, my):
                    self.brush_size = sizes[i]; return

            # canvas interaction
            if cr.collidepoint(mx, my):
                lx, ly = mx - cr.x, my - cr.y
                col = self.PALETTE[self.col_idx]
                if self.tool == "FILL":
                    self._push_undo()
                    self._flood_fill(self.canvas, lx, ly, col)
                elif self.tool == "ERASER":
                    self._push_undo()
                    self.drawing = True
                    pygame.draw.circle(self.canvas, (0,6,18), (lx,ly), self.brush_size)
                elif self.tool == "PEN":
                    self._push_undo()
                    self.drawing = True
                    pygame.draw.circle(self.canvas, col, (lx,ly), max(1,self.brush_size//2))
                else:  # LINE, RECT, CIRCLE
                    self._push_undo()
                    self.drawing = True
                    self.start_pos = (lx, ly)
                    self.preview_surf.fill((0,0,0,0))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # right-click: pick colour from canvas
            if cr.collidepoint(mx, my):
                lx, ly = mx-cr.x, my-cr.y
                if 0 <= lx < self.canvas.get_width() and 0 <= ly < self.canvas.get_height():
                    picked = self.canvas.get_at((lx, ly))[:3]
                    # find nearest in palette
                    best = min(range(len(self.PALETTE)), key=lambda i:
                        sum((self.PALETTE[i][j]-picked[j])**2 for j in range(3)))
                    self.col_idx = best

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drawing and self.start_pos and self.tool in ("LINE","RECT","CIRCLE"):
                lx, ly = mx-cr.x, my-cr.y
                col = self.PALETTE[self.col_idx]
                x0,y0 = self.start_pos
                if self.tool == "LINE":
                    pygame.draw.line(self.canvas, col, (x0,y0), (lx,ly), self.brush_size)
                elif self.tool == "RECT":
                    r = pygame.Rect(min(x0,lx),min(y0,ly),abs(lx-x0),abs(ly-y0))
                    pygame.draw.rect(self.canvas, col, r, self.brush_size)
                elif self.tool == "CIRCLE":
                    rad = int(math.dist((x0,y0),(lx,ly)))
                    if rad > 0:
                        pygame.draw.circle(self.canvas, col, (x0,y0), rad, self.brush_size)
                self.preview_surf.fill((0,0,0,0))
            self.drawing = False
            self.start_pos = None

        if event.type == pygame.MOUSEMOTION:
            if self.drawing and cr.collidepoint(mx, my):
                lx, ly = mx-cr.x, my-cr.y
                col = self.PALETTE[self.col_idx]
                if self.tool == "PEN":
                    pygame.draw.circle(self.canvas, col, (lx,ly), max(1,self.brush_size//2))
                    # connect to last point for smooth stroke
                    if self.start_pos:
                        pygame.draw.line(self.canvas, col, self.start_pos, (lx,ly), max(1,self.brush_size//2)*2)
                    self.start_pos = (lx,ly)
                elif self.tool == "ERASER":
                    if self.start_pos:
                        pygame.draw.line(self.canvas, (0,6,18), self.start_pos, (lx,ly), self.brush_size*2)
                    pygame.draw.circle(self.canvas, (0,6,18), (lx,ly), self.brush_size)
                    self.start_pos = (lx,ly)
                elif self.start_pos and self.tool in ("LINE","RECT","CIRCLE"):
                    x0,y0 = self.start_pos
                    self.preview_surf.fill((0,0,0,0))
                    if self.tool == "LINE":
                        pygame.draw.line(self.preview_surf, (*col,200), (x0,y0),(lx,ly), self.brush_size)
                    elif self.tool == "RECT":
                        r = pygame.Rect(min(x0,lx),min(y0,ly),abs(lx-x0),abs(ly-y0))
                        pygame.draw.rect(self.preview_surf, (*col,200), r, self.brush_size)
                    elif self.tool == "CIRCLE":
                        rad = int(math.dist((x0,y0),(lx,ly)))
                        if rad > 0:
                            pygame.draw.circle(self.preview_surf, (*col,200), (x0,y0), rad, self.brush_size)

        if event.type == pygame.MOUSEWHEEL:
            if cr.collidepoint(*pygame.mouse.get_pos()):
                self.brush_size = max(1, min(40, self.brush_size + event.y))

        if event.type == pygame.KEYDOWN and pygame.Rect(self.x,self.y,self.W,self.H).collidepoint(mx,my):
            if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                if self.undo_stack:
                    self.canvas = self.undo_stack.pop()
            elif event.key == pygame.K_DELETE or event.key == pygame.K_c:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self._push_undo()
                    self.canvas.fill((0,6,18))

    def update(self, dt_ms, now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in ("open","opening","closing"): return
        self.update_fx(dt_ms, now_ms)

    def draw(self, surf, dt_ms, now_ms):
        mx, my = pygame.mouse.get_pos()
        if not self.draw_frame(surf, mx, my, "PAINT_MODULE"): return
        self._ensure_canvas()
        bx,by,bw,bh = self.x,self.y,self.W,self.H
        t_anim = ease_out(self.anim)
        vis_h = int(bh * t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))
        # _ensure_canvas already called above
        cr = self._canvas_rect()

        # canvas bg + border
        pygame.draw.rect(surf, (0,6,18), cr)
        pygame.draw.rect(surf, CYN_FAINT, cr, 1)
        surf.blit(self.canvas, (cr.x, cr.y))
        if self.preview_surf:
            surf.blit(self.preview_surf, (cr.x, cr.y))

        # scan line on canvas
        sy = cr.y + int(self.scan_y * cr.h)
        pygame.draw.line(surf,(0,40,30),(cr.x,sy),(cr.x+cr.w,sy))

        # palette row
        for i, r in enumerate(self._palette_rects()):
            col = self.PALETTE[i]
            pygame.draw.rect(surf, col, r)
            if i == self.col_idx:
                pygame.draw.rect(surf, CYN, r, 2)
                # glow selected
                g = pygame.Surface((r.w+6,r.h+6), pygame.SRCALPHA)
                pygame.draw.rect(g, (col[0],col[1],col[2],60), (0,0,r.w+6,r.h+6), 2)
                surf.blit(g, (r.x-3,r.y-3))
            else:
                pygame.draw.rect(surf, CYN_FAINT, r, 1)

        # tool buttons
        for t, r in self._tool_rects().items():
            active = (t == self.tool)
            hov = r.collidepoint(mx, my)
            col = CYN if active else (CYN_MID if hov else CYN_DIM)
            pygame.draw.rect(surf, (0,30,20) if active else (0,0,0), r)
            pygame.draw.rect(surf, col, r, 1)
            if active:
                g = pygame.Surface((r.w+4,r.h+4), pygame.SRCALPHA)
                pygame.draw.rect(g, (col[0],col[1],col[2],50),(0,0,r.w+4,r.h+4),1)
                surf.blit(g, (r.x-2,r.y-2))
            render_glow(surf, fStat, t, col,
                        (r.x + r.w//2 - fStat.size(t)[0]//2, r.y + r.h//2 - fStat.get_height()//2),
                        glow_radius=2, glow_alpha=35 if active else 12)

        # brush size buttons
        sizes = [1,2,4,8,16]
        for i, (r, sz) in enumerate(zip(self._brush_rects(), sizes)):
            active = (sz == self.brush_size)
            hov = r.collidepoint(mx, my)
            col = CYN if active else (CYN_MID if hov else CYN_DIM)
            pygame.draw.rect(surf, (0,20,14) if active else (0,0,0), r)
            pygame.draw.rect(surf, col, r, 1)
            dot_r = max(1, sz//2)
            pygame.draw.circle(surf, col, (r.centerx, r.centery), min(dot_r, r.h//2-2))

        # brush size label
        sz_lbl = fStat.render(f"SZ:{self.brush_size}", True, CYN_DIM)
        surf.blit(sz_lbl, (self.x+8+70+5*28+4, by+self.H-46+12))

        # cursor preview dot on canvas
        if cr.collidepoint(mx, my):
            col = self.PALETTE[self.col_idx]
            if self.tool == "ERASER":
                pygame.draw.circle(surf, CYN_DIM, (mx,my), self.brush_size, 1)
            else:
                pygame.draw.circle(surf, col, (mx,my), max(1,self.brush_size//2), 1)

        # bottom hint
        hints = fStat.render("Ctrl+Z=undo  Ctrl+C=clear  RMB=pick colour  scroll=brush size", True, CYN_FAINT)
        surf.blit(hints, (cr.x, by+bh-20))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  TERMINAL WINDOW
# ══════════════════════════════════════════════════════
class TermWin(Window):
    LINE_H = 18
    MAX_LINES = 500
    PROMPT = "GLITCH_OS> "

    def __init__(self):
        super().__init__("term","TERM", SW//2-300, SH//2-200, 600, 400)
        self.lines = [
            ("sys", "╔══════════════════════════════════════════╗"),
            ("sys", "║  GLITCH_OS  TERMINAL  v2.0  //  READY    ║"),
            ("sys", "╚══════════════════════════════════════════╝"),
            ("sys", "  Type 'help' for commands. Tab=autocomplete. ↑↓=history."),
            ("sys", ""),
        ]
        self.input_buf = ""
        self.history = []      # command history
        self.hist_idx = -1
        self.scroll = 0
        self.repeat_key = None; self.repeat_t = 0; self.repeat_d = 0
        self.cwd = BASE
        self._thread = None
        self._output_buf = []   # thread-safe output from subprocess
        self._lock = threading.Lock()

    def _add_line(self, kind, text):
        """kind: 'sys'|'in'|'out'|'err'"""
        for ln in (text.split("\n") if "\n" in text else [text]):
            self.lines.append((kind, ln))
        if len(self.lines) > self.MAX_LINES:
            self.lines = self.lines[-self.MAX_LINES:]
        # auto-scroll to bottom
        vis = self._visible_lines()
        self.scroll = max(0, len(self.lines) - vis)

    def _run_cmd(self, cmd):
        """Execute a command and collect output."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=self.cwd, timeout=10
            )
            if result.stdout:
                with self._lock:
                    self._output_buf.append(("out", result.stdout.rstrip()))
            if result.stderr:
                with self._lock:
                    self._output_buf.append(("err", result.stderr.rstrip()))
        except subprocess.TimeoutExpired:
            with self._lock:
                self._output_buf.append(("err", "ERROR: command timed out (10s)"))
        except Exception as ex:
            with self._lock:
                self._output_buf.append(("err", f"ERROR: {ex}"))

    def _built_in(self, cmd):
        """Handle built-in commands. Returns True if handled."""
        parts = cmd.strip().split()
        if not parts: return True
        verb = parts[0].lower()
        args = parts[1:]
        raw_after = cmd.strip()[len(verb):].strip()

        # ── HELP ─────────────────────────────────────
        if verb == "help":
            cats = [
                ("FILESYSTEM",  ["ls [path]","dir [path]","cd <dir>","pwd","cat <file>",
                                  "write <file> <text>","mkdir <dir>","rm <file>","cp <src> <dst>",
                                  "mv <src> <dst>","find <name>","tree","size <file>"]),
                ("SYSTEM",      ["sysinfo","neofetch","ps","kill <pid>","env","uptime",
                                  "diskinfo","meminfo","netinfo","cpu"]),
                ("APPS",        ["open <app>","close <app>","apps","minimize <app>","restart"]),
                ("UTILS",       ["echo <text>","date","clock","calc <expr>","base64 <text>",
                                  "hex <text>","rot13 <text>","rev <text>","wc <text>",
                                  "upper <text>","lower <text>","len <text>","morse <text>",
                                  "flip <text>","sort <words>","shuffle <words>","random [n]",
                                  "roll [NdN]","coin","uuid","hash <text>"]),
                ("FUN",         ["matrix","glitch","banner <text>","ascii <char>","rain",
                                  "color <r> <g> <b>","pulse","starfield","scanline"]),
                ("TERMINAL",    ["clear / cls","history","repeat <n> <cmd>","alias <n>=<cmd>",
                                  "unalias <name>","aliases","exit / quit"]),
            ]
            self._add_line("sys", "╔══════════════════════════════════════════╗")
            self._add_line("sys", "║       GLITCH_OS  TERMINAL  v2.0          ║")
            self._add_line("sys", "╚══════════════════════════════════════════╝")
            for cat, cmds in cats:
                self._add_line("sys", f"── {cat} " + "─"*(36-len(cat)))
                for i in range(0, len(cmds), 2):
                    pair = f"  {cmds[i]:<22}" + (f"  {cmds[i+1]}" if i+1<len(cmds) else "")
                    self._add_line("out", pair)
            self._add_line("sys", "──────────────────────────────────────────")
            return True

        # ── FILESYSTEM ───────────────────────────────
        if verb in ("clear","cls"):
            self.lines = []; self.scroll = 0
            return True

        if verb == "pwd":
            self._add_line("out", self.cwd); return True

        if verb == "cd":
            target = args[0] if args else "~"
            if target == "~": target = BASE
            new = os.path.abspath(os.path.join(self.cwd, target))
            if os.path.isdir(new):
                self.cwd = new
                self._add_line("sys", f"→ {self.cwd}")
            else:
                self._add_line("err", f"cd: not a directory: {target}")
            return True

        if verb in ("ls","dir"):
            path = os.path.join(self.cwd, args[0]) if args else self.cwd
            try:
                entries = sorted(os.listdir(path))
                dirs = [e for e in entries if os.path.isdir(os.path.join(path,e))]
                files = [e for e in entries if not os.path.isdir(os.path.join(path,e))]
                for d in dirs: self._add_line("sys", f"  📁 {d}/")
                for f in files:
                    sz = os.path.getsize(os.path.join(path,f))
                    self._add_line("out", f"  📄 {f:<30} {sz:>8} B")
                self._add_line("sys", f"  {len(dirs)} dirs, {len(files)} files")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "cat":
            if not args: self._add_line("err", "usage: cat <file>"); return True
            fp = os.path.join(self.cwd, args[0])
            try:
                with open(fp) as fh:
                    for line in fh.read().splitlines()[:80]:
                        self._add_line("out", line)
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "write":
            if len(args) < 2: self._add_line("err", "usage: write <file> <text>"); return True
            fp = os.path.join(self.cwd, args[0])
            try:
                with open(fp, "a") as fh: fh.write(" ".join(args[1:]) + "\n")
                self._add_line("sys", f"written → {fp}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "mkdir":
            if not args: self._add_line("err", "usage: mkdir <dir>"); return True
            try:
                os.makedirs(os.path.join(self.cwd, args[0]), exist_ok=True)
                self._add_line("sys", f"created: {args[0]}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "rm":
            if not args: self._add_line("err", "usage: rm <file>"); return True
            fp = os.path.join(self.cwd, args[0])
            try:
                os.remove(fp); self._add_line("sys", f"deleted: {args[0]}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "cp":
            if len(args) < 2: self._add_line("err", "usage: cp <src> <dst>"); return True
            import shutil
            try:
                shutil.copy2(os.path.join(self.cwd,args[0]), os.path.join(self.cwd,args[1]))
                self._add_line("sys", f"copied {args[0]} → {args[1]}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "mv":
            if len(args) < 2: self._add_line("err", "usage: mv <src> <dst>"); return True
            import shutil
            try:
                shutil.move(os.path.join(self.cwd,args[0]), os.path.join(self.cwd,args[1]))
                self._add_line("sys", f"moved {args[0]} → {args[1]}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "find":
            pat = args[0] if args else ""
            matches = []
            for root,dirs,files in os.walk(self.cwd):
                for f in files+dirs:
                    if pat.lower() in f.lower():
                        rel = os.path.relpath(os.path.join(root,f), self.cwd)
                        matches.append(rel)
                if len(matches) > 60: break
            for m in matches[:60]: self._add_line("out", f"  {m}")
            self._add_line("sys", f"{len(matches)} match(es)")
            return True

        if verb == "tree":
            def _tree(path, prefix="", depth=0):
                if depth > 3: return
                try:
                    entries = sorted(os.listdir(path))
                    for i,e in enumerate(entries):
                        last = i==len(entries)-1
                        self._add_line("out", prefix + ("└─ " if last else "├─ ") + e)
                        full = os.path.join(path,e)
                        if os.path.isdir(full):
                            _tree(full, prefix+("   " if last else "│  "), depth+1)
                except: pass
            self._add_line("sys", self.cwd)
            _tree(self.cwd)
            return True

        if verb == "size":
            if not args: self._add_line("err","usage: size <file>"); return True
            fp = os.path.join(self.cwd, args[0])
            try:
                sz = os.path.getsize(fp)
                self._add_line("out", f"{args[0]}: {sz} B  ({sz/1024:.1f} KB)")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        # ── SYSTEM ───────────────────────────────────
        if verb == "date":
            self._add_line("out", time.strftime("%A %d %B %Y  %H:%M:%S")); return True

        if verb == "clock":
            self._add_line("sys", "  " + time.strftime("┌─────────────────┐"))
            self._add_line("sys", "  " + time.strftime("│    %H:%M:%S     │"))
            self._add_line("sys", "  " + time.strftime("│  %d/%m/%Y       │"))
            self._add_line("sys", "  " + "└─────────────────┘")
            return True

        if verb in ("sysinfo","neofetch"):
            import platform
            self._add_line("sys",  "  ╔═══════════════════════════════╗")
            self._add_line("sys",  "  ║   G L I T C H _ O S  v 4 . 1  ║")
            self._add_line("sys",  "  ╚═══════════════════════════════╝")
            self._add_line("out",  f"  OS       : {platform.system()} {platform.release()}")
            self._add_line("out",  f"  Node     : {platform.node()}")
            self._add_line("out",  f"  Machine  : {platform.machine()} {platform.processor()[:20]}")
            self._add_line("out",  f"  Python   : {platform.python_version()}")
            self._add_line("out",  f"  Screen   : {SW} × {SH}")
            self._add_line("out",  f"  CWD      : {self.cwd}")
            self._add_line("out",  f"  Uptime   : {int(time.time()-_BOOT_T)//3600:02d}h {(int(time.time()-_BOOT_T)%3600)//60:02d}m")
            try:
                import psutil
                mem = psutil.virtual_memory()
                self._add_line("out", f"  RAM      : {mem.used//1024//1024} MB / {mem.total//1024//1024} MB ({mem.percent:.0f}%)")
                self._add_line("out", f"  CPU      : {psutil.cpu_percent(interval=0.1):.1f}%")
            except ImportError:
                self._add_line("out", "  RAM/CPU  : install psutil for live stats")
            self._add_line("sys",  "  ────────────────────────────────")
            return True

        if verb == "uptime":
            elapsed = int(time.time() - _BOOT_T)
            h,m,s = elapsed//3600, (elapsed%3600)//60, elapsed%60
            self._add_line("out", f"uptime: {h:02d}:{m:02d}:{s:02d}")
            return True

        if verb == "ps":
            try:
                import psutil
                self._add_line("sys", f"  {'PID':>7}  {'NAME':<25}  {'CPU%':>5}  {'MEM%':>5}")
                self._add_line("sys", "  " + "─"*48)
                procs = sorted(psutil.process_iter(['pid','name','cpu_percent','memory_percent']),
                               key=lambda p: p.info['cpu_percent'] or 0, reverse=True)
                for p in procs[:18]:
                    self._add_line("out",
                        f"  {p.info['pid']:>7}  {(p.info['name'] or '?')[:24]:<25}"
                        f"  {p.info['cpu_percent'] or 0:>5.1f}"
                        f"  {p.info['memory_percent'] or 0:>5.1f}")
            except ImportError:
                self._add_line("err", "install psutil:  pip install psutil")
            return True

        if verb == "kill":
            if not args: self._add_line("err","usage: kill <pid>"); return True
            try:
                import psutil
                p = psutil.Process(int(args[0]))
                name = p.name()
                p.terminate()
                self._add_line("sys", f"sent SIGTERM to {name} (pid {args[0]})")
            except ImportError:
                self._add_line("err","install psutil")
            except Exception as ex:
                self._add_line("err", str(ex))
            return True

        if verb == "env":
            for k,v in sorted(os.environ.items()):
                self._add_line("out", f"  {k}={v[:60]}")
            return True

        if verb == "diskinfo":
            import shutil
            try:
                total, used, free = shutil.disk_usage(self.cwd)
                bar_len = 28
                filled = int(bar_len * used / total)
                bar = "█"*filled + "░"*(bar_len-filled)
                self._add_line("sys", f"  Disk @ {self.cwd}")
                self._add_line("out", f"  [{bar}]")
                self._add_line("out", f"  Used  : {used//1024//1024//1024:.1f} GB")
                self._add_line("out", f"  Free  : {free//1024//1024//1024:.1f} GB")
                self._add_line("out", f"  Total : {total//1024//1024//1024:.1f} GB")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "meminfo":
            try:
                import psutil
                mem = psutil.virtual_memory()
                bar_len = 28
                filled = int(bar_len * mem.percent / 100)
                bar = "█"*filled + "░"*(bar_len-filled)
                self._add_line("sys", "  Memory")
                self._add_line("out", f"  [{bar}] {mem.percent:.1f}%")
                self._add_line("out", f"  Used  : {mem.used//1024//1024} MB")
                self._add_line("out", f"  Avail : {mem.available//1024//1024} MB")
                self._add_line("out", f"  Total : {mem.total//1024//1024} MB")
            except ImportError: self._add_line("err","install psutil")
            return True

        if verb == "cpu":
            try:
                import psutil
                p = psutil.cpu_percent(percpu=True, interval=0.1)
                for i,c in enumerate(p):
                    filled = int(20*c/100)
                    bar = "█"*filled + "░"*(20-filled)
                    self._add_line("out", f"  CPU{i} [{bar}] {c:.1f}%")
            except ImportError: self._add_line("err","install psutil")
            return True

        if verb == "netinfo":
            try:
                import socket
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                self._add_line("out", f"  Hostname : {hostname}")
                self._add_line("out", f"  Local IP : {ip}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        # ── APPS ─────────────────────────────────────
        if verb == "apps":
            self._add_line("sys", "  ── RUNNING APPS ──────────────────")
            for w in WINS:
                status = {"open":"● OPEN","hidden":"○ HIDDEN","closed":"  CLOSED",
                          "opening":"↑ OPENING","closing":"↓ CLOSING"}.get(w.state,"?")
                self._add_line("out", f"  {w.wid:<10} {status}")
            return True

        if verb == "open":
            mapping = {"log":log_win,"music":music_win,"calc":calc_win,
                       "images":img_win,"paint":paint_win,"term":term_win}
            if not args:
                self._add_line("sys", "  apps: " + " | ".join(mapping.keys())); return True
            t = args[0].lower()
            if t in mapping:
                w = mapping[t]
                if w.state in ("closed","closing"): w.open()
                else: w.show()
                self._add_line("sys", f"↑ opening {t}")
            else: self._add_line("err", f"unknown app: {t}")
            return True

        if verb == "close":
            mapping = {"log":log_win,"music":music_win,"calc":calc_win,
                       "images":img_win,"paint":paint_win,"term":term_win}
            if not args: self._add_line("err","usage: close <app>"); return True
            t = args[0].lower()
            if t in mapping: mapping[t].close(); self._add_line("sys", f"↓ closed {t}")
            else: self._add_line("err", f"unknown app: {t}")
            return True

        if verb == "minimize":
            mapping = {"log":log_win,"music":music_win,"calc":calc_win,
                       "images":img_win,"paint":paint_win,"term":term_win}
            if not args: self._add_line("err","usage: minimize <app>"); return True
            t = args[0].lower()
            if t in mapping: mapping[t].hide(); self._add_line("sys", f"_ minimized {t}")
            else: self._add_line("err", f"unknown app: {t}")
            return True

        if verb == "restart":
            self._add_line("sys", "restarting GLITCH_OS...")
            pygame.time.delay(400)
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True

        # ── UTILS ────────────────────────────────────
        if verb == "echo":
            self._add_line("out", raw_after); return True

        if verb == "calc":
            if not args: self._add_line("err","usage: calc <expr>"); return True
            try:
                r = eval(" ".join(args), {"__builtins__":{}}, {"abs":abs,"round":round,"sqrt":math.sqrt,"pi":math.pi,"e":math.e,"sin":math.sin,"cos":math.cos,"tan":math.tan,"log":math.log})
                self._add_line("out", f"  = {r}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "base64":
            import base64 as _b64
            txt = raw_after
            try:
                enc = _b64.b64encode(txt.encode()).decode()
                self._add_line("out", f"  {enc}")
            except Exception as ex: self._add_line("err", str(ex))
            return True

        if verb == "hex":
            txt = raw_after
            self._add_line("out", "  " + " ".join(f"{ord(c):02X}" for c in txt))
            return True

        if verb == "rot13":
            import codecs
            self._add_line("out", "  " + codecs.encode(raw_after, "rot_13"))
            return True

        if verb == "rev":
            self._add_line("out", "  " + raw_after[::-1]); return True

        if verb == "wc":
            words = raw_after.split()
            self._add_line("out", f"  chars:{len(raw_after)}  words:{len(words)}")
            return True

        if verb == "upper":
            self._add_line("out", "  " + raw_after.upper()); return True

        if verb == "lower":
            self._add_line("out", "  " + raw_after.lower()); return True

        if verb == "len":
            self._add_line("out", f"  {len(raw_after)} chars"); return True

        if verb == "morse":
            TABLE = {'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..',' ':'/','0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'}
            out = " ".join(TABLE.get(c.upper(),"?") for c in raw_after)
            self._add_line("out", "  " + out)
            return True

        if verb == "flip":
            TABLE = str.maketrans("abcdefghijklmnopqrstuvwxyz,.!?'","ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz'˙¡¿,")
            self._add_line("out", "  " + raw_after.lower().translate(TABLE)[::-1])
            return True

        if verb == "sort":
            words = raw_after.split()
            self._add_line("out", "  " + " ".join(sorted(words)))
            return True

        if verb == "shuffle":
            words = raw_after.split()
            random.shuffle(words)
            self._add_line("out", "  " + " ".join(words))
            return True

        if verb == "random":
            n = int(args[0]) if args and args[0].isdigit() else 100
            self._add_line("out", f"  {random.randint(0, n)}")
            return True

        if verb == "roll":
            spec = args[0] if args else "1d6"
            try:
                n,sides = (int(x) for x in spec.lower().split("d"))
                rolls = [random.randint(1,sides) for _ in range(n)]
                self._add_line("out", f"  {spec}: {rolls}  sum={sum(rolls)}")
            except: self._add_line("err", "usage: roll 2d6")
            return True

        if verb == "coin":
            self._add_line("out", "  " + random.choice(["HEADS", "TAILS"]))
            return True

        if verb == "uuid":
            import uuid
            self._add_line("out", "  " + str(uuid.uuid4()))
            return True

        if verb == "hash":
            import hashlib
            txt = raw_after.encode()
            self._add_line("out", f"  MD5    : {hashlib.md5(txt).hexdigest()}")
            self._add_line("out", f"  SHA1   : {hashlib.sha1(txt).hexdigest()}")
            self._add_line("out", f"  SHA256 : {hashlib.sha256(txt).hexdigest()[:32]}…")
            return True

        # ── FUN ──────────────────────────────────────
        if verb == "matrix":
            chars = "01アイウエオカキクケコサシスセソ"
            for _ in range(16):
                line = "".join(random.choice(chars) for _ in range(60))
                self._add_line("out", f"  {line}")
            return True

        if verb == "glitch":
            chars = "▓▒░█▄▀■□▪▫◆◇○●"
            for _ in range(8):
                line = "".join(random.choice(chars) for _ in range(48))
                self._add_line("err", f"  {line}")
            self._add_line("sys", "GLITCH_SEQUENCE COMPLETE")
            return True

        if verb == "banner":
            txt = raw_after[:14] or "GLITCH"
            BIG = {
                'A':[" ▄█▄ ","█   █","█████","█   █","█   █"],
                'B':["████ ","█   █","████ ","█   █","████ "],
                'C':[" ████","█    ","█    ","█    "," ████"],
                'D':["████ ","█   █","█   █","█   █","████ "],
                'E':["█████","█    ","████ ","█    ","█████"],
                'F':["█████","█    ","████ ","█    ","█    "],
                'G':[" ████","█    ","█  ██","█   █"," ████"],
                'H':["█   █","█   █","█████","█   █","█   █"],
                'I':["█████","  █  ","  █  ","  █  ","█████"],
                'L':["█    ","█    ","█    ","█    ","█████"],
                'O':[" ███ ","█   █","█   █","█   █"," ███ "],
                'R':["████ ","█   █","████ ","█ █  ","█  ██"],
                'S':[" ████","█    "," ███ ","    █","████ "],
                'T':["█████","  █  ","  █  ","  █  ","  █  "],
                'U':["█   █","█   █","█   █","█   █"," ███ "],
                '_':["     ","     ","     ","     ","─────"],
                ' ':["     ","     ","     ","     ","     "],
            }
            rows = ["","","","",""]
            for ch in txt.upper():
                pat = BIG.get(ch, BIG.get(' '))
                for i in range(5): rows[i] += pat[i] + " "
            for r in rows: self._add_line("out", "  " + r)
            return True

        if verb == "rain":
            chars = "01アイウエオ"
            for row in range(12):
                line = ""
                for _ in range(40):
                    if random.random() < 0.3: line += random.choice(chars)
                    else: line += " "
                self._add_line("out", f"  {line}")
            return True

        if verb == "color":
            if len(args) < 3:
                self._add_line("err","usage: color <r> <g> <b>  (0-255)")
                return True
            try:
                r_,g_,b_ = int(args[0]),int(args[1]),int(args[2])
                bar = "██████████████████████████████"
                self._add_line("out", f"  RGB({r_},{g_},{b_})  →  #{r_:02X}{g_:02X}{b_:02X}")
                self._add_line("out", f"  {bar}  ← approx swatch")
            except: self._add_line("err","invalid values")
            return True

        if verb == "ascii":
            ch = (args[0][0] if args else "?")
            self._add_line("out", f"  '{ch}'  dec={ord(ch)}  hex=0x{ord(ch):X}  bin={ord(ch):08b}")
            return True

        if verb in ("pulse","starfield","scanline"):
            self._add_line("sys", f"{verb} effect active on desktop")
            return True

        # ── TERMINAL MGMT ────────────────────────────
        if verb == "history":
            if not self.history:
                self._add_line("sys","(empty)")
            for i,h in enumerate(self.history[-30:], 1):
                self._add_line("out", f"  {i:>3}  {h}")
            return True

        if verb == "repeat":
            if len(args) < 2: self._add_line("err","usage: repeat <n> <cmd>"); return True
            try:
                n = int(args[0])
                sub = " ".join(args[1:])
                for _ in range(min(n, 20)):
                    if not self._built_in(sub):
                        self._thread = threading.Thread(target=self._run_cmd, args=(sub,), daemon=True)
                        self._thread.start()
            except: self._add_line("err","invalid repeat count")
            return True

        if not hasattr(self, "_aliases"): self._aliases = {}

        if verb == "alias":
            if not args: self._add_line("err","usage: alias name=cmd"); return True
            pair = " ".join(args)
            if "=" not in pair: self._add_line("err","usage: alias name=cmd"); return True
            name, cmd_ = pair.split("=",1)
            self._aliases[name.strip()] = cmd_.strip()
            self._add_line("sys", f"alias {name.strip()} = {cmd_.strip()}")
            return True

        if verb == "unalias":
            if not args: self._add_line("err","usage: unalias <name>"); return True
            n = args[0]
            if n in self._aliases:
                del self._aliases[n]; self._add_line("sys", f"removed alias {n}")
            else: self._add_line("err", f"no alias: {n}")
            return True

        if verb == "aliases":
            if not hasattr(self,"_aliases") or not self._aliases:
                self._add_line("sys","(no aliases defined)")
            else:
                for k,v in self._aliases.items():
                    self._add_line("out", f"  {k:<12} → {v}")
            return True

        if verb in ("exit","quit"):
            self.close(); return True

        # check aliases
        if not hasattr(self,"_aliases"): self._aliases = {}
        if verb in self._aliases:
            self._execute(self._aliases[verb] + (" " + " ".join(args) if args else ""))
            return True

        return False

    def _execute(self, cmd):
        cmd = cmd.strip()
        if not cmd: return
        self.history.append(cmd)
        if len(self.history) > 100: self.history.pop(0)
        self.hist_idx = -1
        self._add_line("in", self.PROMPT + cmd)
        if not self._built_in(cmd):
            # run in thread
            self._thread = threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True)
            self._thread.start()

    def _content_rect(self):
        return pygame.Rect(self.x+8, self.y+STATUS_H+8, self.W-16, self.H-STATUS_H-42)

    def _visible_lines(self):
        cr = self._content_rect()
        return max(1, (cr.h - self.LINE_H) // self.LINE_H)  # -1 row for input

    def handle(self, event, now_ms):
        if self.state != "open": return
        act = self.handle_base(event, now_ms)
        if act == "close": self.close()
        elif act == "minimize": self.hide()
        mx,my = pygame.mouse.get_pos()
        cr = self._content_rect()

        if event.type == pygame.MOUSEWHEEL:
            if cr.collidepoint(*pygame.mouse.get_pos()):
                vis = self._visible_lines()
                max_s = max(0, len(self.lines) - vis)
                self.scroll = max(0, min(max_s, self.scroll - event.y * 3))

        if event.type == pygame.KEYDOWN:
            if not pygame.Rect(self.x,self.y,self.W,self.H).collidepoint(mx,my): return
            k = event.key; uni = event.unicode
            if k == pygame.K_RETURN:
                self._execute(self.input_buf)
                self.input_buf = ""
            elif k == pygame.K_BACKSPACE:
                self.input_buf = self.input_buf[:-1]
                self.repeat_key = k; self.repeat_t = now_ms+400; self.repeat_d = 38
            elif k == pygame.K_UP:
                if self.history:
                    if self.hist_idx == -1: self.hist_idx = len(self.history)-1
                    elif self.hist_idx > 0: self.hist_idx -= 1
                    self.input_buf = self.history[self.hist_idx]
            elif k == pygame.K_DOWN:
                if self.hist_idx != -1:
                    self.hist_idx += 1
                    if self.hist_idx >= len(self.history):
                        self.hist_idx = -1; self.input_buf = ""
                    else:
                        self.input_buf = self.history[self.hist_idx]
            elif k == pygame.K_TAB:
                # basic tab-complete: filenames in cwd starting with last word
                parts = self.input_buf.split()
                prefix = parts[-1] if parts else ""
                try:
                    matches = [e for e in os.listdir(self.cwd) if e.startswith(prefix)]
                    if len(matches) == 1:
                        self.input_buf = " ".join(parts[:-1] + [matches[0]]) if parts else matches[0]
                    elif len(matches) > 1:
                        self._add_line("sys", "  " + "  ".join(matches))
                except Exception:
                    pass
            elif uni and uni.isprintable():
                self.input_buf += uni
                self.repeat_key = k; self.repeat_t = now_ms+400; self.repeat_d = 38
            else:
                self.repeat_key = None
        if event.type == pygame.KEYUP:
            self.repeat_key = None

    def update(self, dt_ms, now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in ("open","opening","closing"): return
        self.update_fx(dt_ms, now_ms)
        # flush thread output
        with self._lock:
            for kind, text in self._output_buf:
                self._add_line(kind, text)
            self._output_buf.clear()
        # key repeat
        if self.repeat_key == pygame.K_BACKSPACE and now_ms >= self.repeat_t:
            self.input_buf = self.input_buf[:-1]
            self.repeat_t = now_ms + self.repeat_d

    def draw(self, surf, dt_ms, now_ms):
        mx,my = pygame.mouse.get_pos()
        if not self.draw_frame(surf, mx, my, "TERM_MODULE"): return
        bx,by,bw,bh = self.x,self.y,self.W,self.H
        t_anim = ease_out(self.anim)
        vis_h = int(bh * t_anim)
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        cr = self._content_rect()
        pygame.draw.rect(surf, (0,4,10), cr)
        pygame.draw.rect(surf, CYN_FAINT, cr, 1)

        vis = self._visible_lines()
        # colour map
        COL_MAP = {"sys":CYN_MID,"in":CYN,"out":TXT,"err":(220,80,60)}

        for i in range(vis):
            li = i + self.scroll
            if li >= len(self.lines): break
            kind, text = self.lines[li]
            col = COL_MAP.get(kind, TXT)
            y_ = cr.y + 4 + i * self.LINE_H
            # prefix glyph
            glyph = {"sys":"//","in":">>","out":"  ","err":"!!"}[kind]
            gs = fTerm.render(glyph, True, CYN_FAINT)
            surf.blit(gs, (cr.x+4, y_))
            ts = fTerm.render(text[:int((cr.w-40)/fTerm.size("W")[0])], True, col)
            surf.blit(ts, (cr.x+30, y_))

        # scrollbar
        total = len(self.lines)
        if total > vis:
            sb_x = cr.x + cr.w - 5
            sb_h = cr.h - self.LINE_H - 4
            th = max(12, int(sb_h * vis / total))
            ty_ = cr.y + int(sb_h * self.scroll / total)
            pygame.draw.rect(surf, CYN_FAINT, (sb_x, cr.y, 4, sb_h))
            pygame.draw.rect(surf, CYN_DIM,   (sb_x, ty_, 4, th))

        # input line
        input_y = cr.y + cr.h - self.LINE_H - 4
        pygame.draw.line(surf, CYN_FAINT, (cr.x, input_y-2), (cr.x+cr.w, input_y-2))
        prompt_s = fTerm.render(self.PROMPT, True, CYN)
        surf.blit(prompt_s, (cr.x+4, input_y))
        cursor_x = cr.x + 4 + fTerm.size(self.PROMPT)[0]
        disp_input = self.input_buf
        max_chars = (cr.w - fTerm.size(self.PROMPT)[0] - 20) // max(1, fTerm.size("W")[0])
        if len(disp_input) > max_chars:
            disp_input = disp_input[-max_chars:]
        inp_s = fTerm.render(disp_input, True, TXT)
        surf.blit(inp_s, (cursor_x, input_y))
        if (now_ms//500)%2==0:
            cx = cursor_x + fTerm.size(disp_input)[0]
            pygame.draw.rect(surf, CYN, (cx, input_y, 2, self.LINE_H-2))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  PERFORMANCE / SETTINGS WINDOW  (PERF.exe)
# ══════════════════════════════════════════════════════
class PerfWin(Window):
    def __init__(self):
        super().__init__("perf","PERF", SW//2-220, SH//2-180, 440, 360)
        self.bt = {k:0. for k in ("lite","cyber","black","particles","glitch_fx")}
        self.show_particles = True
        self.show_glitch    = True

    def handle(self, event, now_ms):
        if self.state != "open": return
        act = self.handle_base(event, now_ms)
        if act == "close": self.close()
        elif act == "minimize": self.hide()
        mx, my = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, r in self._rows().items():
                if r.collidepoint(mx, my):
                    self._toggle(key)

    def _toggle(self, key):
        global _SHOW_PARTICLES, _SHOW_GLITCH_FX
        if key == "lite":
            bg_mgr.set_mode(BG_MODE_LITE)
        elif key == "cyber":
            bg_mgr.set_mode(BG_MODE_GRID)
        elif key == "black":
            bg_mgr.set_mode(BG_MODE_BLACK)
        elif key == "particles":
            _SHOW_PARTICLES = not _SHOW_PARTICLES
        elif key == "glitch_fx":
            _SHOW_GLITCH_FX = not _SHOW_GLITCH_FX

    def _rows(self):
        bx, by = self.x+20, self.y+STATUS_H+28
        rw, rh, gap = self.W-40, 34, 8
        keys = ["lite","cyber","black","particles","glitch_fx"]
        return {k: pygame.Rect(bx, by+i*(rh+gap), rw, rh) for i,k in enumerate(keys)}

    def update(self, dt_ms, now_ms):
        self.update_anim(dt_ms/1000.)
        if self.state not in ("open","opening","closing"): return
        self.update_fx(dt_ms, now_ms)

    def draw(self, surf, dt_ms, now_ms):
        mx, my = pygame.mouse.get_pos()
        if not self.draw_frame(surf, mx, my, "PERF_MODULE"): return
        bx,by,bw,bh = self.x,self.y,self.W,self.H
        vis_h = int(bh*ease_out(self.anim))
        surf.set_clip(pygame.Rect(bx,by,bw,vis_h))

        render_glow(surf, fLabel, "PERFORMANCE  &  DISPLAY", CYN_DIM,
                    (bx+26, by+STATUS_H+8), glow_radius=2, glow_alpha=35)

        LABELS = {
            "lite":       ("LITE MODE  (static dot grid, no rain)",    BG_MODE_LITE),
            "cyber":      ("CYBER GRID  (perspective + rain)",         BG_MODE_GRID),
            "black":      ("PURE BLACK  (rain only)",                  BG_MODE_BLACK),
            "particles":  ("PARTICLE WEB",                             None),
            "glitch_fx":  ("GLITCH SCANLINES",                        None),
        }

        for key, r in self._rows().items():
            hov = r.collidepoint(mx, my)
            label, bg_mode = LABELS[key]

            # is this option currently active?
            if bg_mode is not None:
                active = (bg_mgr.mode == bg_mode)
            elif key == "particles":
                active = _SHOW_PARTICLES
            else:
                active = _SHOW_GLITCH_FX

            fill_col = (0,35,25) if active else ((0,18,12) if hov else (0,8,6))
            pygame.draw.rect(surf, fill_col, r)
            border_col = CYN if active else (CYN_MID if hov else CYN_DIM)
            pygame.draw.rect(surf, border_col, r, 1)

            # status indicator  ● / ○
            dot = "●" if active else "○"
            dot_col = CYN if active else CYN_DIM
            dot_s = fBtn.render(dot, True, dot_col)
            surf.blit(dot_s, (r.x+10, r.y+r.h//2-dot_s.get_height()//2))

            lbl_s = fMain.render(label, True, CYN if active else (TXT if hov else CYN_DIM))
            surf.blit(lbl_s, (r.x+32, r.y+r.h//2-lbl_s.get_height()//2))

            # glow on active row
            if active:
                g = pygame.Surface((r.w+6,r.h+6), pygame.SRCALPHA)
                pygame.draw.rect(g, (0,255,200,18), (0,0,r.w+6,r.h+6), 2)
                surf.blit(g, (r.x-3,r.y-3))

        # bottom tip
        tip = fStat.render("BG modes are mutually exclusive  //  toggles take effect instantly", True, CYN_FAINT)
        surf.blit(tip, (bx + bw//2 - tip.get_width()//2, by+bh-32))

        surf.set_clip(None)


# ══════════════════════════════════════════════════════
#  DESKTOP ICONS  — glowing like FPS, multi-select drag
# ══════════════════════════════════════════════════════
IW,IH=72,72; IPAD=28
IGRID=96

# Load saved positions
_saved_positions = _cfg.get("icon_positions", {})

# ── performance toggles (used by PerfWin and draw loop) ──
_SHOW_PARTICLES = True
_SHOW_GLITCH_FX = True

ICONS=[
    {"id":"log",   "label":"LOG.exe",
     "x":_saved_positions.get("log",   [IPAD, SH//2-IH*2-16])[0],
     "y":_saved_positions.get("log",   [IPAD, SH//2-IH*2-16])[1]},
    {"id":"music", "label":"MUSIC.exe",
     "x":_saved_positions.get("music", [IPAD, SH//2-IH//2])[0],
     "y":_saved_positions.get("music", [IPAD, SH//2-IH//2])[1]},
    {"id":"calc",  "label":"CALC.exe",
     "x":_saved_positions.get("calc",  [IPAD, SH//2+IH//2+16])[0],
     "y":_saved_positions.get("calc",  [IPAD, SH//2+IH//2+16])[1]},
    {"id":"images","label":"IMGS.exe",
     "x":_saved_positions.get("images",[IPAD, SH//2+IH*2+32])[0],
     "y":_saved_positions.get("images",[IPAD, SH//2+IH*2+32])[1]},
    {"id":"paint", "label":"PAINT.exe",
     "x":_saved_positions.get("paint", [IPAD+IGRID, SH//2-IH*2-16])[0],
     "y":_saved_positions.get("paint", [IPAD+IGRID, SH//2-IH*2-16])[1]},
    {"id":"term",  "label":"TERM.exe",
     "x":_saved_positions.get("term",  [IPAD+IGRID, SH//2-IH//2])[0],
     "y":_saved_positions.get("term",  [IPAD+IGRID, SH//2-IH//2])[1]},
    {"id":"perf",  "label":"PERF.exe",
     "x":_saved_positions.get("perf",  [IPAD+IGRID, SH//2+IH//2+16])[0],
     "y":_saved_positions.get("perf",  [IPAD+IGRID, SH//2+IH//2+16])[1]},
]

def _save_icon_positions():
    pos = {ic["id"]: [ic["x"], ic["y"]] for ic in ICONS}
    _cfg["icon_positions"] = pos
    save_config(_cfg)

_dclick={}; DC_MS=380

# Multi-select drag state
_ic_state = {
    "drag_ids": [],          # list of icon ids being dragged
    "drag_offsets": {},      # id -> (ox, oy) offset from mouse
    "t": 0,                  # time of press
    "ghost": {},             # id -> (gx,gy) snap preview
    "lmb_down": False,
    "lmb_down_pos": (0,0),
    "select_rect_start": None,  # (mx,my) for rubber-band
    "selected_ids": set(),      # currently selected icons
}
_ic_drag_threshold = 200     # ms hold before drag activates
_GLOW_PULSE = {}             # id -> float (0..1 glow intensity)

def _snap_to_grid(x, y):
    gx = round(x / IGRID) * IGRID
    gy = round(y / IGRID) * IGRID
    gx = max(0, min(SW - IW, gx))
    gy = max(0, min(SH - TASKBAR_H - IH - 20, gy))
    return gx, gy

def draw_icon(surf, icon, mx, my, active, selected=False, dragging=False, glow=0.0):
    ix,iy=icon["x"],icon["y"]; r=pygame.Rect(ix,iy,IW,IH)
    hov=r.collidepoint(mx,my) and not dragging
    lit = hov or active or selected or glow > 0.05

    # base colour (mimics FPS widget colour logic)
    if active:
        col = CYN
    elif selected:
        col = (0, 220, 170)
    elif hov:
        col = CYN_MID
    else:
        col = (0,50,40)

    alpha = 130 if dragging else 255
    tmp=pygame.Surface((IW,IH),pygame.SRCALPHA)
    tmp.fill((0,8,6,alpha))
    pygame.draw.rect(tmp,(*col,alpha),(0,0,IW,IH),1)
    surf.blit(tmp,(ix,iy))

    # corner brackets — same as FPS widget
    for seg in [[(ix,iy+12),(ix,iy),(ix+12,iy)],
                [(ix+IW-12,iy),(ix+IW,iy),(ix+IW,iy+12)],
                [(ix,iy+IH-12),(ix,iy+IH),(ix+12,iy+IH)],
                [(ix+IW-12,iy+IH),(ix+IW,iy+IH),(ix+IW,iy+IH-12)]]:
        pygame.draw.lines(surf, col, False, seg, 1)

    # glow aura (like FPS bar)
    if lit or glow > 0.1:
        intensity = max(glow, 0.3 if (hov or active or selected) else 0.0)
        g_surf = pygame.Surface((IW+16, IH+16), pygame.SRCALPHA)
        for off in range(3, 0, -1):
            a_val = int(intensity * 50 * (1 - off/4))
            pygame.draw.rect(g_surf, (col[0],col[1],col[2],a_val),
                             (off, off, IW+16-off*2, IH+16-off*2), 1)
        surf.blit(g_surf, (ix-8, iy-8))

    # icon art
    mid=ix+IW//2; midy=iy+IH//2
    if icon["id"]=="log":
        for li in range(3): pygame.draw.line(surf,col,(ix+12,iy+18+li*12),(ix+12+(28 if li<2 else 18),iy+18+li*12),2)
    elif icon["id"]=="music":
        pygame.draw.line(surf,col,(mid+4,midy-12),(mid+4,midy+3),2)
        pygame.draw.line(surf,col,(mid+4,midy-12),(mid+12,midy-9),2)
        pygame.draw.ellipse(surf,col,(mid,midy+1,8,5),1)
    elif icon["id"]=="calc":
        for li in range(3):
            for ci in range(3): pygame.draw.rect(surf,col,(ix+16+ci*14,iy+18+li*12,8,8),1)
    elif icon["id"]=="images":
        pygame.draw.rect(surf,col,(ix+10,iy+14,IW-20,IH-28),1)
        pygame.draw.circle(surf,col,(ix+22,iy+26),4,1)
        pts_=[(ix+10,iy+IH-14),(ix+26,iy+30),(ix+42,iy+40),(ix+IW-10,iy+20),(ix+IW-10,iy+IH-14)]
        pygame.draw.lines(surf,col,False,pts_,1)
    elif icon["id"]=="paint":
        # palette icon
        pygame.draw.rect(surf,col,(ix+14,iy+14,IW-28,IH-28),1)
        for ci,c2 in enumerate([(255,80,80),(0,255,200),(255,200,0)]):
            pygame.draw.circle(surf,c2,(ix+20+ci*14,iy+IH-22),4)
        pygame.draw.line(surf,col,(ix+IW-22,iy+18),(ix+22,iy+IH-22),2)
    elif icon["id"]=="term":
        # terminal icon: > prompt
        pygame.draw.lines(surf,col,False,[(ix+14,midy-10),(ix+26,midy),(ix+14,midy+10)],2)
        pygame.draw.line(surf,col,(ix+30,midy+10),(ix+IW-14,midy+10),2)
    elif icon["id"]=="perf":
        # perf icon: speedometer / gauge
        pygame.draw.arc(surf,col,pygame.Rect(ix+10,iy+14,IW-20,IH-20),0.4,math.pi-0.4,2)
        mid2=ix+IW//2; midy2=iy+IH//2+4
        pygame.draw.line(surf,CYN,(mid2,midy2),(mid2-12,midy2-10),2)
        pygame.draw.circle(surf,col,(mid2,midy2),3)

    # label with glow
    lbl=fIcon.render(icon["label"],True,col)
    render_glow(surf, fIcon, icon["label"], col,
                (ix+IW//2-lbl.get_width()//2, iy+IH+4),
                glow_radius=2 if lit else 1,
                glow_alpha=50 if (hov or active or selected) else 18)

    # selection tick
    if selected:
        pygame.draw.rect(surf, CYN, (ix+IW-14, iy+2, 12, 12), 1)
        pygame.draw.line(surf, CYN, (ix+IW-12, iy+8), (ix+IW-9, iy+12), 1)
        pygame.draw.line(surf, CYN, (ix+IW-9,  iy+12),(ix+IW-4,  iy+5),  1)


# ══════════════════════════════════════════════════════
#  TASKBAR
# ══════════════════════════════════════════════════════
def draw_taskbar(surf,windows,mx,my):
    TH=TASKBAR_H
    # bg with gradient tint
    tb_surf = pygame.Surface((SW, TH), pygame.SRCALPHA)
    tb_surf.fill((0,3,10,245))
    # hex-dot pattern
    for tx_ in range(0,SW,18):
        pygame.draw.circle(tb_surf,(0,255,200,8),(tx_,TH//2),1)
    surf.blit(tb_surf,(0,SH-TH))
    # top border double-line
    pygame.draw.line(surf,CYN_DIM,(0,SH-TH),(SW,SH-TH),1)
    pygame.draw.line(surf,(0,255,200,40),(0,SH-TH+1),(SW,SH-TH+1),1)
    # left brand
    render_glow(surf, fIcon, "GLITCH_OS v4.1", CYN_MID, (12, SH-TH+(TH-fIcon.get_height())//2),
                glow_radius=2, glow_alpha=35)
    # right clock
    cl_txt = time.strftime("// %H:%M:%S  %d.%m.%Y")
    render_glow(surf, fClock, cl_txt, CYN_MID,
                (SW-fClock.size(cl_txt)[0]-14, SH-TH+(TH-fClock.get_height())//2),
                glow_radius=2, glow_alpha=35)
    bx=130
    for win in windows:
        r=pygame.Rect(bx,SH-TH+4,64,TH-8)
        is_open=win.state in("open","opening")
        is_hid =win.state=="hidden"
        col=CYN if is_open else (CYN_MID if is_hid else CYN_FAINT)
        hov=r.collidepoint(mx,my)
        pygame.draw.rect(surf,(0,28,20) if is_open else ((0,14,10) if is_hid else (0,0,0)),r)
        pygame.draw.rect(surf,col,r,1)
        if hov:
            g=pygame.Surface((r.w+4,r.h+4),pygame.SRCALPHA)
            pygame.draw.rect(g,(col[0],col[1],col[2],35),(0,0,r.w+4,r.h+4),1)
            surf.blit(g,(r.x-2,r.y-2))
        if is_open: pygame.draw.rect(surf,CYN,(bx+r.w//2-3,SH-TH+TH-6,6,2))
        lbl_s=fIcon.render(win.wid.upper(),True,col)
        surf.blit(lbl_s,(r.x+r.w//2-lbl_s.get_width()//2,r.y+r.h//2-lbl_s.get_height()//2))
        bx+=72


def taskbar_click(windows,mx,my):
    bx=130
    for win in windows:
        r=pygame.Rect(bx,SH-TASKBAR_H+4,64,TASKBAR_H-8)
        if r.collidepoint(mx,my):
            if win.state=="open": win.hide()
            elif win.state=="hidden": win.show()
            elif win.state=="closed": win.open()
            elif win.state in("closing","opening"): pass
        bx+=72


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
log_win   = LogWin()
music_win = MusicWin()
calc_win  = CalcWin()
img_win   = ImageWin()
paint_win = PaintWin()
term_win  = TermWin()
perf_win  = PerfWin()
WINS      = [log_win, music_win, calc_win, img_win, paint_win, term_win, perf_win]
WIN_MAP   = {w.wid:w for w in WINS}

# ── context menu callbacks ────────────────────────────
def _ctx_new_note():
    log_win.open()
    log_win._new_page()
    log_win.bring_to_front()

def _ctx_bg_grid():  bg_mgr.set_mode(BG_MODE_GRID)
def _ctx_bg_black(): bg_mgr.set_mode(BG_MODE_BLACK)
def _ctx_bg_video(): bg_mgr.pick_video()

def show_desktop_ctx(mx, my):
    ctx_menu.show(mx, my, [
        ("  NEW NOTE",           _ctx_new_note),
        (None, None),
        ("  BACKGROUND",         None),
        ("    • Cyber Grid",     _ctx_bg_grid),
        ("    • Pure Black",     _ctx_bg_black),
        ("    • Video (MP4)",    _ctx_bg_video),
        (None, None),
        ("  OPEN LOG",        lambda: log_win.show() if log_win.state=="hidden" else log_win.open()),
        ("  OPEN MUSIC",      lambda: music_win.show() if music_win.state=="hidden" else music_win.open()),
        ("  OPEN CALC",       lambda: calc_win.show() if calc_win.state=="hidden" else calc_win.open()),
        ("  OPEN IMAGES",     lambda: img_win.show() if img_win.state=="hidden" else img_win.open()),
        ("  OPEN PAINT",      lambda: paint_win.show() if paint_win.state=="hidden" else paint_win.open()),
        ("  OPEN TERMINAL",   lambda: term_win.show() if term_win.state=="hidden" else term_win.open()),
        ("  OPEN PERF",        lambda: perf_win.show() if perf_win.state=="hidden" else perf_win.open()),
    ])

scan_y   = 0.
gl_lines = []

fps_samples = []
fps_display = 0.0
fps_update_t = 0

# rubber-band selection surface
_sel_rect_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)

sfx.play("boot")
running=True
while running:
    dt_ms=clock.tick(60)
    now_ms=pygame.time.get_ticks()
    mx,my=pygame.mouse.get_pos()
    dt=dt_ms/1000.

    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            if ctx_menu.visible: ctx_menu.hide()
            elif _ic_state["selected_ids"]: _ic_state["selected_ids"].clear()
            else: running=False

        # context menu gets first crack
        if ctx_menu.handle(event):
            pass
        else:
            # right-click on desktop
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==3:
                on_win = any(
                    pygame.Rect(w.x,w.y,w.W,w.H).collidepoint(mx,my)
                    for w in WINS if w.state=="open"
                )
                if not on_win and my < SH - TASKBAR_H:
                    show_desktop_ctx(mx, my)

            # ── LMB down ────────────────────────────────────
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                # check for a window click first
                on_win = any(
                    pygame.Rect(w.x,w.y,w.W,w.H).collidepoint(mx,my)
                    for w in WINS if w.state=="open"
                )
                taskbar_click(WINS,mx,my)

                if not on_win and my < SH - TASKBAR_H:
                    # which icons did we land on?
                    hit = None
                    for i, ic in enumerate(ICONS):
                        if pygame.Rect(ic["x"],ic["y"],IW,IH).collidepoint(mx,my):
                            hit = ic["id"]; break

                    if hit:
                        # if hitting a selected icon, prepare group drag
                        if hit not in _ic_state["selected_ids"]:
                            _ic_state["selected_ids"] = {hit}
                        drag_ids = list(_ic_state["selected_ids"])
                        offsets = {}
                        for ic in ICONS:
                            if ic["id"] in drag_ids:
                                offsets[ic["id"]] = (mx - ic["x"], my - ic["y"])
                        _ic_state["drag_ids"] = drag_ids
                        _ic_state["drag_offsets"] = offsets
                        _ic_state["t"] = now_ms
                        _ic_state["ghost"] = {}
                        _ic_state["lmb_down"] = True
                        _ic_state["lmb_down_pos"] = (mx, my)
                        _ic_state["select_rect_start"] = None
                    else:
                        # start rubber-band selection
                        _ic_state["drag_ids"] = []
                        _ic_state["lmb_down"] = True
                        _ic_state["lmb_down_pos"] = (mx, my)
                        _ic_state["select_rect_start"] = (mx, my)
                        _ic_state["selected_ids"] = set()

            # ── LMB up ──────────────────────────────────────
            if event.type==pygame.MOUSEBUTTONUP and event.button==1:
                if _ic_state["lmb_down"]:
                    held = now_ms - _ic_state["t"]
                    if _ic_state["drag_ids"] and not _ic_state["select_rect_start"]:
                        if held < _ic_drag_threshold:
                            # it was a click — double-click check (single icon)
                            if len(_ic_state["drag_ids"]) == 1:
                                iid = _ic_state["drag_ids"][0]
                                last=_dclick.get(iid,0)
                                if now_ms-last<DC_MS:
                                    w=WIN_MAP[iid]
                                    if w.state=="closed": w.open()
                                    elif w.state=="hidden": w.show()
                                    else: w.bring_to_front()
                                _dclick[iid]=now_ms
                        else:
                            # snap all dragged icons
                            for ic in ICONS:
                                if ic["id"] in _ic_state["drag_ids"]:
                                    nx,ny = _snap_to_grid(ic["x"], ic["y"])
                                    ic["x"]=nx; ic["y"]=ny
                            _save_icon_positions()
                        _ic_state["ghost"] = {}

                    elif _ic_state["select_rect_start"]:
                        # finalise rubber-band
                        sx,sy = _ic_state["select_rect_start"]
                        sel_r = pygame.Rect(min(sx,mx),min(sy,my),abs(mx-sx),abs(my-sy))
                        _ic_state["selected_ids"] = set()
                        for ic in ICONS:
                            ir = pygame.Rect(ic["x"],ic["y"],IW,IH)
                            if sel_r.colliderect(ir):
                                _ic_state["selected_ids"].add(ic["id"])
                        _ic_state["select_rect_start"] = None

                    _ic_state["lmb_down"] = False
                    _ic_state["drag_ids"] = []

            # ── mouse motion ────────────────────────────────
            if event.type==pygame.MOUSEMOTION:
                if _ic_state["lmb_down"] and _ic_state["drag_ids"] and not _ic_state["select_rect_start"]:
                    held = now_ms - _ic_state["t"]
                    if held >= _ic_drag_threshold:
                        # move all dragged icons with the mouse
                        ghost_map = {}
                        for ic in ICONS:
                            if ic["id"] in _ic_state["drag_ids"]:
                                ox,oy = _ic_state["drag_offsets"].get(ic["id"],(0,0))
                                ic["x"] = mx-ox; ic["y"] = my-oy
                                gx,gy = _snap_to_grid(ic["x"],ic["y"])
                                ghost_map[ic["id"]] = (gx,gy)
                        _ic_state["ghost"] = ghost_map

            # window events
            for win in sorted(WINS,key=lambda w:-w.z):
                if win.state=="open":
                    win.handle(event,now_ms)

    # update glow pulse
    for ic in ICONS:
        iid = ic["id"]
        w = WIN_MAP[iid]
        target_glow = 1.0 if w.state in ("open","opening") else 0.0
        cur = _GLOW_PULSE.get(iid, 0.0)
        _GLOW_PULSE[iid] = cur + (target_glow - cur) * min(1.0, dt * 8)

    # update
    bg_mgr.update(time.time(), dt)
    for p in pts:
        p["x"]=(p["x"]+p["vx"])%SW; p["y"]=(p["y"]+p["vy"])%SH
    scan_y=(scan_y+dt_ms/3200.)%1.
    if random.random()<.007:
        gl_lines.append({"y":random.uniform(0,1),"h":random.uniform(1,3),
            "a":random.randint(4,14),"exp":now_ms+random.randint(40,90)})
    gl_lines=[g for g in gl_lines if g["exp"]>now_ms]

    for win in WINS: win.update(dt_ms,now_ms)

    if dt_ms > 0:
        fps_samples.append(1000.0 / dt_ms)
        if len(fps_samples) > 30: fps_samples.pop(0)
    if now_ms - fps_update_t > 250:
        fps_display = sum(fps_samples) / len(fps_samples) if fps_samples else 0.
        fps_update_t = now_ms

    # ── draw ─────────────────────────────────────────
    bg_mgr.draw(screen, time.time())

    if _SHOW_PARTICLES:
        PSURF.fill((0,0,0,0))
        for i in range(len(pts)):
            for j in range(i+1,len(pts)):
                dx=pts[i]["x"]-pts[j]["x"]; dy=pts[i]["y"]-pts[j]["y"]
                d=math.sqrt(dx*dx+dy*dy)
                if d<CONN:
                    a=int(14*(1-d/CONN))
                    pygame.draw.line(PSURF,(0,170,130,a),(int(pts[i]["x"]),int(pts[i]["y"])),(int(pts[j]["x"]),int(pts[j]["y"])))
        for p in pts:
            b=p["b"]
            pygame.draw.circle(PSURF,(0,b,int(b*.75),180),(int(p["x"]),int(p["y"])),max(1,int(p["r"])))
        screen.blit(PSURF,(0,0))

    if _SHOW_GLITCH_FX:
        for g in gl_lines:
            gy=int(g["y"]*SH); gh=max(1,int(g["h"]))
            gs=pygame.Surface((SW,gh));gs.set_alpha(g["a"]);gs.fill(CYN_FAINT)
            screen.blit(gs,(0,gy))
        pygame.draw.line(screen,(0,30,24),(0,int(scan_y*SH)),(SW,int(scan_y*SH)))

    # OS title — bright glow
    render_glow(screen, fTitle, "GLITCH_OS", CYN,
                (SW//2 - fTitle.size("GLITCH_OS")[0]//2, 16),
                glow_radius=2, glow_alpha=35)
    hint_txt = "// dbl-click=open  |  hold+drag=move  |  drag desktop=select  |  RMB=menu  |  ESC quit"
    render_glow(screen, fStat, hint_txt, CYN_MID,
                (SW//2 - fStat.size(hint_txt)[0]//2, 46),
                glow_radius=3, glow_alpha=50)

    # rubber-band selection rectangle
    if _ic_state["select_rect_start"] and _ic_state["lmb_down"]:
        sx,sy = _ic_state["select_rect_start"]
        sel_w,sel_h = mx-sx, my-sy
        _sel_rect_surf.fill((0,0,0,0))
        sel_box = pygame.Rect(min(sx,mx),min(sy,my),abs(sel_w),abs(sel_h))
        if sel_box.w > 2 and sel_box.h > 2:
            pygame.draw.rect(_sel_rect_surf,(0,255,200,18),sel_box)
            pygame.draw.rect(_sel_rect_surf,(0,255,200,100),sel_box,1)
        screen.blit(_sel_rect_surf,(0,0))

    # ghost snap previews
    for iid,(gx,gy) in _ic_state["ghost"].items():
        ghost=pygame.Surface((IW,IH),pygame.SRCALPHA)
        pygame.draw.rect(ghost,(0,255,200,35),(0,0,IW,IH))
        pygame.draw.rect(ghost,(0,255,200,80),(0,0,IW,IH),1)
        screen.blit(ghost,(gx,gy))

    # draw icons
    drag_set = set(_ic_state["drag_ids"]) if _ic_state["drag_ids"] else set()
    for ic in ICONS:
        w = WIN_MAP[ic["id"]]
        draw_icon(screen, ic, mx, my,
                  active=w.state not in("closed","closing"),
                  selected=ic["id"] in _ic_state["selected_ids"],
                  dragging=ic["id"] in drag_set,
                  glow=_GLOW_PULSE.get(ic["id"],0.0))

    for win in sorted(WINS,key=lambda w:w.z):
        win.draw(screen,dt_ms,now_ms)

    draw_taskbar(screen,WINS,mx,my)
    ctx_menu.draw(screen)

    # FPS widget
    fps_val = int(fps_display)
    if fps_val >= 55:   fps_col=(0,255,180)
    elif fps_val >= 40: fps_col=(200,220,0)
    else:               fps_col=(255,80,60)
    FW,FH=88,34; FX=SW-FW-8; FY=SH-TASKBAR_H-FH-8
    fps_bg=pygame.Surface((FW,FH),pygame.SRCALPHA)
    fps_bg.fill((0,4,12,210)); screen.blit(fps_bg,(FX,FY))
    for seg in [[(FX,FY+8),(FX,FY),(FX+8,FY)],
                [(FX+FW-8,FY),(FX+FW,FY),(FX+FW,FY+8)],
                [(FX,FY+FH-8),(FX,FY+FH),(FX+8,FY+FH)],
                [(FX+FW-8,FY+FH),(FX+FW,FY+FH),(FX+FW,FY+FH-8)]]:
        pygame.draw.lines(screen,fps_col,False,seg,1)
    lbl_s=fStat.render("FPS",True,CYN_FAINT)
    screen.blit(lbl_s,(FX+5,FY+3))
    num_s=fBtn.render(f"{fps_val:3d}",True,fps_col)
    screen.blit(num_s,(FX+FW-num_s.get_width()-6,FY+FH//2-num_s.get_height()//2+2))
    bar_area=pygame.Rect(FX+4,FY+FH-7,FW-8,5)
    pygame.draw.rect(screen,CYN_FAINT,bar_area,1)
    samples=fps_samples[-18:]
    if samples:
        bw_=max(1,(bar_area.w)//len(samples))
        for i,s in enumerate(samples):
            frac=min(1.,s/70.); bh_=max(1,int(bar_area.h*frac))
            c=(0,int(80+frac*170),int(60+frac*120))
            pygame.draw.rect(screen,c,(bar_area.x+i*bw_,bar_area.y+bar_area.h-bh_,max(1,bw_-1),bh_))

    # cursor
    cur_set=False
    for win in sorted(WINS,key=lambda w:-w.z):
        if win.cursor_check(): cur_set=True;break
    if not cur_set:
        on_icon=any(pygame.Rect(ic["x"],ic["y"],IW,IH).collidepoint(mx,my) for ic in ICONS)
        on_task=pygame.Rect(130,SH-TASKBAR_H+4,len(WINS)*72,TASKBAR_H-8).collidepoint(mx,my)
        if ctx_menu.visible:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        elif _ic_state["select_rect_start"]:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if (on_icon or on_task) else pygame.SYSTEM_CURSOR_ARROW)

    pygame.display.flip()

# save icon positions on exit
_save_icon_positions()
pygame.quit()
sys.exit()