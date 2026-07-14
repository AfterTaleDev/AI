import tkinter as tk
from tkinter import font as tkfont
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import math, re

# ─────────────────────────────────────────────────────────────────────────────
#  PALETTE  — warm off-black with amber/gold accent, clean editorial feel
# ─────────────────────────────────────────────────────────────────────────────
BG0    = "#0c0c0e"   # deepest bg
BG1    = "#111114"   # panel bg
BG2    = "#18181d"   # card bg
BG3    = "#1f1f26"   # input bg
BORDER = "#2a2a35"
BORDER2= "#3a3a48"
GOLD   = "#f0c040"   # primary accent
GOLD2  = "#c8962a"   # darker gold
TEAL   = "#3dd6c8"   # secondary accent
RED    = "#e05555"
GREEN  = "#4ecb71"
WHITE  = "#eeeef2"
DIM    = "#9090a8"
DIM2   = "#55556a"

PLOT_COLORS = [
    "#f0c040","#3dd6c8","#f07050","#a78bfa","#4ecb71",
    "#f472b6","#60a5fa","#fb923c","#34d399","#e879f9",
]

UI_FONT   = "Segoe UI"
CODE_FONT = "Cascadia Code"

# ─────────────────────────────────────────────────────────────────────────────
#  MATH NAMESPACE
# ─────────────────────────────────────────────────────────────────────────────
def make_ns(x=None):
    xv = x if x is not None else np.array([0.0])
    return {
        "x": xv, "np": np,
        "sin":np.sin,"cos":np.cos,"tan":np.tan,
        "asin":np.arcsin,"acos":np.arccos,"atan":np.arctan,"atan2":np.arctan2,
        "sinh":np.sinh,"cosh":np.cosh,"tanh":np.tanh,
        "exp":np.exp,"log":np.log,"log2":np.log2,"log10":np.log10,"ln":np.log,
        "sqrt":np.sqrt,"abs":np.abs,"floor":np.floor,"ceil":np.ceil,
        "sign":np.sign,"round":np.round,
        "pi":np.pi,"e":np.e,"tau":2*np.pi,"inf":np.inf,
        "factorial":np.vectorize(math.factorial),
        "degrees":np.degrees,"radians":np.radians,
        "__builtins__":{},
    }

# ─────────────────────────────────────────────────────────────────────────────
#  PARSER  — understands: y=f(x), x=c, y=c, y=c1 x=c2, bare expr
# ─────────────────────────────────────────────────────────────────────────────
def parse_expr(raw):
    raw = raw.strip()
    pairs = re.findall(r'([xy])\s*=\s*([^,;]+)', raw, re.I)
    if len(pairs) == 2:
        d = {k.lower(): v.strip() for k,v in pairs}
        return {"type":"combined","x":d.get("x"),"y":d.get("y")}
    m = re.match(r'^x\s*=\s*(.+)$', raw, re.I)
    if m: return {"type":"xline","expr":m.group(1).strip()}
    m = re.match(r'^y\s*=\s*(.+)$', raw, re.I)
    expr = m.group(1).strip() if m else raw
    return {"type":"yplot","expr":expr}

# ─────────────────────────────────────────────────────────────────────────────
#  SMART ERROR HINTS
# ─────────────────────────────────────────────────────────────────────────────
ERROR_HINTS = [
    (r"invalid syntax",
     "Syntax error — check your brackets and operators.\n"
     "• Use ** for powers, not ^ (e.g. x**2, not x^2)\n"
     "• Conditions like x>0 won't work directly — try:\n"
     "  np.where(x>0, x, np.nan)   ← only shows when x>0\n"
     "  np.where((x>0)&(x<5), x, np.nan)   ← between 0 and 5"),
    (r"name '(\w+)' is not defined",
     "Unknown name '{0}' — did you mean:\n"
     "• pi  (not π or PI)\n"
     "• e   (Euler's number)\n"
     "• np.sin / sin, np.cos / cos, etc.\n"
     "• If using a condition: np.where(x>0, x, np.nan)"),
    (r"(truth value|ambiguous)",
     "Can't use plain comparisons like x>0 as conditions here.\n"
     "Use np.where instead:\n"
     "  np.where(x > 0, x, np.nan)\n"
     "  np.where((x > 0) & (x < 5), sin(x), np.nan)\n"
     "  ← Use & for AND,  | for OR,  ~ for NOT"),
    (r"division by zero|divide by zero",
     "Division by zero — the function blows up at some x value.\n"
     "The graph will show a gap there automatically.\n"
     "If you want to restrict the domain:\n"
     "  np.where(x != 0, 1/x, np.nan)"),
    (r"overflow",
     "Overflow — the values are getting too large to plot.\n"
     "Try a smaller x range in the Window section, or\n"
     "divide by a large constant to scale it down."),
    (r"could not convert|float conversion",
     "Could not convert to numbers — check your expression.\n"
     "Make sure you're using x as the variable, not t or n."),
]

def smart_hint(err_str, match_groups=None):
    low = err_str.lower()
    for pattern, hint in ERROR_HINTS:
        m = re.search(pattern, low)
        if m:
            try: return hint.format(*m.groups())
            except: return hint
    return (f"Error: {err_str}\n\nGeneral tips:\n"
            "• Use ** for powers  (x**2 not x^2)\n"
            "• Use np.where(condition, value, np.nan) for domains\n"
            "• Example: np.where((x>0) & (x<5), sin(x), np.nan)")

# ─────────────────────────────────────────────────────────────────────────────
#  STYLED WIDGETS
# ─────────────────────────────────────────────────────────────────────────────
def styled_entry(parent, font_size=12, **kw):
    e = tk.Entry(parent, font=(CODE_FONT, font_size),
                 bg=BG3, fg=WHITE, insertbackground=GOLD,
                 bd=0, highlightthickness=1,
                 highlightbackground=BORDER2,
                 highlightcolor=GOLD,
                 relief="flat", **kw)
    return e

def section_bar(parent, text):
    f = tk.Frame(parent, bg=BG1)
    f.pack(fill=tk.X, padx=0, pady=(14,4))
    # gold left accent bar
    tk.Frame(f, bg=GOLD, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(14,8))
    tk.Label(f, text=text, font=(UI_FONT,8,"bold"),
             bg=BG1, fg=GOLD, pady=2).pack(side=tk.LEFT)
    return f

def icon_btn(parent, text, cmd, bg=BG3, fg=WHITE, hover_bg=BG2, hover_fg=GOLD,
             font_size=9, padx=10, pady=5, side=None, fill=None):
    b = tk.Button(parent, text=text, font=(UI_FONT, font_size, "bold"),
                  bg=bg, fg=fg, bd=0, activebackground=hover_bg,
                  activeforeground=hover_fg, cursor="hand2",
                  command=cmd, padx=padx, pady=pady, relief="flat")
    if side:   b.pack(side=side, padx=2, pady=1)
    elif fill: b.pack(fill=fill, padx=0, pady=1)
    else:      b.pack(padx=2, pady=1)
    def _enter(e): b.config(bg=hover_bg, fg=hover_fg)
    def _leave(e): b.config(bg=bg, fg=fg)
    b.bind("<Enter>", _enter)
    b.bind("<Leave>", _leave)
    return b

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GraphCalc")
        self.geometry("1220x800")
        self.minsize(900, 600)
        self.configure(bg=BG0)
        self.resizable(True, True)

        self.eqs   = []
        self.cidx  = 0
        self.xmin  = tk.DoubleVar(value=-10)
        self.xmax  = tk.DoubleVar(value=10)
        self.ymin  = tk.DoubleVar(value=-10)
        self.ymax  = tk.DoubleVar(value=10)

        # pan/zoom state
        self._pan_start = None
        self._pan_xlim  = None
        self._pan_ylim  = None

        self._build_ui()
        self._draw()

    # ─────────────────────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── HEADER BAR ───────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG0, height=58)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        # logo
        logo = tk.Frame(hdr, bg=BG0)
        logo.pack(side=tk.LEFT, padx=22, pady=10)
        tk.Label(logo, text="◈", font=(UI_FONT,22), bg=BG0, fg=GOLD).pack(side=tk.LEFT)
        tk.Label(logo, text=" GraphCalc", font=(UI_FONT,18,"bold"), bg=BG0, fg=WHITE).pack(side=tk.LEFT)

        # controls top-right
        ctrl = tk.Frame(hdr, bg=BG0)
        ctrl.pack(side=tk.RIGHT, padx=16)
        tk.Label(ctrl, text="scroll to zoom  •  drag to pan  •  right-click resets view",
                 font=(UI_FONT,8), bg=BG0, fg=DIM2).pack(side=tk.RIGHT, padx=8)

        # thin gold line under header
        tk.Frame(self, bg=GOLD, height=1).pack(fill=tk.X)
        tk.Frame(self, bg=BG0, height=1).pack(fill=tk.X)

        # ── BODY ─────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG0)
        body.pack(fill=tk.BOTH, expand=True)

        # LEFT SIDEBAR
        sidebar = tk.Frame(body, bg=BG1, width=295)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # thin separator
        tk.Frame(body, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # RIGHT GRAPH
        graph_area = tk.Frame(body, bg=BG0)
        graph_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar(sidebar)
        self._build_graph(graph_area)

    # ─────────────────────────────────────────────────────────────────────
    #  SIDEBAR
    # ─────────────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        # make it scrollable
        outer = tk.Frame(parent, bg=BG1)
        outer.pack(fill=tk.BOTH, expand=True)
        cv = tk.Canvas(outer, bg=BG1, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL, command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        inner = tk.Frame(cv, bg=BG1)
        win_id = cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(win_id, width=e.width))
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))

        p = inner  # shorthand

        # ── EXPRESSION INPUT ─────────────────────────────────────────────
        section_bar(p, "PLOT EXPRESSION")

        inp_wrap = tk.Frame(p, bg=BG2, highlightbackground=BORDER2, highlightthickness=1)
        inp_wrap.pack(fill=tk.X, padx=14, pady=2)

        self.expr_entry = styled_entry(inp_wrap, font_size=13)
        self.expr_entry.insert(0, "sin(x)")
        self.expr_entry.pack(fill=tk.X, padx=10, pady=(10,4))
        self.expr_entry.bind("<Return>", lambda e: self._add())
        self.expr_entry.bind("<FocusIn>",  lambda e: inp_wrap.config(highlightbackground=GOLD))
        self.expr_entry.bind("<FocusOut>", lambda e: inp_wrap.config(highlightbackground=BORDER2))

        # syntax hint
        self.hint_lbl = tk.Label(inp_wrap,
            text="y=sin(x)  •  x=3  •  y=2, x=-1  •  x**2-1",
            font=(UI_FONT,8), bg=BG2, fg=DIM, wraplength=250, justify=tk.LEFT, anchor=tk.W)
        self.hint_lbl.pack(fill=tk.X, padx=10, pady=(0,6))

        btn_row = tk.Frame(inp_wrap, bg=BG2)
        btn_row.pack(fill=tk.X, padx=8, pady=(0,10))
        icon_btn(btn_row, "+ PLOT", self._add,
                 bg=GOLD, fg=BG0, hover_bg=GOLD2, hover_fg=BG0,
                 font_size=10, padx=16, pady=7, side=tk.LEFT)
        icon_btn(btn_row, "CLEAR ALL", self._clear,
                 bg=BG3, fg=DIM, hover_bg=RED, hover_fg=WHITE,
                 font_size=9, padx=10, pady=7, side=tk.LEFT)

        # ── ACTIVE PLOTS LIST ────────────────────────────────────────────
        section_bar(p, "ACTIVE PLOTS")
        self.list_frame = tk.Frame(p, bg=BG1)
        self.list_frame.pack(fill=tk.X, padx=14)

        # ── VECTOR SECTION ───────────────────────────────────────────────
        section_bar(p, "VECTORS")
        vec_card = tk.Frame(p, bg=BG2, highlightbackground=BORDER2, highlightthickness=1)
        vec_card.pack(fill=tk.X, padx=14, pady=2)

        # Vector A
        va_row = tk.Frame(vec_card, bg=BG2)
        va_row.pack(fill=tk.X, padx=10, pady=(10,4))
        tk.Label(va_row, text="A =", font=(CODE_FONT,12,"bold"),
                 bg=BG2, fg=TEAL, width=3).pack(side=tk.LEFT)
        tk.Label(va_row, text="x:", font=(CODE_FONT,11),
                 bg=BG2, fg=DIM).pack(side=tk.LEFT, padx=(4,2))
        self.vax = styled_entry(va_row, font_size=11, width=6)
        self.vax.insert(0, "3")
        self.vax.pack(side=tk.LEFT, ipady=3, padx=(0,6))
        tk.Label(va_row, text="y:", font=(CODE_FONT,11),
                 bg=BG2, fg=DIM).pack(side=tk.LEFT, padx=(0,2))
        self.vay = styled_entry(va_row, font_size=11, width=6)
        self.vay.insert(0, "4")
        self.vay.pack(side=tk.LEFT, ipady=3)

        # Vector B
        vb_row = tk.Frame(vec_card, bg=BG2)
        vb_row.pack(fill=tk.X, padx=10, pady=(0,4))
        tk.Label(vb_row, text="B =", font=(CODE_FONT,12,"bold"),
                 bg=BG2, fg=GOLD, width=3).pack(side=tk.LEFT)
        tk.Label(vb_row, text="x:", font=(CODE_FONT,11),
                 bg=BG2, fg=DIM).pack(side=tk.LEFT, padx=(4,2))
        self.vbx = styled_entry(vb_row, font_size=11, width=6)
        self.vbx.insert(0, "1")
        self.vbx.pack(side=tk.LEFT, ipady=3, padx=(0,6))
        tk.Label(vb_row, text="y:", font=(CODE_FONT,11),
                 bg=BG2, fg=DIM).pack(side=tk.LEFT, padx=(0,2))
        self.vby = styled_entry(vb_row, font_size=11, width=6)
        self.vby.insert(0, "2")
        self.vby.pack(side=tk.LEFT, ipady=3)

        # Vector result display
        self.vec_res = tk.Label(vec_card, text="", font=(CODE_FONT,10),
                                bg=BG2, fg=TEAL, anchor=tk.W, wraplength=240, justify=tk.LEFT)
        self.vec_res.pack(fill=tk.X, padx=10, pady=(2,4))

        # Vector buttons grid
        vbtn = tk.Frame(vec_card, bg=BG2)
        vbtn.pack(fill=tk.X, padx=8, pady=(0,10))
        vec_actions = [
            ("Plot A",    self._vec_plot_a),
            ("Plot B",    self._vec_plot_b),
            ("Plot A+B",  self._vec_add),
            ("A · B",     self._vec_dot),
            ("|A|",       self._vec_mag_a),
            ("|B|",       self._vec_mag_b),
            ("Angle",     self._vec_angle),
            ("Clear",     self._vec_clear),
        ]
        for i,(txt,cmd) in enumerate(vec_actions):
            b = tk.Button(vbtn, text=txt, font=(UI_FONT,9),
                          bg=BG3, fg=WHITE, bd=0, activebackground=BORDER2,
                          activeforeground=GOLD, cursor="hand2",
                          command=cmd, padx=6, pady=5)
            b.grid(row=i//4, column=i%4, padx=2, pady=2, sticky="ew")
            b.bind("<Enter>", lambda e,b=b: b.config(bg=BORDER2,fg=GOLD))
            b.bind("<Leave>", lambda e,b=b: b.config(bg=BG3,fg=WHITE))
        for c in range(4): vbtn.columnconfigure(c,weight=1)

        # ── WINDOW / RANGE ───────────────────────────────────────────────
        section_bar(p, "WINDOW")
        wnd = tk.Frame(p, bg=BG1)
        wnd.pack(fill=tk.X, padx=14, pady=2)
        for i,(lbl,var) in enumerate([("x min",self.xmin),("x max",self.xmax),
                                       ("y min",self.ymin),("y max",self.ymax)]):
            row = tk.Frame(wnd, bg=BG1)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=lbl, font=(UI_FONT,9), bg=BG1, fg=DIM, width=6, anchor=tk.W
                     ).pack(side=tk.LEFT)
            e = styled_entry(row, font_size=11, width=8)
            e.insert(0, str(int(var.get())))
            e.pack(side=tk.LEFT, ipady=4, padx=(4,0))
            e.bind("<FocusOut>", lambda ev, v=var, en=e: self._apply_range(v, en))
            e.bind("<Return>",   lambda ev, v=var, en=e: self._apply_range(v, en))
            var._entry = e

        wbtn = tk.Frame(p, bg=BG1)
        wbtn.pack(fill=tk.X, padx=14, pady=4)
        icon_btn(wbtn, "APPLY",    self._draw,  BG3,  GOLD,  BORDER2, GOLD, side=tk.LEFT)
        icon_btn(wbtn, "RESET VIEW",self._reset, BG3, DIM,   BORDER2, WHITE, side=tk.LEFT)

        # ── KEYPAD ───────────────────────────────────────────────────────
        section_bar(p, "KEYPAD")
        kp = tk.Frame(p, bg=BG1)
        kp.pack(fill=tk.X, padx=14, pady=(0,6))
        keys = [
            [("sin(","fn"),("cos(","fn"),("tan(","fn"),("sqrt(","fn")],
            [("log(","fn"),("ln(","fn"), ("abs(","fn"),("exp(","fn")],
            [("pi","const"),("e","const"),("**2","op"),("**","op")],
            [("7","num"),("8","num"),("9","num"),("/","op")],
            [("4","num"),("5","num"),("6","num"),("*","op")],
            [("1","num"),("2","num"),("3","num"),("-","op")],
            [("0","num"),(".","num"),("(","op"),(")","op")],
        ]
        style_map = {
            "fn":    (BG0,    TEAL,  BG3,    TEAL),
            "const": (BG0,    GOLD,  BG3,    GOLD),
            "op":    (BG3,    DIM,   BORDER2,WHITE),
            "num":   (BG2,    WHITE, BG3,    WHITE),
        }
        for r,row in enumerate(keys):
            for c,(k,kind) in enumerate(row):
                nb,nf,hb,hf = style_map[kind]
                b = tk.Button(kp, text=k, font=(CODE_FONT,10),
                              bg=nb, fg=nf, bd=0, cursor="hand2",
                              activebackground=hb, activeforeground=hf,
                              command=lambda v=k: self._kp(v))
                b.grid(row=r, column=c, padx=1, pady=1, sticky="nsew", ipady=7)
                b.bind("<Enter>", lambda e,b=b,hb=hb,hf=hf: b.config(bg=hb,fg=hf))
                b.bind("<Leave>", lambda e,b=b,nb=nb,nf=nf: b.config(bg=nb,fg=nf))
            kp.rowconfigure(r, weight=1)
        for c in range(4): kp.columnconfigure(c, weight=1)

        # ── ERROR / HINT BOX ─────────────────────────────────────────────
        section_bar(p, "TIPS & FIXES")
        err_outer = tk.Frame(p, bg=BG2, highlightbackground=BORDER, highlightthickness=1)
        err_outer.pack(fill=tk.X, padx=14, pady=(2,16))
        self.error_lbl = tk.Label(err_outer,
            text="Errors will show here with fix suggestions.",
            font=(UI_FONT,9), bg=BG2, fg=DIM,
            wraplength=245, justify=tk.LEFT, anchor=tk.NW,
            pady=10, padx=10)
        self.error_lbl.pack(fill=tk.X)

    # ─────────────────────────────────────────────────────────────────────
    #  GRAPH AREA
    # ─────────────────────────────────────────────────────────────────────
    def _build_graph(self, parent):
        self.fig = plt.Figure(figsize=(8, 7), dpi=100)
        self.fig.patch.set_facecolor(BG0)
        self.ax = self.fig.add_subplot(111)
        self._style_ax()

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # coord bar
        coord_bar = tk.Frame(parent, bg=BG1, height=26)
        coord_bar.pack(fill=tk.X)
        coord_bar.pack_propagate(False)
        self.coord_lbl = tk.Label(coord_bar, text="",
                                  font=(CODE_FONT,9), bg=BG1, fg=DIM, anchor=tk.W)
        self.coord_lbl.pack(side=tk.LEFT, padx=14)

        # ── MOUSE EVENTS ─────────────────────────────────────────────────
        self.canvas.mpl_connect("motion_notify_event",  self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event",   self._on_press)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event",  self._on_drag)
        self.canvas.mpl_connect("scroll_event",         self._on_scroll)
        # right click resets view
        self.canvas.mpl_connect("button_press_event",   self._on_right_click)

    def _style_ax(self):
        ax = self.ax
        ax.set_facecolor("#09090d")
        ax.tick_params(colors=DIM2, labelsize=9, which="both", length=3)
        ax.grid(True, color="#1a1a22", linestyle="-", linewidth=0.7, zorder=0)
        ax.axhline(0, color=BORDER2, lw=0.9, zorder=1)
        ax.axvline(0, color=BORDER2, lw=0.9, zorder=1)
        for s in ax.spines.values():
            s.set_color(BORDER); s.set_linewidth(0.8)
        ax.set_xlim(self.xmin.get(), self.xmax.get())
        ax.set_ylim(self.ymin.get(), self.ymax.get())
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_color(DIM2)
        self.fig.tight_layout(pad=1.4)

    # ─────────────────────────────────────────────────────────────────────
    #  DRAW
    # ─────────────────────────────────────────────────────────────────────
    def _draw(self, *_):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.clear()
        self._style_ax()
        self.ax.set_xlim(xlim); self.ax.set_ylim(ylim)

        errors = []
        legend_items = []

        for eq in self.eqs:
            if not eq["on"]: continue
            eq["err"] = None
            c = eq["color"]
            try:
                p = parse_expr(eq["expr"])
                x = np.linspace(xlim[0], xlim[1], 3000)

                if p["type"] == "combined":
                    xexpr, yexpr = p.get("x"), p.get("y")
                    xv = float(eval(xexpr, make_ns())) if xexpr else None
                    yv_raw = eval(yexpr, make_ns(x)) if yexpr else None
                    is_const_y = yv_raw is not None and np.ndim(yv_raw) == 0

                    if xv is not None and is_const_y:
                        # single point
                        px, py = float(xv), float(yv_raw)
                        self.ax.plot(px, py, "o", color=c, markersize=9, zorder=6,
                                     markeredgewidth=1.5, markeredgecolor=BG0)
                        self.ax.annotate(f"({px:g}, {py:g})", (px, py),
                            xytext=(10,10), textcoords="offset points", color=c,
                            fontsize=9, fontfamily=CODE_FONT,
                            bbox=dict(boxstyle="round,pad=0.3", fc=BG2, ec=c, lw=1))
                        legend_items.append((c, eq["expr"]))
                    else:
                        if xv is not None:
                            l, = self.ax.plot([xv,xv], ylim, color=c, lw=1.5,
                                              linestyle="--", zorder=3)
                            legend_items.append((c, f"x = {xv:g}"))
                        if yexpr and yv_raw is not None:
                            if is_const_y:
                                yc = float(yv_raw)
                                self.ax.axhline(yc, color=c, lw=1.5, linestyle="--", zorder=3)
                                legend_items.append((c, f"y = {yc:g}"))
                            else:
                                y = np.where(np.isfinite(np.atleast_1d(yv_raw).astype(float)),
                                             yv_raw, np.nan)
                                self.ax.plot(x, y, color=c, lw=2.2, zorder=3)
                                legend_items.append((c, eq["expr"]))

                elif p["type"] == "xline":
                    xv = float(eval(p["expr"], make_ns()))
                    self.ax.axvline(xv, color=c, lw=1.8, linestyle="--", zorder=3)
                    legend_items.append((c, f"x = {xv:g}"))

                else:
                    y = eval(p["expr"], make_ns(x))
                    y = np.where(np.isfinite(np.atleast_1d(y).astype(float)), y, np.nan)
                    if np.ndim(y) == 0 or (hasattr(y,"size") and y.size == 1):
                        yc = float(np.atleast_1d(y)[0])
                        self.ax.axhline(yc, color=c, lw=1.8, linestyle="--", zorder=3)
                        legend_items.append((c, f"y = {yc:g}"))
                    else:
                        self.ax.plot(x, y, color=c, lw=2.2, zorder=3)
                        legend_items.append((c, eq["expr"]))

            except Exception as ex:
                eq["err"] = str(ex)
                errors.append((eq["expr"], str(ex)))

        # legend
        if legend_items:
            handles = [mpatches.Patch(color=c, label=lbl) for c,lbl in legend_items]
            self.ax.legend(handles=handles, facecolor=BG2, edgecolor=BORDER2,
                           labelcolor=WHITE, fontsize=9, loc="upper right",
                           framealpha=0.95, prop={"family": CODE_FONT, "size": 9})

        self.canvas.draw()
        self._rebuild_list()
        self._show_errors(errors)

    def _show_errors(self, errors):
        if not errors:
            self.error_lbl.config(
                text="No errors. Scroll to zoom, drag to pan, right-click to reset.",
                fg=DIM)
            return
        expr, err = errors[-1]
        hint = smart_hint(err)
        self.error_lbl.config(
            text=f"⚠  \"{expr}\"\n\n{hint}",
            fg=GOLD, bg=BG2)

    # ─────────────────────────────────────────────────────────────────────
    #  PAN / ZOOM / MOUSE
    # ─────────────────────────────────────────────────────────────────────
    def _on_scroll(self, event):
        if event.inaxes != self.ax: return
        factor = 0.88 if event.button == "up" else 1.0/0.88
        xc, yc = event.xdata, event.ydata
        xl, xr = self.ax.get_xlim()
        yb, yt = self.ax.get_ylim()
        self.ax.set_xlim(xc + (xl-xc)*factor, xc + (xr-xc)*factor)
        self.ax.set_ylim(yc + (yb-yc)*factor, yc + (yt-yc)*factor)
        self.canvas.draw_idle()

    def _on_press(self, event):
        if event.button == 1 and event.inaxes == self.ax:
            self._pan_start = (event.x, event.y)
            self._pan_xlim  = self.ax.get_xlim()
            self._pan_ylim  = self.ax.get_ylim()

    def _on_release(self, event):
        if event.button == 1:
            self._pan_start = None

    def _on_drag(self, event):
        if self._pan_start is None or event.inaxes != self.ax: return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        xl, xr = self._pan_xlim
        yb, yt = self._pan_ylim
        w = xr - xl; h = yt - yb
        bbox = self.ax.get_window_extent()
        px = dx / bbox.width  * w
        py = dy / bbox.height * h
        self.ax.set_xlim(xl - px, xr - px)
        self.ax.set_ylim(yb + py, yt + py)
        self.canvas.draw_idle()

    def _on_right_click(self, event):
        if event.button == 3:
            self.ax.set_xlim(self.xmin.get(), self.xmax.get())
            self.ax.set_ylim(self.ymin.get(), self.ymax.get())
            self.canvas.draw_idle()

    def _on_mouse_move(self, event):
        if event.inaxes == self.ax:
            self.coord_lbl.config(
                text=f"  x = {event.xdata:+.4f}   y = {event.ydata:+.4f}")

    # ─────────────────────────────────────────────────────────────────────
    #  EQUATION MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────
    def _add(self):
        raw = self.expr_entry.get().strip()
        if not raw: return
        c = PLOT_COLORS[self.cidx % len(PLOT_COLORS)]
        self.cidx += 1
        self.eqs.append({"expr":raw,"color":c,"on":True,"err":None})
        self.expr_entry.delete(0, tk.END)
        self._draw()

    def _rebuild_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        if not self.eqs:
            tk.Label(self.list_frame, text="no plots yet",
                     font=(UI_FONT,9), bg=BG1, fg=DIM2).pack(anchor=tk.W)
            return
        for i, eq in enumerate(self.eqs):
            row = tk.Frame(self.list_frame, bg=BG2,
                           highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill=tk.X, pady=2)
            # colored strip
            tk.Frame(row, bg=eq["color"], width=4).pack(side=tk.LEFT, fill=tk.Y)
            txt = eq["expr"][:26] + ("…" if len(eq["expr"])>26 else "")
            fg = RED if eq.get("err") else WHITE
            tk.Label(row, text=txt, font=(CODE_FONT,10), bg=BG2, fg=fg,
                     anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
            # toggle
            vis = eq["on"]
            vb = tk.Button(row, text="◉" if vis else "◎",
                           font=(UI_FONT,11), bg=BG2, fg=GOLD if vis else DIM2,
                           bd=0, activebackground=BG2, cursor="hand2",
                           command=lambda idx=i: self._toggle(idx))
            vb.pack(side=tk.LEFT, padx=2)
            # delete
            tk.Button(row, text="✕", font=(UI_FONT,10), bg=BG2, fg=DIM2,
                      bd=0, activebackground=BG2, cursor="hand2",
                      activeforeground=RED,
                      command=lambda idx=i: self._del(idx)).pack(side=tk.LEFT, padx=(0,6))

    def _toggle(self, i): self.eqs[i]["on"] = not self.eqs[i]["on"]; self._draw()
    def _del(self, i):    self.eqs.pop(i); self._draw()
    def _clear(self):     self.eqs.clear(); self.cidx=0; self._draw()

    # ─────────────────────────────────────────────────────────────────────
    #  VECTORS
    # ─────────────────────────────────────────────────────────────────────
    def _get_vecs(self):
        ns0 = make_ns()
        ax_val = float(eval(self.vax.get(), ns0))
        ay_val = float(eval(self.vay.get(), ns0))
        bx_val = float(eval(self.vbx.get(), ns0))
        by_val = float(eval(self.vby.get(), ns0))
        return np.array([ax_val, ay_val]), np.array([bx_val, by_val])

    def _draw_arrow(self, dx, dy, color, label="", origin=(0,0)):
        ox, oy = origin
        self.ax.annotate("", xy=(ox+dx, oy+dy), xytext=(ox, oy),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2,
                            mutation_scale=16))
        mag = math.sqrt(dx**2 + dy**2)
        mx, my = ox + dx*0.55, oy + dy*0.55
        self.ax.text(mx, my, f" {label} ({mag:.3g})", color=color,
                     fontsize=9, fontfamily=CODE_FONT,
                     bbox=dict(boxstyle="round,pad=0.2", fc=BG2, ec=color, lw=0.8))
        self.ax.plot(ox+dx, oy+dy, "o", color=color, markersize=5, zorder=7)

    def _vec_plot_a(self):
        try:
            a, _ = self._get_vecs(); self._draw_arrow(*a, TEAL, "A"); self.canvas.draw()
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_plot_b(self):
        try:
            _, b = self._get_vecs(); self._draw_arrow(*b, GOLD, "B"); self.canvas.draw()
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_add(self):
        try:
            a, b = self._get_vecs()
            self._draw_arrow(*a, TEAL, "A")
            self._draw_arrow(*b, GOLD, "B", origin=tuple(a))
            r = a + b
            self._draw_arrow(*r, WHITE, "A+B")
            self.vec_res.config(text=f"A+B = ({r[0]:g}, {r[1]:g})", fg=WHITE)
            self.canvas.draw()
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_dot(self):
        try:
            a, b = self._get_vecs()
            d = float(np.dot(a, b))
            self.vec_res.config(text=f"A · B = {d:.6g}", fg=TEAL)
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_mag_a(self):
        try:
            a, _ = self._get_vecs()
            self.vec_res.config(text=f"|A| = {np.linalg.norm(a):.6g}", fg=TEAL)
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_mag_b(self):
        try:
            _, b = self._get_vecs()
            self.vec_res.config(text=f"|B| = {np.linalg.norm(b):.6g}", fg=GOLD)
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_angle(self):
        try:
            a, b = self._get_vecs()
            cosθ = np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))
            deg  = math.degrees(math.acos(max(-1, min(1, float(cosθ)))))
            self.vec_res.config(text=f"Angle = {deg:.4g}°", fg=GOLD)
        except Exception as e: self.vec_res.config(text=f"Error: {e}", fg=RED)

    def _vec_clear(self):
        self._draw()
        self.vec_res.config(text="", fg=TEAL)

    # ─────────────────────────────────────────────────────────────────────
    #  RANGE / WINDOW
    # ─────────────────────────────────────────────────────────────────────
    def _apply_range(self, var, entry):
        try: var.set(float(entry.get()))
        except: pass

    def _reset(self):
        self.xmin.set(-10); self.xmax.set(10)
        self.ymin.set(-10); self.ymax.set(10)
        self.ax.set_xlim(-10,10); self.ax.set_ylim(-10,10)
        self._draw()

    # ─────────────────────────────────────────────────────────────────────
    #  KEYPAD
    # ─────────────────────────────────────────────────────────────────────
    def _kp(self, v):
        w = self.focus_get()
        target = self.expr_entry
        if w in (self.vax, self.vay, self.vbx, self.vby): target = w
        target.insert(tk.INSERT, v)
        target.focus()


if __name__ == "__main__":
    App().mainloop()