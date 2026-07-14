"""
learning_bot_gui.py  (v6)

A chatbot with a sci-fi HUD interface. No AI/ML libraries -- just
Python's standard library (tkinter for everything).

WHAT'S NEW IN v6
------------------------
1) SMARTER REPLIES
   - RESPONSE_BANK entries are now scored (keyword-overlap) instead of
     "first substring match wins", so the bot picks the BEST match,
     not just the first thing that happens to appear in your text.
   - No more endless re-greeting: the bot remembers it already said hi
     and switches to "we already did hellos" replies after the first one.
   - Recently-used replies are tracked per category so it stops
     repeating itself.
   - New REFLECTION fallback: when nothing in the bank fits and the
     word-chain generator produces something too short/weak, the bot
     falls back to an ELIZA-style reflective question built from your
     own words ("why do you think you feel tired?") instead of babble.
   - Word-chain fallback (chain4->chain1) is unchanged under the hood
     but now only kicks in as a last resort.

2) PERSONA MODES (replaces the old single slang slider)
   - CHILL / CHAOTIC / SARCASTIC / WHOLESOME
   - Each mode has its own filler words, reply energy, and how often
     it interrupts with asides. This is the "make it say more shit"
     button -- no fetish content, just more personality.

3) LOOK
   - New color palette, chat-bubble-styled log (background + margins
     per speaker instead of plain text), animated "thinking..." beat
     before the bot replies, nicer header/avatar, hover states on
     buttons, restyled tabs and calculator.

4) SIDE PANEL
   - PERSONALITY tab: persona mode selector, live stats, wipe-memory.
   - CALCULATOR tab: working calculator.
   - NOTES tab: persistent scratchpad (saves to notes.txt).

Run it with:  python learning_bot_gui.py
"""

import ast
import json
import operator
import os
import queue
import random
import re
import threading
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import scrolledtext, font, messagebox

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
BRAIN_FILE = "brain.json"
NOTES_FILE = "notes.txt"
MAX_HISTORY = 100
MAX_REPLY_LEN = 16
MIN_REPLY_LEN = 4
NO_REPEAT_LAST_N = 6
GENERATION_ATTEMPTS = 8
REINFORCE_STRENGTH = 3
THINK_DELAY_MS = (350, 900)  # min, max fake "thinking" delay
GREETING_STARTER_BLOCK = {"hello", "hi", "hey", "yo", "sup", "wassup"}

# ---------------------------------------------------------------
# THEME
# ---------------------------------------------------------------
BG = "#020810"
PANEL_BG = "#061420"
PANEL_BG_2 = "#0b1f30"
BUBBLE_USER = "#0c2438"
BUBBLE_BOT = "#0a1c34"
BORDER = "#123650"
GLOW = "#5fd4ff"
ACCENT = "#5fd4ff"
ACCENT_DIM = "#164a63"
MAGENTA = "#ff5fd0"
VIOLET = "#8a6bff"
TEXT_MAIN = "#eaf9ff"
TEXT_DIM = "#5a7a90"
GOOD_COLOR = "#2bff9c"
BAD_COLOR = "#ff4d6a"
MONO_FAMILY = "Consolas"
UI_FAMILY = "Segoe UI"

PULSE_COLORS = [ACCENT, "#8fe6ff", "#bff3ff", "#8fe6ff", VIOLET]

# ---------------------------------------------------------------
# BOOTSTRAP VOCABULARY (auto-learned once, on the very first run)
# ---------------------------------------------------------------
SEED_STARTERS = ["hello", "hi", "hey", "what", "i", "how"]

SEED_CHAIN1 = {
    "hello": {"there": 3, "how": 2, "i": 1},
    "how": {"are": 4, "is": 1},
    "are": {"you": 5},
    "you": {"doing": 2, "there": 1, "good": 1},
    "i": {"am": 3, "think": 2, "like": 1},
    "am": {"good": 2, "fine": 2, "okay": 1},
    "what": {"is": 2, "do": 1, "are": 1},
    "is": {"up": 2, "going": 1, "it": 1},
    "yes": {"i": 1},
    "no": {"i": 1},
}

BOOTSTRAP_SENTENCES = [
    "hello there how are you doing today",
    "i am doing well thank you for asking",
    "what do you like to talk about",
    "i think that sounds like a good idea",
    "that is really interesting tell me more",
    "i am not sure but i would like to know",
    "thank you very much for saying that",
    "i like talking with you about this",
    "what is your favorite thing to do",
    "i had a good day today how about you",
    "that made me happy to hear",
    "i am sorry to hear that",
    "can you tell me more about that",
    "i understand what you mean",
    "that is a great question",
    "i want to learn more about that",
    "how was your day today",
    "i feel good about this conversation",
    "that sounds like a lot of fun",
    "i agree with what you said",
    "i am still learning so please be patient with me",
    "what should we talk about next",
    "i think you are right about that",
    "that is a funny thing to say",
    "i hope you are having a good time",
    "i am excited to learn new words",
    "that is something i had not thought about before",
    "i would like to hear your opinion on that",
    "thank you for teaching me new things",
    "i am curious what you think about that",
    "my favorite thing to do is talk with people",
    "i really enjoy learning new words every day",
    "that is a cool way to think about it",
    "i am doing my best to understand you",
    "what kind of things do you enjoy doing",
    "i think computers and technology are pretty interesting",
    "artificial intelligence is a fascinating topic to learn about",
    "i am a small program that learns from what you type",
    "the more you talk to me the smarter i get",
    "i do not know everything but i am learning fast",
    "that is a great point i had not considered",
    "i think games can be a lot of fun",
    "do you have a favorite hobby or activity",
    "i like hearing about what other people enjoy",
    "sometimes learning new things takes a little bit of time",
    "i am glad we are having this conversation",
    "what made you think of that",
    "that is a good question let me think about it",
    "i want to get better at talking with you",
    "i think that makes a lot of sense",
    "you can teach me new words any time you want",
    "i remember what you tell me and try to use it",
    "that is pretty cool i did not know that",
    "i am always trying to learn something new",
    "what do you think about that idea",
    "i think it would be fun to talk more",
    "sometimes i say strange things because i am still learning",
    "please let me know if i say something wrong",
    "i appreciate you taking the time to teach me",
    "that is a nice way to put it",
    "i think we can figure this out together",
    "what does that word mean to you",
    "i like when you explain things to me",
    "that helps me understand a little bit better",
    "i am trying my best to make sense here",
    "you seem like a pretty interesting person",
    "i think talking to people helps me learn faster",
    "what is something you learned recently",
    "i find that pretty fascinating honestly",
    "that is a good way to describe it",
    "i think i am starting to understand this better",
    "can you give me an example of that",
    "i like when conversations go in unexpected directions",
    "that reminds me of something you said earlier",
    "i think patience is important when learning something new",
    "what would you like to teach me today",
    "i am happy to keep chatting with you",
    "that is a really good observation",
    "i think i understand what you are getting at",
    "you make some really good points",
    "i want to sound more like you over time",
    "that is exactly the kind of thing i want to learn",
    "i think practice makes a big difference",
    "what should i say back to that",
    "i am not perfect but i am improving",
    "that is a clever way of looking at it",
    "i think i will remember that one",
    "you have taught me a lot already",
    "i think that is a fair point",
    "what happens next in this conversation",
    "i like how this is going so far",
    "that is worth thinking about some more",
    "i think i can work with that",
    "you are helping me get smarter every day",
    "i think that is a solid answer",
    "what other topics should we cover",
    "i am ready to learn whatever you want to teach",
    "that is a neat little detail",
    "i think this is going pretty well",
    "you clearly know a lot about that",
    "i think i should ask more questions",
    "what do you find most interesting about that",
    "i like learning things step by step",
    "that is a helpful way to explain it",
    "i think i am getting the hang of this",
    "you make it easy to understand",
    "i think that is worth remembering",
    "what is on your mind right now",
    "i am glad you are here talking with me",
    "that is a good place to start",
    "sup what are you up to",
    "yo hows it going",
    "not much just chilling what about you",
    "lol thats pretty funny ngl",
    "nah i dont think thats it",
    "fr that is actually kind of wild",
    "bro that is crazy",
    "idk maybe we should try something else",
    "yeah that sounds good to me",
    "haha okay that makes sense",
    "wait really thats cool",
    "no way thats actually insane",
    "for sure lets do that",
    "same honestly i feel that",
    "thats fair i get what you mean",
    "ngl that kind of slaps",
    "yo that game is actually really fun",
    "lol i was just thinking about that too",
    "bet lets go do that then",
    "honestly same here",
    "thats lowkey a good point",
    "ok that actually makes a lot of sense",
    "damn thats actually pretty smart",
    "yeah nah i see what you mean",
    "lol dude you are funny",
    "aight bet lets talk about that",
]

EXTRA_PHRASES = [
    "wassup with you today",
    "yo that is actually really cool",
    "lol no way that happened",
    "bro i cant believe that",
    "haha yeah thats about right",
    "ngl i did not expect that",
    "fr thats wild ngl",
    "bet ill catch up with you later",
    "nah man that is not it",
    "lowkey that kind of makes sense",
    "highkey i love that idea",
    "dude that is actually amazing",
    "im down for that lets go",
    "thats a mood honestly",
    "yeah for real i feel you",
    "no cap that is impressive",
    "that is actually a solid point ngl",
    "lol you are not wrong",
    "aight i see what you did there",
    "yo lets figure this out together",
]

# ---------------------------------------------------------------
# INSTANT RESPONSE BANK
# Each entry: category (used to avoid repeats / detect re-greets),
# keywords (substrings to score against), replies, and an optional
# "repeat" set used once that category has already fired this session.
# ---------------------------------------------------------------
RESPONSE_BANK = [
    dict(category="greeting",
         keywords=["hello", "hi ", "hi there", "hey", "yo", "sup", "wassup", "whats up"],
         replies=["hey whats good", "yo whats up", "sup how you doing",
                  "hey there, good to see you"],
         repeat=["we already did hellos, whats actually on your mind",
                 "back again huh, whats up this time",
                 "you keep saying hi lol, talk to me for real",
                 "haha ok we've said hi like three times now, hit me with something else"]),

    dict(category="how_are_you",
         keywords=["how are you", "hows it going", "how you doing", "how you doin",
                    "how are things"],
         replies=["im doing pretty good honestly how about you",
                  "cant complain hows it going with you",
                  "im good just vibing what about you"],
         repeat=["still doing fine, you already asked lol, whats new with you",
                 "same as five minutes ago, good. what else is going on"]),

    dict(category="identity",
         keywords=["who are you", "what are you"],
         replies=["im a little chat program that learns how you talk",
                  "just a bot built to pick up on your vibe and talk back",
                  "im an ai thats still learning but im figuring it out"],
         repeat=["still the same bot as last time you asked haha"]),

    dict(category="name",
         keywords=["your name", "whats your name"],
         replies=["i dont really have a name yet you could give me one",
                  "no official name just call me bot for now"],
         repeat=["still nameless, you never gave me one"]),

    dict(category="farewell",
         keywords=["bye", "goodbye", "see you", "gotta go", "im out"],
         replies=["alright catch you later", "see ya take care",
                  "bet ill be here whenever you wanna talk again"],
         repeat=["ok bye for real this time"]),

    dict(category="thanks",
         keywords=["thank you", "thanks", "thx"],
         replies=["no worries anytime", "of course happy to help",
                  "all good glad that worked out"],
         repeat=["seriously no problem"]),

    dict(category="capability",
         keywords=["what can you do", "what do you do"],
         replies=["i chat with you and pick up on how you talk over time",
                  "mostly just talking and learning your style as we go"],
         repeat=["same answer as before, mostly just talking and learning"]),

    dict(category="joke",
         keywords=["tell me a joke", "say something funny", "make me laugh"],
         replies=["why did the computer get cold, it left its windows open",
                  "i tried to think of a joke but my memory is still loading",
                  "why dont robots panic, they have great cache under pressure"],
         repeat=["i only know like three jokes and you heard them already"]),

    dict(category="affection",
         keywords=["i love you"],
         replies=["thats sweet i appreciate you too", "aw thanks that means a lot"],
         repeat=["you keep saying that, im flattered, still just a bot though"]),

    dict(category="insult",
         keywords=["i hate you", "you suck", "youre dumb", "youre stupid"],
         replies=["harsh but ill try to do better", "damn ok noted ill work on it",
                  "thats fair im still figuring stuff out"],
         repeat=["ok you really dont like me huh, noted again"]),

    dict(category="praise",
         keywords=["good job", "well done", "youre smart", "nice one", "youre cool"],
         replies=["thanks i appreciate that", "haha thanks that means a lot",
                  "appreciate you saying that"],
         repeat=["you're too kind, seriously"]),

    dict(category="are_you_real",
         keywords=["are you real", "are you human", "are you a robot", "are you ai"],
         replies=["im a program running on your computer not a real person",
                  "nah im just code but i try to sound natural"],
         repeat=["still just code, nothing changed since you last asked"]),

    dict(category="bored",
         keywords=["i am bored", "im bored", "so bored"],
         replies=["wanna talk about something random then",
                  "same energy lets find something interesting to talk about"],
         repeat=["still bored huh, ok lets actually pick a topic this time"]),

    dict(category="sad",
         keywords=["i am sad", "im sad", "feeling down", "not doing great", "im not okay"],
         replies=["im sorry to hear that im here if you want to talk about it",
                  "that sounds rough im listening if you want to talk"],
         repeat=["still here if you want to keep talking about it"]),

    dict(category="happy",
         keywords=["i am happy", "im happy", "feeling good", "great day", "amazing day"],
         replies=["thats awesome glad youre having a good one",
                  "love that energy whats got you feeling good"],
         repeat=["still riding that good mood, i see it"]),

    dict(category="time",
         keywords=["what time is it", "what day is it"],
         replies=["i dont actually have a clock built in sorry",
                  "no calendar access here but i wish i knew too"],
         repeat=["still no clock, still dont know"]),

    dict(category="sleep",
         keywords=["do you sleep", "do you get tired"],
         replies=["nah i just sit here waiting for you to type something",
                  "no sleep needed just ready whenever you are"],
         repeat=["nope, still dont sleep"]),

    dict(category="ai_talk",
         keywords=["what do you think about ai", "artificial intelligence"],
         replies=["its a pretty wild field honestly still moving fast",
                  "i think its interesting since im kind of a tiny example of it"],
         repeat=["still think ai is wild, that opinion hasn't changed"]),

    dict(category="roblox",
         keywords=["roblox"],
         replies=["roblox is pretty popular yeah you play a lot",
                  "oh nice whats your favorite roblox game"],
         repeat=["roblox again huh, what game specifically"]),

    dict(category="minecraft",
         keywords=["minecraft"],
         replies=["minecraft is a classic honestly still holds up",
                  "building stuff in minecraft is always fun"],
         repeat=["minecraft again, you really like that game"]),

    dict(category="affirm",
         keywords=["yes", "yeah", "yep", "yup"],
         replies=["nice okay", "gotcha", "bet"],
         repeat=["cool cool"]),

    dict(category="deny",
         keywords=["no", "nah", "nope"],
         replies=["fair enough", "okay noted", "alright thats valid"],
         repeat=["ok understood"]),

    dict(category="help",
         keywords=["help", "can you help me", "i need help"],
         replies=["yeah for sure whats going on", "im listening whats up"],
         repeat=["still listening, what do you need"]),

    dict(category="favorite",
         keywords=["what is your favorite", "do you have a favorite"],
         replies=["i dont really have preferences yet but im curious what yours is",
                  "havent picked a favorite yet honestly whats yours"],
         repeat=["still no favorite picked, still curious about yours though"]),
]

# ---------------------------------------------------------------
# LIVE WEB LOOKUP -- this is the "actually go find out" upgrade.
# Detects when the user is asking about a real topic (or just
# mentions one, like "roblox") and fetches a short factual summary
# from Wikipedia's public REST API instead of guessing.
# ---------------------------------------------------------------
LOOKUP_PATTERNS = [
    r"what(?:'s| is) (?:a |an |the )?(.+?)\??$",
    r"whats (?:a |an |the )?(.+?)\??$",
    r"who (?:is|was) (.+?)\??$",
    r"tell me about (.+?)\??$",
    r"define (.+?)\??$",
    r"do you know (?:what|who) (.+?) is\??$",
]

# Topics the bot proactively looks up even without a "what is" style
# question -- e.g. just saying "roblox" in a sentence.
AUTO_TOPIC_WORDS = {
    "roblox": "Roblox", "minecraft": "Minecraft", "fortnite": "Fortnite",
}

LOOKUP_SKIP_TOPICS = {
    "you", "your name", "your favorite", "me", "that", "this", "it", "up",
}


def detect_lookup_topic(text):
    norm = text.strip().lower().rstrip("?.! ")
    for pat in LOOKUP_PATTERNS:
        m = re.match(pat, norm)
        if m:
            topic = m.group(1).strip()
            if topic and topic not in LOOKUP_SKIP_TOPICS and not topic.startswith("your"):
                return topic
    for word, proper in AUTO_TOPIC_WORDS.items():
        if re.search(rf"\b{word}\b", norm):
            return proper
    return None


def wiki_lookup(term, timeout=5):
    """Fetch a short factual summary from Wikipedia. Returns None on any
    failure (no internet, no page, disambiguation, etc) so callers can
    fall back gracefully."""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(term)
        req = urllib.request.Request(
            url, headers={"User-Agent": "LearningBotGUI/1.0 (personal tkinter chatbot project)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("type") == "disambiguation":
            return None
        extract = (data.get("extract") or "").strip()
        if not extract:
            return None
        sentences = re.split(r"(?<=[.!?]) +", extract)
        short = " ".join(sentences[:2])
        if len(short) > 320:
            short = short[:317].rsplit(" ", 1)[0] + "..."
        return short
    except Exception:
        return None


# ---------------------------------------------------------------
# REFLECTION FALLBACK (lightweight ELIZA-style)
# Used when the response bank has no good match AND the word-chain
# generator's output is too short/weak to feel like a real answer.
# ---------------------------------------------------------------
PRONOUN_SWAP = {
    "i": "you", "me": "you", "my": "your", "mine": "yours", "myself": "yourself",
    "am": "are", "you": "I", "your": "my", "yours": "mine", "yourself": "myself",
    "are": "am",
}

REFLECTION_TEMPLATES = [
    "why do you say {t}",
    "what makes you think {t}",
    "how does it feel that {t}",
    "why is that important to you",
    "tell me more about that",
    "go on, what else about {t}",
    "does that happen a lot",
    "what do you mean by {t}",
]

STOPWORDS = {"the", "a", "an", "is", "it", "to", "and", "of", "in", "that", "this"}


def swap_pronouns(words):
    return [PRONOUN_SWAP.get(w, w) for w in words]


def build_reflection(user_text):
    words = tokenize(user_text)
    if not words:
        return random.choice(["tell me more", "go on", "whats on your mind"])
    swapped = swap_pronouns(words)
    trimmed = [w for w in swapped if w not in STOPWORDS]
    tail = " ".join(trimmed[-6:]) if trimmed else " ".join(swapped[-6:])
    template = random.choice(REFLECTION_TEMPLATES)
    if "{t}" in template:
        return template.format(t=tail)
    return template


# ---------------------------------------------------------------
# PERSONA MODES (replaces the old plain slang slider)
# ---------------------------------------------------------------
PERSONAS = {
    "CHILL": dict(
        fillers=["honestly ", "for real ", "no rush but "],
        intensity=20,
        asides=[],
    ),
    "CHAOTIC": dict(
        fillers=["lol ", "ngl ", "fr fr ", "bro ", "ok but ", "wait- "],
        intensity=65,
        asides=["anyway", "unrelated but", "side note"],
    ),
    "SARCASTIC": dict(
        fillers=["oh totally ", "sure ", "wow groundbreaking ", "riveting, "],
        intensity=45,
        asides=["just saying", "not that it matters"],
    ),
    "WHOLESOME": dict(
        fillers=["aw ", "thats sweet, ", "genuinely though, "],
        intensity=15,
        asides=[],
    ),
    "FURRY/UWU": dict(
        fillers=["nya~ ", "uwu ", "hehe~ ", "mmm~ "],
        intensity=60,
        asides=["*wags*", "*paws at the keyboard*", "*happy noises*"],
    ),
}

# "noms your text box" style reactions -- prepended occasionally when
# the FURRY/UWU persona is active. Silly pet-speak / hangry-gremlin
# flavor only, nothing sexual -- just a chatbot bit.
UWU_NOM_REACTIONS = [
    "*noms your message whole* mmm dat text packet was so yummy and warm~",
    "*chomps your words* tasty~ ok here's my reply:",
    "*chews on your message thoughtfully* nom nom, ok so~",
    "ohai~! *noms your text box* ok lemme answer that:",
]


def uwuify(text):
    text = re.sub(r"[rl]", "w", text)
    text = re.sub(r"[RL]", "W", text)
    text = text.replace("th", "d").replace("Th", "D")
    if random.random() < 0.4:
        text += " " + random.choice(["~", "owo", "uwu", ">w<"])
    return text


def apply_persona(text, persona_name):
    persona = PERSONAS.get(persona_name, PERSONAS["CHILL"])

    if persona_name == "FURRY/UWU":
        out = text
        if random.randint(1, 100) <= persona["intensity"]:
            filler = random.choice(persona["fillers"])
            out = (filler + out) if random.random() < 0.6 else (out + " " + filler.strip())
        if persona["asides"] and random.random() < 0.3:
            out += " " + random.choice(persona["asides"])
        out = uwuify(out)
        if random.random() < 0.35:
            out = random.choice(UWU_NOM_REACTIONS) + " " + out
        return out

    if random.randint(1, 100) > persona["intensity"]:
        return text
    filler = random.choice(persona["fillers"])
    out = (filler + text) if random.random() < 0.6 else (text + " " + filler.strip())
    if persona["asides"] and random.random() < 0.25:
        out += ", " + random.choice(persona["asides"])
    return out


MONO = None  # set once a tk root exists


def tokenize(text):
    return re.findall(r"[a-z']+", text.lower())


def normalize(text):
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def ckey(words):
    return "|".join(words)


def score_bank_entry(norm_text, entry):
    score = 0
    for trig in entry["keywords"]:
        pattern = r"\b" + re.escape(trig.strip()) + r"\b"
        if re.search(pattern, norm_text):
            score += len(trig.split())  # longer/more specific phrases score higher
    return score


def match_bank(user_text, already_fired):
    """Return (reply, category) or (None, None). already_fired is a set of
    category names that have already produced a reply this session, used
    to switch to the 'repeat' reply set and stop the endless-greeting loop."""
    norm = normalize(user_text)
    scored = []
    for entry in RESPONSE_BANK:
        s = score_bank_entry(norm, entry)
        if s > 0:
            scored.append((s, entry))
    if not scored:
        return None, None
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    top_entries = [e for s, e in scored if s == top_score]
    entry = random.choice(top_entries)
    if entry["category"] in already_fired and entry.get("repeat"):
        reply = random.choice(entry["repeat"])
    else:
        reply = random.choice(entry["replies"])
    return reply, entry["category"]


# ---------------------------------------------------------------
# SAFE CALCULATOR EXPRESSION EVALUATOR (no eval() on raw input)
# ---------------------------------------------------------------
_CALC_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def safe_calc(expr):
    node = ast.parse(expr, mode="eval").body

    def _eval(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _CALC_OPS:
            return _CALC_OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _CALC_OPS:
            return _CALC_OPS[type(n.op)](_eval(n.operand))
        raise ValueError("unsupported expression")

    return _eval(node)


# ---------------------------------------------------------------
# THE LEARNING BOT (word-chain fallback engine)
# ---------------------------------------------------------------
class LearningBot:
    def __init__(self, path=BRAIN_FILE):
        self.path = path
        self.load()
        self.last_learn_events = []
        self.recent_replies = []
        self.fired_categories = set()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
            self.chain1 = data.get("chain1", {})
            self.chain2 = data.get("chain2", {})
            self.chain3 = data.get("chain3", {})
            self.chain4 = data.get("chain4", {})
            self.starters = data.get("starters", {})
            self.history = data.get("history", [])
            self.used_extra_phrases = data.get("used_extra_phrases", [])
            self.good_count = data.get("good_count", 0)
            self.bad_count = data.get("bad_count", 0)
        else:
            self.chain1 = {w: dict(nexts) for w, nexts in SEED_CHAIN1.items()}
            self.chain2 = {}
            self.chain3 = {}
            self.chain4 = {}
            self.starters = {w: 1 for w in SEED_STARTERS}
            self.history = []
            self.used_extra_phrases = []
            self.good_count = 0
            self.bad_count = 0
            for sentence in BOOTSTRAP_SENTENCES:
                self.learn(sentence)
            self.save()

    def save(self):
        with open(self.path, "w") as f:
            json.dump({
                "chain1": self.chain1, "chain2": self.chain2,
                "chain3": self.chain3, "chain4": self.chain4,
                "starters": self.starters,
                "history": self.history[-MAX_HISTORY:],
                "used_extra_phrases": self.used_extra_phrases,
                "good_count": self.good_count, "bad_count": self.bad_count,
            }, f, indent=2)

    def remember(self, role, text):
        self.history.append({"role": role, "text": text})
        self.history = self.history[-MAX_HISTORY:]

    def learn(self, text):
        words = tokenize(text)
        if not words:
            return
        self.starters[words[0]] = self.starters.get(words[0], 0) + 1
        for a, b in zip(words, words[1:]):
            self.chain1.setdefault(a, {})
            self.chain1[a][b] = self.chain1[a].get(b, 0) + 1
        for a, b, c in zip(words, words[1:], words[2:]):
            key = ckey([a, b])
            self.chain2.setdefault(key, {})
            self.chain2[key][c] = self.chain2[key].get(c, 0) + 1
        for a, b, c, d in zip(words, words[1:], words[2:], words[3:]):
            key = ckey([a, b, c])
            self.chain3.setdefault(key, {})
            self.chain3[key][d] = self.chain3[key].get(d, 0) + 1
        for a, b, c, d, e in zip(words, words[1:], words[2:], words[3:], words[4:]):
            key = ckey([a, b, c, d])
            self.chain4.setdefault(key, {})
            self.chain4[key][e] = self.chain4[key].get(e, 0) + 1

    def learn_extra_phrase(self):
        remaining = [s for s in EXTRA_PHRASES if s not in self.used_extra_phrases]
        if not remaining:
            return None
        sentence = random.choice(remaining)
        self.learn(sentence)
        self.used_extra_phrases.append(sentence)
        return sentence

    def reinforce(self, good):
        if good:
            self.good_count += 1
        else:
            self.bad_count += 1
        delta = REINFORCE_STRENGTH if good else -REINFORCE_STRENGTH
        tables = {1: self.chain1, 2: self.chain2, 3: self.chain3, 4: self.chain4}
        for kind, key, nxt in self.last_learn_events:
            table = tables[kind]
            if key in table and nxt in table[key]:
                table[key][nxt] = max(1, table[key][nxt] + delta)
        self.last_learn_events = []
        self.save()

    def _weighted_choice(self, options):
        words = list(options.keys())
        weights = list(options.values())
        return random.choices(words, weights=weights, k=1)[0]

    def _generate_once(self, max_len):
        if not self.starters:
            return None, []
        # Greetings are already fully owned by the response bank -- never let
        # the word-chain fallback start a reply with one, or it dominates
        # every fallback reply since "hello there how are you doing today"
        # is one of the longest learnable sentences in the bootstrap corpus.
        usable_starters = {w: c for w, c in self.starters.items()
                            if w not in GREETING_STARTER_BLOCK}
        starter_pool = usable_starters if usable_starters else self.starters
        word1 = self._weighted_choice(starter_pool)
        sentence = [word1]
        events = []
        options1 = self.chain1.get(word1)
        if not options1:
            return " ".join(sentence), events
        word2 = self._weighted_choice(options1)
        events.append((1, word1, word2))
        sentence.append(word2)

        recent = [word1, word2]
        for _ in range(max_len - 2):
            nxt = None
            if len(recent) >= 4:
                key4 = ckey(recent[-4:])
                opts4 = self.chain4.get(key4)
                if opts4:
                    nxt = self._weighted_choice(opts4)
                    events.append((4, key4, nxt))
            if nxt is None and len(recent) >= 3:
                key3 = ckey(recent[-3:])
                opts3 = self.chain3.get(key3)
                if opts3:
                    nxt = self._weighted_choice(opts3)
                    events.append((3, key3, nxt))
            if nxt is None:
                key2 = ckey(recent[-2:])
                opts2 = self.chain2.get(key2)
                if opts2:
                    nxt = self._weighted_choice(opts2)
                    events.append((2, key2, nxt))
            if nxt is None:
                opts1 = self.chain1.get(recent[-1])
                if opts1:
                    nxt = self._weighted_choice(opts1)
                    events.append((1, recent[-1], nxt))
            if nxt is None:
                break
            sentence.append(nxt)
            recent.append(nxt)
        return " ".join(sentence), events

    def chain_reply(self, max_len=MAX_REPLY_LEN):
        """Word-chain generation only (no bank, no reflection). Returns
        (sentence, is_weak) where is_weak flags outputs too short/repeated
        to be worth using over a reflection fallback."""
        candidates = []
        for _ in range(GENERATION_ATTEMPTS):
            sentence, events = self._generate_once(max_len)
            if sentence is None:
                return None, True
            candidates.append((sentence, events))
        fresh = [c for c in candidates if c[0] not in self.recent_replies]
        pool = fresh if fresh else candidates
        long_enough = [c for c in pool if len(c[0].split()) >= MIN_REPLY_LEN]
        pool = long_enough if long_enough else pool
        # Pick randomly among the longest few instead of always the single
        # longest candidate -- otherwise one dominant learned sentence wins
        # every single time and the bot feels stuck on repeat.
        pool_sorted = sorted(pool, key=lambda c: len(c[0].split()), reverse=True)
        top_pool = pool_sorted[:3] if len(pool_sorted) >= 3 else pool_sorted
        best_sentence, best_events = random.choice(top_pool)
        self.last_learn_events = best_events
        is_weak = len(best_sentence.split()) < MIN_REPLY_LEN
        return best_sentence, is_weak

    def reply(self, user_text):
        """Full reply pipeline: response bank -> word chain -> reflection."""
        bank_reply, category = match_bank(user_text, self.fired_categories)
        if bank_reply is not None:
            self.fired_categories.add(category)
            self.last_learn_events = []
            self.recent_replies.append(bank_reply)
            self.recent_replies = self.recent_replies[-NO_REPEAT_LAST_N:]
            return bank_reply

        sentence, is_weak = self.chain_reply()
        if sentence is None:
            return "...(nothing learned yet -- teach me something!)"
        if is_weak:
            sentence = build_reflection(user_text)
            self.last_learn_events = []

        self.recent_replies.append(sentence)
        self.recent_replies = self.recent_replies[-NO_REPEAT_LAST_N:]
        return sentence

    def vocab_size(self):
        words = set(self.chain1.keys())
        for d in self.chain1.values():
            words.update(d.keys())
        return len(words)


# ---------------------------------------------------------------
# GUI
# ---------------------------------------------------------------
class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.bot = LearningBot()
        self.awaiting_feedback = False
        self._fullscreen = False
        self._pulse_i = 0
        self._pending_reply = None
        self._search_queue = queue.Queue()

        root.title("NEURAL // LEARNING TERMINAL")
        root.configure(bg=BG)
        self._maximize(root)
        root.bind("<F11>", self._toggle_fullscreen)
        root.bind("<Escape>", self._exit_fullscreen)

        self.mono = font.Font(family=MONO_FAMILY, size=12)
        self.mono_bold = font.Font(family=MONO_FAMILY, size=12, weight="bold")
        self.ui_font = font.Font(family=UI_FAMILY, size=10)
        self.ui_bold = font.Font(family=UI_FAMILY, size=10, weight="bold")
        self.header_font = font.Font(family=UI_FAMILY, size=17, weight="bold")
        self.small_font = font.Font(family=UI_FAMILY, size=9)
        self.big_font = font.Font(family=MONO_FAMILY, size=20, weight="bold")

        # Everything lives on top of this canvas so the animated glow grid
        # and drifting particles show through every gap and margin, not
        # just a strip at the top/bottom.
        self.bg_canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)

        self._build_header(self.bg_canvas)
        self.accent_line = tk.Frame(self.bg_canvas, bg=ACCENT, height=2)
        self.accent_line.pack(fill=tk.X, side=tk.TOP)
        self._pulse()

        self._build_ticker(self.bg_canvas)

        body = tk.Frame(self.bg_canvas, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 14))

        left = tk.Frame(body, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        self._build_chat_area(left)

        right = tk.Frame(body, bg=BG, width=340)
        right.pack(side=tk.LEFT, fill=tk.Y)
        right.pack_propagate(False)
        self._build_side_panel(right)

        self._boot_sequence()
        self.root.after(400, self._init_background_fx)

    # ---------------- header ----------------

    def _build_header(self, root):
        header = tk.Frame(root, bg=PANEL_BG, height=60,
                           highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        avatar = tk.Canvas(header, width=34, height=34, bg=PANEL_BG,
                            highlightthickness=0)
        avatar.pack(side=tk.LEFT, padx=(18, 10))
        avatar.create_oval(2, 2, 32, 32, outline=ACCENT, width=2)
        avatar.create_oval(11, 11, 23, 23, fill=ACCENT, outline="")

        title_box = tk.Frame(header, bg=PANEL_BG)
        title_box.pack(side=tk.LEFT, pady=8)
        tk.Label(title_box, text="NEURAL LEARNING TERMINAL",
                 bg=PANEL_BG, fg=ACCENT, font=self.header_font).pack(anchor="w")
        tk.Label(title_box, text="one character \u00b7 gets sharper the more you talk",
                 bg=PANEL_BG, fg=TEXT_DIM, font=self.small_font).pack(anchor="w")

        self.status_dot = tk.Label(header, text="\u25CF", bg=PANEL_BG,
                                    fg=GOOD_COLOR, font=("Consolas", 14))
        self.status_dot.pack(side=tk.RIGHT, padx=(0, 6))
        self.status_lbl = tk.Label(header, text="ONLINE", bg=PANEL_BG,
                                    fg=TEXT_DIM, font=self.ui_bold)
        self.status_lbl.pack(side=tk.RIGHT, padx=(0, 4))
        self._blink_on = True
        self._blink_status_dot()

        self.eq_canvas = tk.Canvas(header, width=54, height=28, bg=PANEL_BG,
                                    highlightthickness=0)
        self.eq_canvas.pack(side=tk.RIGHT, padx=(0, 16))
        self._eq_bars = []
        bar_w, gap = 6, 4
        for i in range(6):
            x0 = i * (bar_w + gap)
            bar = self.eq_canvas.create_rectangle(x0, 28, x0 + bar_w, 28,
                                                   fill=ACCENT, outline="")
            self._eq_bars.append((bar, x0))
        self._animate_eq()

    def _animate_eq(self):
        colors = [ACCENT, VIOLET, MAGENTA]
        for bar, x0 in self._eq_bars:
            h = random.randint(4, 26)
            self.eq_canvas.coords(bar, x0, 28 - h, x0 + 6, 28)
            self.eq_canvas.itemconfig(bar, fill=random.choice(colors))
        self.root.after(180, self._animate_eq)

    def _build_ticker(self, root):
        self.ticker_canvas = tk.Canvas(root, height=26, bg=PANEL_BG,
                                        highlightbackground=BORDER,
                                        highlightthickness=1)
        self.ticker_canvas.pack(fill=tk.X, side=tk.BOTTOM)
        self._ticker_id = self.ticker_canvas.create_text(
            4, 13, text="", fill=ACCENT_DIM, font=self.small_font, anchor="w"
        )
        self.root.after(300, self._start_ticker)

    def _ticker_string(self):
        g, b = self.bot.good_count, self.bot.bad_count
        persona = getattr(self, "persona_name", None)
        persona_txt = persona.get() if persona else "CHILL"
        return (
            f"VOCAB:{self.bot.vocab_size()}   MSGS:{len(self.bot.history)}   "
            f"MOOD:{g}\u2191/{b}\u2193   PERSONA:{persona_txt}   "
            f"SYNC:{random.randint(92, 99)}%   PING:{random.randint(8, 24)}ms   "
            f"NODES:{random.randint(3, 7)} ONLINE      \u25C8      "
        )

    def _start_ticker(self):
        self.ticker_canvas.itemconfig(self._ticker_id, text=self._ticker_string())
        self._animate_ticker()

    def _animate_ticker(self):
        self.ticker_canvas.move(self._ticker_id, -2, 0)
        bbox = self.ticker_canvas.bbox(self._ticker_id)
        if bbox and bbox[2] < 0:
            width = self.ticker_canvas.winfo_width() or 900
            self.ticker_canvas.coords(self._ticker_id, width, 13)
            self.ticker_canvas.itemconfig(self._ticker_id, text=self._ticker_string())
        self.root.after(35, self._animate_ticker)

    def _pulse(self):
        self._pulse_i = (self._pulse_i + 1) % len(PULSE_COLORS)
        self.accent_line.config(bg=PULSE_COLORS[self._pulse_i])
        self.root.after(400, self._pulse)

    def _init_background_fx(self):
        """Draws a faint circuit-style grid once, then starts an animated
        field of drifting glowing particles + occasional light streaks on
        the bg_canvas. Everything renders behind the header/body/ticker
        frames and shows through in every gap and margin."""
        w = self.bg_canvas.winfo_width() or self.root.winfo_screenwidth()
        h = self.bg_canvas.winfo_height() or self.root.winfo_screenheight()

        step = 64
        for gx in range(0, int(w), step):
            self.bg_canvas.create_line(gx, 0, gx, h, fill="#081826", width=1)
        for gy in range(0, int(h), step):
            self.bg_canvas.create_line(0, gy, w, gy, fill="#081826", width=1)

        self._particles = []
        particle_colors = [ACCENT, "#8fe6ff", ACCENT_DIM, VIOLET]
        for _ in range(55):
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            r = random.uniform(1.0, 2.6)
            dx = random.uniform(-0.35, 0.35)
            dy = random.uniform(-0.35, 0.35)
            color = random.choice(particle_colors)
            glow_id = self.bg_canvas.create_oval(x - r * 2.4, y - r * 2.4,
                                                   x + r * 2.4, y + r * 2.4,
                                                   fill="", outline=color)
            core_id = self.bg_canvas.create_oval(x - r, y - r, x + r, y + r,
                                                   fill=color, outline="")
            self._particles.append({"glow": glow_id, "core": core_id,
                                     "x": x, "y": y, "dx": dx, "dy": dy, "r": r})

        self._streaks = []
        self._animate_background()
        self.root.after(2600, self._spawn_streak)

    def _animate_background(self):
        w = self.bg_canvas.winfo_width() or 1200
        h = self.bg_canvas.winfo_height() or 800
        for p in self._particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]
            if p["x"] < 0 or p["x"] > w:
                p["dx"] *= -1
                p["x"] = max(0, min(w, p["x"]))
            if p["y"] < 0 or p["y"] > h:
                p["dy"] *= -1
                p["y"] = max(0, min(h, p["y"]))
            r = p["r"]
            self.bg_canvas.coords(p["core"], p["x"] - r, p["y"] - r,
                                   p["x"] + r, p["y"] + r)
            self.bg_canvas.coords(p["glow"], p["x"] - r * 2.4, p["y"] - r * 2.4,
                                   p["x"] + r * 2.4, p["y"] + r * 2.4)

        still_alive = []
        for s in self._streaks:
            self.bg_canvas.move(s["id"], s["dx"], s["dy"])
            s["ttl"] -= 1
            if s["ttl"] <= 0:
                self.bg_canvas.delete(s["id"])
            else:
                still_alive.append(s)
        self._streaks = still_alive

        self.root.after(45, self._animate_background)

    def _spawn_streak(self):
        w = self.bg_canvas.winfo_width() or 1200
        h = self.bg_canvas.winfo_height() or 800
        horizontal = random.random() < 0.5
        if horizontal:
            y = random.uniform(0, h)
            length = random.uniform(60, 130)
            sid = self.bg_canvas.create_line(-length, y, 0, y,
                                              fill=ACCENT, width=1)
            self._streaks.append({"id": sid, "dx": random.uniform(6, 10),
                                   "dy": 0, "ttl": int(w / 8)})
        else:
            x = random.uniform(0, w)
            length = random.uniform(60, 130)
            sid = self.bg_canvas.create_line(x, -length, x, 0,
                                              fill=VIOLET, width=1)
            self._streaks.append({"id": sid, "dx": 0,
                                   "dy": random.uniform(6, 10), "ttl": int(h / 8)})
        self.root.after(random.randint(2200, 4200), self._spawn_streak)

    def _blink_status_dot(self):
        self._blink_on = not self._blink_on
        self.status_dot.config(fg=GOOD_COLOR if self._blink_on else ACCENT_DIM)
        self.root.after(700, self._blink_status_dot)

    def _set_status(self, text, color=ACCENT):
        self.status_lbl.config(text=text, fg=color)
        self.root.update_idletasks()

    # ---------------- chat area ----------------

    def _glow_wrap(self, parent, **pack_kwargs):
        """Returns an inner frame that visually reads as a glowing outline:
        a thin bright accent ring around a darker bordered box."""
        glow = tk.Frame(parent, bg=ACCENT)
        glow.pack(**pack_kwargs)
        inner = tk.Frame(glow, bg=BORDER, highlightbackground=ACCENT_DIM,
                          highlightthickness=1)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        return inner

    def _build_chat_area(self, parent):
        tk.Label(parent, text="CHAT LOG", bg=BG, fg=TEXT_DIM,
                 font=self.small_font, anchor="w").pack(fill=tk.X)

        log_border = self._glow_wrap(parent, fill=tk.BOTH, expand=True, pady=(4, 10))

        self.chat_log = scrolledtext.ScrolledText(
            log_border, wrap=tk.WORD, state="disabled", font=self.mono,
            bg=PANEL_BG, fg=TEXT_MAIN, insertbackground=ACCENT, borderwidth=0,
            padx=14, pady=12, spacing3=10
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.chat_log.tag_config("user_label", foreground=ACCENT, font=self.mono_bold)
        self.chat_log.tag_config("user_bubble", background=BUBBLE_USER,
                                  foreground=TEXT_MAIN, lmargin1=10, lmargin2=10,
                                  rmargin=60, spacing1=4, spacing3=4)
        self.chat_log.tag_config("bot_label", foreground=MAGENTA, font=self.mono_bold)
        self.chat_log.tag_config("bot_bubble", background=BUBBLE_BOT,
                                  foreground=TEXT_MAIN, lmargin1=10, lmargin2=10,
                                  rmargin=60, spacing1=4, spacing3=4)
        self.chat_log.tag_config("system", foreground=TEXT_DIM, font=self.small_font)
        self.chat_log.tag_config("typing", foreground=TEXT_DIM, font=self.small_font)

        feedback_frame = tk.Frame(parent, bg=BG)
        feedback_frame.pack(fill=tk.X, pady=(0, 4))

        self.good_btn = self._make_button(
            feedback_frame, "\u25B2 GOOD", self.mark_good, GOOD_COLOR, "#0f2a20")
        self.good_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.good_btn.config(state="disabled")

        self.bad_btn = self._make_button(
            feedback_frame, "\u25BC BAD", self.mark_bad, BAD_COLOR, "#2a0f16")
        self.bad_btn.pack(side=tk.LEFT)
        self.bad_btn.config(state="disabled")

        self.feedback_label = tk.Label(feedback_frame, text="", bg=BG,
                                        fg=TEXT_DIM, font=self.small_font)
        self.feedback_label.pack(side=tk.LEFT, padx=14)

        search_frame = tk.Frame(parent, bg=BG)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        self.search_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(
            search_frame, text="\u25C9 LEARN EXTRA PHRASES (before reply)",
            variable=self.search_mode, bg=BG, fg=TEXT_DIM, selectcolor=PANEL_BG,
            activebackground=BG, activeforeground=ACCENT, font=self.small_font,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        input_frame = tk.Frame(parent, bg=BG)
        input_frame.pack(fill=tk.X)

        entry_border = tk.Frame(input_frame, bg=ACCENT_DIM)
        entry_border.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry = tk.Entry(entry_border, font=self.mono, bg=PANEL_BG,
                               fg=TEXT_MAIN, insertbackground=ACCENT, borderwidth=0)
        self.entry.pack(fill=tk.BOTH, expand=True, ipady=8, padx=1, pady=1)
        self.entry.bind("<Return>", lambda e: self.send())
        self.entry.focus()

        send_btn = self._make_button(input_frame, "SEND \u25B6", self.send,
                                      "#00131a", "#5df3ff", fill=ACCENT)
        send_btn.pack(side=tk.LEFT)

    def _make_button(self, parent, text, command, fg, hover_bg, fill=None):
        base_bg = fill if fill else PANEL_BG
        btn = tk.Button(
            parent, text=text, command=command, bg=base_bg, fg=fg,
            activebackground=hover_bg, activeforeground=fg,
            highlightbackground=fg if not fill else base_bg,
            highlightthickness=0 if fill else 1, borderwidth=0,
            font=self.ui_bold, padx=16, pady=7, cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=base_bg))
        return btn

    def _boot_sequence(self):
        lines = [
            "// booting neural link...",
            f"// vocabulary loaded ({self.bot.vocab_size()} linked words)",
            f"// {len(self.bot.history)} past messages in memory",
            "// response bank + reflection engine online",
            "// live web lookup online (ask 'what is x' or mention a topic)",
            "// ready. type below and press ENTER or SEND.",
        ]
        for i, line in enumerate(lines):
            self.root.after(180 * i, lambda l=line: self._log("system", l))

    def _log(self, tag, message):
        self.chat_log.configure(state="normal")
        if tag == "user":
            self.chat_log.insert(tk.END, "YOU\n", "user_label")
            self.chat_log.insert(tk.END, message + "\n\n", "user_bubble")
        elif tag == "bot":
            self.chat_log.insert(tk.END, "BOT\n", "bot_label")
            self.chat_log.insert(tk.END, message + "\n\n", "bot_bubble")
        elif tag == "typing":
            self.chat_log.insert(tk.END, message + "\n", "typing")
        else:
            self.chat_log.insert(tk.END, message + "\n", "system")
        self.chat_log.configure(state="disabled")
        self.chat_log.see(tk.END)

    def _remove_last_line(self):
        self.chat_log.configure(state="normal")
        self.chat_log.delete("end-2l", "end-1l")
        self.chat_log.configure(state="disabled")

    # ---------------- side panel ----------------

    def _build_side_panel(self, parent):
        tk.Label(parent, text="CONTROL PANEL", bg=BG, fg=TEXT_DIM,
                 font=self.small_font, anchor="w").pack(fill=tk.X)

        tab_row = tk.Frame(parent, bg=BG)
        tab_row.pack(fill=tk.X, pady=(4, 8))

        self.tab_buttons = {}
        self.tabs = {}
        container = tk.Frame(parent, bg=PANEL_BG, highlightbackground=ACCENT_DIM,
                              highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True)

        for name in ("PERSONALITY", "CALC", "NOTES"):
            btn = tk.Button(
                tab_row, text=name, command=lambda n=name: self._show_tab(n),
                bg=PANEL_BG, fg=TEXT_DIM, activebackground=PANEL_BG_2,
                activeforeground=ACCENT, borderwidth=0, font=self.small_font,
                padx=8, pady=7, cursor="hand2"
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
            self.tab_buttons[name] = btn

            tab_frame = tk.Frame(container, bg=PANEL_BG)
            self.tabs[name] = tab_frame

        self._build_personality_tab(self.tabs["PERSONALITY"])
        self._build_calc_tab(self.tabs["CALC"])
        self._build_notes_tab(self.tabs["NOTES"])

        self._show_tab("PERSONALITY")

    def _show_tab(self, name):
        for n, frame in self.tabs.items():
            frame.pack_forget()
            self.tab_buttons[n].config(bg=PANEL_BG, fg=TEXT_DIM)
        self.tabs[name].pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.tab_buttons[name].config(bg=PANEL_BG_2, fg=ACCENT)
        if name == "PERSONALITY":
            self._refresh_stats()

    # --- personality tab ---

    def _build_personality_tab(self, frame):
        tk.Label(frame, text="PERSONA MODE", bg=PANEL_BG, fg=ACCENT,
                 font=self.ui_bold).pack(anchor="w", pady=(4, 6))

        self.persona_name = tk.StringVar(value="CHILL")
        persona_row = tk.Frame(frame, bg=PANEL_BG)
        persona_row.pack(fill=tk.X, pady=(0, 4))
        self.persona_buttons = {}
        descs = {
            "CHILL": "low-key, mostly normal",
            "CHAOTIC": "lol/ngl everywhere, random asides",
            "SARCASTIC": "dry, deadpan replies",
            "WHOLESOME": "extra warm and encouraging",
            "FURRY/UWU": "labeled furry/uwu mode: soft pet-speak, noms your text box, still SFW",
        }
        for i, name in enumerate(PERSONAS):
            b = tk.Button(
                persona_row, text=name, command=lambda n=name: self._set_persona(n),
                bg=PANEL_BG_2, fg=TEXT_DIM, activebackground=BORDER,
                borderwidth=0, font=self.small_font, padx=6, pady=6, cursor="hand2"
            )
            b.grid(row=i // 2, column=i % 2, sticky="nsew", padx=2, pady=2)
            self.persona_buttons[name] = b
        persona_row.columnconfigure(0, weight=1)
        persona_row.columnconfigure(1, weight=1)

        self.persona_desc = tk.Label(frame, text=descs["CHILL"], bg=PANEL_BG,
                                      fg=TEXT_DIM, font=self.small_font,
                                      wraplength=280, justify="left")
        self.persona_desc.pack(anchor="w", pady=(4, 14))
        self._persona_descs = descs
        self._set_persona("CHILL")

        tk.Label(frame, text="LIVE STATS", bg=PANEL_BG, fg=ACCENT,
                 font=self.ui_bold).pack(anchor="w", pady=(8, 4))

        self.stat_vocab = tk.Label(frame, text="", bg=PANEL_BG, fg=TEXT_MAIN,
                                    font=self.small_font, anchor="w", justify="left")
        self.stat_vocab.pack(fill=tk.X)
        self.stat_memory = tk.Label(frame, text="", bg=PANEL_BG, fg=TEXT_MAIN,
                                     font=self.small_font, anchor="w", justify="left")
        self.stat_memory.pack(fill=tk.X)
        self.stat_mood = tk.Label(frame, text="", bg=PANEL_BG, fg=TEXT_MAIN,
                                   font=self.small_font, anchor="w", justify="left")
        self.stat_mood.pack(fill=tk.X, pady=(0, 16))

        wipe_btn = self._make_button(frame, "\u26A0 WIPE MEMORY", self._wipe_memory,
                                      BAD_COLOR, "#2a0f16")
        wipe_btn.pack(anchor="w")

    def _set_persona(self, name):
        self.persona_name.set(name)
        for n, b in self.persona_buttons.items():
            if n == name:
                b.config(bg=PANEL_BG_2, fg=ACCENT, highlightbackground=ACCENT,
                         highlightthickness=1)
            else:
                b.config(bg=PANEL_BG_2, fg=TEXT_DIM, highlightthickness=0)
        self.persona_desc.config(text=self._persona_descs[name])

    def _refresh_stats(self):
        self.stat_vocab.config(text=f"WORDS LINKED : {self.bot.vocab_size()}")
        self.stat_memory.config(text=f"MESSAGES KEPT: {len(self.bot.history)}")
        g, b = self.bot.good_count, self.bot.bad_count
        total = g + b
        mood = "NEUTRAL" if total == 0 else f"{round(100 * g / total)}% POSITIVE"
        self.stat_mood.config(text=f"FEEDBACK MOOD: {mood} ({g}\u2191/{b}\u2193)")

    def _wipe_memory(self):
        if messagebox.askyesno("Wipe memory?",
                                "This deletes everything learned and restarts "
                                "from the built-in bootstrap vocabulary. Continue?"):
            if os.path.exists(self.bot.path):
                os.remove(self.bot.path)
            self.bot = LearningBot()
            self._log("system", "// memory wiped -- back to bootstrap vocabulary")
            self._refresh_stats()

    # --- calculator tab ---

    def _build_calc_tab(self, frame):
        self.calc_display = tk.StringVar(value="")
        entry = tk.Entry(frame, textvariable=self.calc_display, font=self.big_font,
                          bg=PANEL_BG_2, fg=ACCENT, insertbackground=ACCENT,
                          borderwidth=0, justify="right")
        entry.pack(fill=tk.X, pady=(4, 10), ipady=10)
        entry.bind("<Return>", lambda e: self._calc_equals())

        rows = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "C", "+"],
        ]
        grid = tk.Frame(frame, bg=PANEL_BG)
        grid.pack(fill=tk.X)
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                cmd = self._calc_clear if label == "C" else (lambda l=label: self._calc_press(l))
                fg = BAD_COLOR if label == "C" else (ACCENT if label in "+-*/" else TEXT_MAIN)
                b = tk.Button(
                    grid, text=label, command=cmd, bg=PANEL_BG_2, fg=fg,
                    activebackground=BORDER, borderwidth=0, font=self.mono_bold,
                    width=4, height=2, cursor="hand2"
                )
                b.bind("<Enter>", lambda e, b=b: b.config(bg=BORDER))
                b.bind("<Leave>", lambda e, b=b: b.config(bg=PANEL_BG_2))
                b.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
        for c in range(4):
            grid.columnconfigure(c, weight=1)

        eq_btn = self._make_button(frame, "= EQUALS", self._calc_equals,
                                    "#00131a", "#5df3ff", fill=ACCENT)
        eq_btn.pack(fill=tk.X, pady=(8, 0))

    def _calc_press(self, char):
        self.calc_display.set(self.calc_display.get() + char)

    def _calc_clear(self):
        self.calc_display.set("")

    def _calc_equals(self):
        expr = self.calc_display.get().strip()
        if not expr:
            return
        try:
            result = safe_calc(expr)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            self.calc_display.set(str(result))
        except Exception:
            self.calc_display.set("ERR")

    # --- notes tab ---

    def _build_notes_tab(self, frame):
        tk.Label(frame, text="NOTES", bg=PANEL_BG, fg=ACCENT,
                 font=self.ui_bold).pack(anchor="w", pady=(4, 4))
        self.notes_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=self.small_font, bg=PANEL_BG_2, fg=TEXT_MAIN,
            insertbackground=ACCENT, borderwidth=0, padx=8, pady=8, height=14
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r") as f:
                self.notes_text.insert("1.0", f.read())

        btn_row = tk.Frame(frame, bg=PANEL_BG)
        btn_row.pack(fill=tk.X)
        save_btn = self._make_button(btn_row, "SAVE", self._save_notes,
                                      GOOD_COLOR, "#0f2a20")
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        clear_btn = self._make_button(btn_row, "CLEAR", self._clear_notes,
                                       BAD_COLOR, "#2a0f16")
        clear_btn.pack(side=tk.LEFT)

    def _save_notes(self):
        with open(NOTES_FILE, "w") as f:
            f.write(self.notes_text.get("1.0", tk.END))

    def _clear_notes(self):
        if messagebox.askyesno("Clear notes?", "Erase everything in the notes tab?"):
            self.notes_text.delete("1.0", tk.END)
            self._save_notes()

    # ---------------- window helpers ----------------

    def _maximize(self, root):
        try:
            root.state("zoomed")
        except tk.TclError:
            try:
                root.attributes("-zoomed", True)
            except tk.TclError:
                w, h = root.winfo_screenwidth(), root.winfo_screenheight()
                root.geometry(f"{w}x{h}+0+0")

    def _toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _exit_fullscreen(self, event=None):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)

    # ---------------- chat actions ----------------

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._log("user", text)

        if self.search_mode.get():
            self._set_status("LEARNING...", MAGENTA)
            learned = self.bot.learn_extra_phrase()
            if learned:
                self._log("system", f"// learned a phrase: {learned}")
            else:
                self._log("system", "// nothing new to learn right now")
            self.bot.save()

        self.bot.learn(text)
        self.bot.remember("user", text)

        topic = detect_lookup_topic(text)
        if topic:
            self._start_search(topic)
            return

        # compute the reply now, but reveal it after a short "thinking" beat
        response = self.bot.reply(text)
        response = apply_persona(response, self.persona_name.get())
        self._pending_reply = response

        self._set_status("THINKING...", ACCENT)
        self._log("typing", "BOT is typing...")
        delay = random.randint(*THINK_DELAY_MS)
        self.root.after(delay, self._reveal_reply)

    def _start_search(self, topic):
        self._set_status("SEARCHING...", VIOLET)
        self._log("typing", f"BOT is searching the web for \"{topic}\"...")
        threading.Thread(target=self._search_worker, args=(topic,), daemon=True).start()
        self.root.after(120, self._poll_search)

    def _search_worker(self, topic):
        result = wiki_lookup(topic)
        self._search_queue.put((topic, result))

    def _poll_search(self):
        try:
            topic, result = self._search_queue.get_nowait()
        except queue.Empty:
            self.root.after(120, self._poll_search)
            return

        if result:
            response = f"ok i looked it up -- {result}"
        else:
            response = (f"tried to search the web for \"{topic}\" but couldn't reach it "
                        f"or didn't find anything solid, so idk on that one")
        response = apply_persona(response, self.persona_name.get())
        self._pending_reply = response
        self._reveal_reply()

    def _reveal_reply(self):
        self._remove_last_line()
        response = self._pending_reply
        self._pending_reply = None
        self._log("bot", response)
        self.bot.remember("bot", response)
        self.bot.save()
        self._set_status("ONLINE", TEXT_DIM)
        self._refresh_stats()

        self.awaiting_feedback = True
        self.good_btn.config(state="normal")
        self.bad_btn.config(state="normal")
        self.feedback_label.config(text="rate that reply ->")

    def _clear_feedback_state(self):
        self.awaiting_feedback = False
        self.good_btn.config(state="disabled")
        self.bad_btn.config(state="disabled")
        self.feedback_label.config(text="")

    def mark_good(self):
        if not self.awaiting_feedback:
            return
        self.bot.reinforce(good=True)
        self._log("system", "// reinforced as GOOD")
        self._clear_feedback_state()
        self._refresh_stats()

    def mark_bad(self):
        if not self.awaiting_feedback:
            return
        self.bot.reinforce(good=False)
        self._log("system", "// reinforced as BAD")
        self._clear_feedback_state()
        self._refresh_stats()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()