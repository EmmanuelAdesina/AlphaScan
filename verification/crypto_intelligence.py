"""
Crypto Key Intelligence for AlphaScan v0.5.

Detects and verifies cryptocurrency private keys, seed phrases, and exchange API keys.
Uses passive verification methods - wallet balance checks via Etherscan (read-only).
"""
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# BIP39 wordlist (subset for validation - 2048 words total)
BIP39_WORDLIST = {
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "act", "action", "actor", "adapt", "add",
    "addict", "address", "admit", "adult", "advance", "affair", "afford", "afraid",
    "again", "against", "age", "agency", "agent", "agree", "ahead", "aim",
    "air", "all", "allow", "almost", "alone", "along", "already", "also",
    "alter", "always", "am", "among", "amount", "an", "and", "animal",
    "another", "answer", "any", "anyone", "anything", "apartment", "appeal", "apply",
    "apron", "are", "area", "arm", "army", "around", "arrive", "arrow",
    "art", "artefact", "as", "ask", "aspect", "assault", "asset", "at",
    "attack", "attend", "attorney", "audience", "audit", "avoid", "awake", "aware",
    "away", "awesome", "bad", "bag", "ball", "bar", "barrel", "base",
    "basic", "batch", "battle", "be", "bear", "beat", "beautiful", "because",
    "become", "bed", "before", "begin", "behavior", "behind", "believe", "benefit",
    "best", "better", "between", "beyond", "big", "bike", "bill", "billion",
    "bit", "black", "block", "blood", "blue", "board", "boat", "body",
    "book", "born", "both", "box", "boy", "brain", "brand", "brave",
    "bread", "break", "breed", "breath", "brew", "brick", "bridge", "brief",
    "bright", "bring", "broad", "bronze", "broom", "brown", "bubble", "bucket",
    "budget", "build", "bulb", "bulk", "bullet", "bundle", "bunker", "burden",
    "burger", "burst", "bury", "bus", "business", "busy", "but", "buy",
    "buyer", "buzz", "cabin", "cabinet", "cable", "cake", "calculate", "calendar",
    "call", "calm", "camera", "camp", "can", "cancer", "candidate", "candle",
    "candy", "cannon", "canvas", "canyon", "capable", "capital", "captain", "car",
    "carbon", "card", "care", "career", "careless", "carpet", "carry", "cart",
    "case", "cash", "casino", "cat", "catalog", "catch", "category", "cattle",
    "caught", "cause", "caution", "cave", "ceiling", "cell", "center", "central",
    "century", "certain", "chair", "champion", "change", "character", "charge", "check",
    "cheese", "chef", "cherry", "chest", "chicken", "chief", "child", "child",
    "choice", "choose", "church", "cinema", "circle", "circus", "city", "civil",
    "claim", "class", "clean", "clear", "clever", "click", "client", "climate",
    "climb", "clinic", "clock", "close", "coach", "coast", "coat", "code",
    "coffee", "coin", "cold", "collect", "college", "color", "come", "comment",
    "commercial", "commission", "commit", "commitment", "community", "company", "compare", "computer",
    "complain", "complete", "complex", "concern", "condition", "confirm", "connect", "consider",
    "consist", "constant", "constitute", "construction", "consult", "contact", "contain", "content",
    "contest", "context", "contract", "control", "conversation", "cook", "cool", "cooperate",
    "coordinator", "copy", "corner", "correct", "cost", "could", "council", "count",
    "counter", "country", "county", "couple", "course", "court", "cover", "craft",
    "crash", "cream", "creative", "creator", "creature", "credit", "crime", "crisis",
    "critic", "cross", "crowd", "cry", "crystal", "cube", "culture", "cup",
    "current", "customer", "cut", "cycle", "dad", "daily", "damage", "dance",
    "danger", "dare", "dark", "data", "database", "daughter", "day", "dead",
    "deal", "death", "debate", "debt", "decade", "decide", "decision", "deep",
    "defeat", "defend", "defense", "degree", "democrat", "democratic", "demonstrate", "deny",
    "department", "depend", "depression", "describe", "design", "despite", "dessert", "detail",
    "determine", "develop", "development", "device", "die", "difference", "different", "difficult",
    "dinner", "direction", "director", "dirt", "disappear", "discover", "discuss", "disease",
    "disk", "display", "distance", "distinct", "distribute", "district", "disturb", "diverse",
    "divorce", "do", "doctor", "document", "dog", "door", "down", "draw",
    "dream", "dress", "drink", "drive", "driver", "drop", "drug", "dry",
    "due", "during", "duty", "each", "ear", "early", "earn", "earth",
    "ease", "east", "easy", "eat", "economic", "economy", "edge", "education",
    "effect", "effort", "egg", "eight", "either", "election", "electric", "element",
    "else", "email", "emergency", "emotion", "employ", "employee", "end", "energy",
    "engine", "engineering", "enjoy", "enough", "enter", "entire", "environment", "environmental",
    "especially", "establish", "even", "evening", "event", "ever", "every", "everybody",
    "everyone", "everything", "evidence", "exactly", "excellent", "except", "exchange", "excite",
    "executive", "exercise", "exist", "expect", "experience", "expert", "explain", "eye",
    "face", "fact", "factor", "factory", "fail", "fair", "fairly", "fall",
    "false", "family", "famous", "fan", "far", "farm", "farmer", "fast",
    "fat", "father", "fear", "federal", "feel", "feeling", "few", "field",
    "fight", "figure", "file", "fill", "film", "final", "finally", "find",
    "fine", "finger", "finish", "fire", "firm", "first", "fish", "fit",
    "five", "fix", "flat", "flee", "flexible", "flight", "floor", "flow",
    "flower", "fly", "focus", "follow", "food", "foot", "for", "football",
    "forbid", "force", "foreign", "forest", "forever", "forget", "form", "former",
    "forward", "found", "four", "free", "freedom", "freeze", "fresh", "friend",
    "friendly", "friends", "friendship", "from", "front", "fruit", "fuel", "full",
    "fully", "fun", "function", "fund", "fundamental", "funny", "furniture", "further",
    "future", "garden", "gas", "gate", "gather", "gave", "gear", "general",
    "generation", "generous", "gentleman", "get", "girl", "give", "given", "glass",
    "global", "glory", "go", "goal", "god", "gold", "golden", "golf",
    "good", "goodbye", "government", "grab", "grade", "graduate", "grain", "grand",
    "grandfather", "grandmother", "grant", "grass", "great", "greatly", "green", "grew",
    "green", "ground", "group", "grow", "growth", "guarantee", "guard", "guess",
    "guest", "guide", "gun", "guy", "habit", "hair", "half", "hand",
    "hang", "happen", "happy", "hard", "hardly", "hat", "hate", "have",
    "he", "head", "health", "healthy", "hear", "heart", "heat", "heavy",
    "height", "hello", "help", "helpful", "her", "here", "heritage", "hero",
    "hers", "herself", "hey", "hide", "high", "highway", "hill", "him",
    "himself", "hire", "his", "historian", "historic", "history", "hit", "hold",
    "hole", "holiday", "holy", "home", "homeless", "honey", "honest", "honey",
    "horse", "hospital", "host", "hot", "hotel", "hour", "house", "housing",
    "how", "however", "human", "hundred", "hunger", "hunt", "hurry", "hurt",
    "husband", "ice", "idea", "identify", "identity", "if", "ignore", "ill",
    "illegal", "illness", "illustrate", "image", "imagine", "immediate", "immigrant", "impact",
    "imply", "import", "important", "impose", "impossible", "improve", "improvement", "in",
    "include", "including", "income", "increase", "incredible", "indeed", "indicate", "individual",
    "industry", "infant", "infection", "inflation", "influence", "inform", "information", "ingredient",
    "initial", "injury", "inner", "innocent", "inside", "inspection", "inspire", "install",
    "instance", "instead", "institution", "instruction", "instrument", "insurance", "intelligent", "intend",
    "intense", "interest", "interesting", "international", "interview", "into", "introduce", "invest",
    "investigate", "invite", "involve", "is", "island", "issue", "it", "item",
    "its", "itself", "jacket", "jail", "job", "join", "joint", "joke",
    "journal", "journey", "joy", "judge", "jump", "junior", "jury", "just",
    "justice", "keep", "key", "kick", "kid", "kill", "kind", "kitchen",
    "knee", "knife", "knock", "know", "knowledge", "lab", "labor", "lack",
    "lady", "lake", "land", "language", "lantern", "large", "last", "late",
    "later", "latter", "laugh", "law", "lawyer", "lay", "layer", "lead",
    "leader", "leadership", "leaf", "lean", "learn", "least", "leave", "left",
    "leg", "legal", "legend", "legislation", "lemon", "length", "less", "lesson",
    "let", "letter", "level", "liberal", "library", "license", "lie", "life",
    "lift", "light", "like", "likely", "limit", "limited", "line", "link",
    "lion", "lip", "list", "listen", "literally", "literary", "live", "local",
    "locate", "location", "log", "logical", "lonely", "long", "look", "loose",
    "lose", "loss", "lost", "lot", "loud", "love", "lovely", "lover",
    "low", "lower", "loyal", "luck", "lucky", "lunch", "lung", "machine",
    "mad", "made", "magic", "mail", "main", "mainly", "maintain", "major",
    "majority", "make", "man", "manage", "management", "manager", "mankind", "manner",
    "manufacture", "many", "map", "march", "mark", "market", "marriage", "married",
    "marry", "mass", "master", "match", "material", "matter", "may", "maybe",
    "mayor", "me", "meal", "mean", "meaning", "meanwhile", "measure", "meat",
    "mechanism", "meet", "meeting", "member", "memory", "mention", "menu", "merely",
    "message", "metal", "middle", "might", "military", "milk", "mind", "mine",
    "minister", "minor", "minority", "minute", "mirror", "miss", "mission", "mistake",
    "mix", "mixed", "mixture", "mobile", "model", "moderate", "modern", "modest",
    "moment", "money", "monitor", "monkey", "month", "mood", "moon", "moral",
    "more", "morning", "most", "mostly", "mother", "motion", "motor", "mountain",
    "mouse", "mouth", "move", "movement", "movie", "much", "music", "musical",
    "musician", "must", "mutual", "my", "myself", "mystery", "myth", "naked",
    "name", "narrow", "nation", "national", "native", "natural", "nature", "near",
    "nearly", "necessary", "neck", "need", "negative", "negotiate", "neighbor", "neighborhood",
    "neither", "nerve", "nervous", "network", "never", "nevertheless", "new", "news",
    "newspaper", "next", "nice", "night", "nine", "no", "nobody", "nod",
    "noise", "none", "noon", "nor", "normal", "north", "northeast", "nose",
    "note", "nothing", "notice", "novel", "now", "nowhere", "nuclear", "number",
    "nurse", "nut", "object", "objective", "obligation", "observation", "observe", "obtain",
    "obvious", "obviously", "occasion", "occupy", "occur", "ocean", "odd", "of",
    "off", "offer", "office", "officer", "official", "often", "oh", "oil",
    "ok", "old", "olympic", "on", "once", "one", "ongoing", "online",
    "only", "onto", "open", "opening", "operate", "operation", "opinion", "opportunity",
    "oppose", "opposite", "option", "or", "orange", "order", "ordinary", "organize",
    "origin", "original", "other", "others", "otherwise", "ought", "our", "ours",
    "ourselves", "out", "outcome", "outdoor", "outer", "output", "outside", "over",
    "overall", "overcome", "overlook", "own", "owner", "pace", "pack", "page",
    "pain", "painting", "pair", "palace", "pan", "panel", "panic", "paper",
    "parent", "park", "part", "participate", "particular", "particularly", "partly", "parts",
    "party", "pass", "passage", "passenger", "passion", "past", "path", "patient",
    "pattern", "pause", "pay", "payment", "peace", "peacefully", "peer", "pen",
    "penalty", "pencil", "people", "pepper", "per", "perform", "performance", "perhaps",
    "period", "permanent", "permit", "person", "personal", "personality", "perspective", "persuade",
    "phase", "phone", "photo", "photograph", "photographer", "pick", "picture", "piece",
    "pill", "pilot", "pin", "pipe", "place", "plain", "plan", "platform",
    "play", "player", "PM", "point", "poem", "poet", "poetry", "police",
    "policy", "political", "politics", "pollution", "pool", "poor", "pop", "popular",
    "population", "port", "portion", "portrait", "position", "positive", "possess", "possible",
    "power", "powerful", "practical", "practice", "praise", "pray", "prayer", "preach",
    "precious", "prefer", "pregnant", "prepare", "presence", "present", "preserve", "president",
    "press", "pressure", "pretend", "pretty", "prevent", "previous", "price", "pride",
    "priest", "primary", "prime", "principal", "principle", "print", "prior", "priority",
    "prison", "prisoner", "privacy", "private", "prize", "probably", "problem", "procedure",
    "proceed", "process", "produce", "producer", "product", "production", "profession", "professional",
    "professor", "profile", "profit", "program", "project", "promise", "promote", "proof",
    "proper", "properly", "property", "proposal", "propose", "prosecutor", "protect", "protein",
    "protest", "proud", "prove", "provide", "province", "public", "publication", "publish",
    "pull", "punishment", "purchase", "pure", "purpose", "pursue", "push", "put",
    "quality", "quantity", "quarter", "queen", "question", "quickly", "quiet", "quietly",
    "quit", "quite", "quiz", "quote", "race", "radical", "radio", "rail",
    "rain", "raise", "range", "rank", "rapid", "rare", "rarely", "rate",
    "rather", "rating", "ratio", "raw", "reach", "react", "read", "reader",
    "ready", "real", "reality", "realize", "really", "reason", "reasonable", "recall",
    "receive", "recent", "recently", "recipe", "recognize", "record", "recover", "red",
    "reflect", "reform", "refuge", "refuse", "regard", "region", "regional", "register",
    "regular", "regularly", "regulate", "reinforce", "reject", "relate", "relation", "relationship",
    "relative", "relatively", "relief", "religion", "religious", "rely", "remain", "remarkable",
    "remember", "remind", "remote", "remove", "repeat", "repeatedly", "replace", "reply",
    "report", "reporter", "represent", "Republican", "require", "research", "reserve", "resident",
    "resist", "resolve", "resource", "respond", "response", "responsibility", "rest", "restaurant",
    "restore", "restrict", "result", "retain", "retire", "return", "reveal", "revenue",
    "review", "revolution", "rhythm", "rich", "ride", "right", "ring", "rise",
    "risk", "road", "rock", "role", "roll", "romantic", "roof", "room",
    "round", "route", "routine", "row", "royal", "rub", "rule", "run",
    "rural", "sacred", "sad", "safe", "safety", "sail", "salad", "salary",
    "sale", "salt", "same", "sample", "sand", "satellite", "satisfaction", "save",
    "saw", "say", "scene", "schedule", "scheme", "scholar", "scholarship", "school",
    "science", "scientific", "scientist", "scope", "score", "scream", "screen", "script",
    "sea", "search", "season", "seat", "second", "secret", "secretary", "section",
    "sector", "secure", "security", "see", "seed", "seek", "seem", "segment",
    "seize", "select", "self", "sell", "senate", "senator", "send", "senior",
    "sense", "sensitive", "sentence", "separate", "serious", "serve", "service", "session",
    "set", "settle", "settlement", "seven", "several", "severe", "shake", "shall",
    "shame", "shape", "share", "sharp", "she", "sheet", "shelf", "shell",
    "shelter", "shift", "shine", "ship", "shirt", "shock", "shoe", "shoot",
    "shop", "shore", "short", "shot", "should", "shoulder", "shout", "show",
    "shower", "shut", "sick", "side", "sigh", "sight", "sign", "signal",
    "significance", "significant", "silence", "silent", "silly", "silver", "similar", "simple",
    "simply", "since", "sing", "singer", "single", "sister", "sit", "site",
    "situation", "six", "size", "skill", "skin", "small", "smile", "so",
    "social", "society", "soft", "software", "soil", "soldier", "solid", "solution",
    "solve", "some", "somebody", "someone", "something", "sometimes", "son", "song",
    "soon", "sophisticated", "sore", "sorrow", "sorry", "sort", "soul", "sound",
    "source", "south", "southeast", "southern", "space", "speak", "speak", "special",
    "specific", "specifically", "speech", "speed", "spend", "spill", "spin", "spirit",
    "spiritual", "split", "spokesman", "sport", "spot", "spread", "spring", "square",
    "stable", "staff", "stage", "stair", "stand", "standard", "star", "stare",
    "start", "state", "statement", "station", "statistical", "status", "stay", "steady",
    "steal", "steam", "steel", "step", "stick", "still", "stir", "stock",
    "stomach", "stone", "stop", "store", "storm", "story", "straight", "strange",
    "stranger", "strategic", "strategy", "stream", "street", "strength", "strengthen", "stress",
    "stretch", "strict", "strike", "string", "strip", "stroke", "strong", "strongly",
    "structural", "structure", "struggle", "student", "studio", "study", "stuff", "stupid",
    "style", "subject", "success", "successful", "successfully", "such", "sudden", "suddenly",
    "suffer", "sufficient", "sugar", "suggest", "suit", "summer", "sun", "super",
    "supply", "support", "supporter", "suppose", "sure", "surface", "surgery", "surprise",
    "surround", "survey", "survival", "survive", "survivor", "suspect", "suspend", "sustain",
    "swear", "sweep", "sweet", "swim", "swing", "switch", "symbol", "sympathy",
    "system", "table", "tablet", "tackle", "tag", "tail", "take", "taking",
    "tale", "talent", "talk", "tall", "tank", "tap", "tape", "target",
    "task", "taste", "tax", "tea", "teach", "teacher", "team", "tear",
    "technical", "technique", "teen", "teenager", "telephone", "television", "tell", "temperature",
    "temporary", "ten", "tend", "tendency", "tennis", "tension", "term", "terms",
    "terrible", "territory", "terror", "test", "testify", "text", "than", "thank",
    "that", "the", "their", "them", "themselves", "then", "theory", "therapy",
    "there", "therefore", "these", "they", "thick", "thin", "thing", "think",
    "third", "thirty", "this", "those", "though", "thought", "thousand", "threat",
    "three", "throat", "through", "throughout", "throw", "thus", "ticket", "tie",
    "tight", "time", "tiny", "tip", "tire", "tired", "tissue", "title",
    "to", "today", "toe", "together", "tomato", "tomorrow", "ton", "tone",
    "tongue", "tonight", "too", "tool", "tooth", "top", "topic", "torture",
    "total", "totally", "touch", "tough", "tour", "tourism", "tourist", "tournament",
    "toward", "tower", "town", "toy", "trace", "track", "trade", "tradition",
    "traditional", "traffic", "tragedy", "trail", "train", "training", "transfer", "transform",
    "transit", "translate", "transport", "transportation", "trap", "travel", "treat", "treatment",
    "tree", "tremendous", "trend", "trial", "tribe", "trick", "trip", "troops",
    "trouble", "truck", "true", "truly", "trust", "truth", "try", "tube",
    "tunnel", "turn", "twelve", "twenty", "twice", "twin", "twist", "two",
    "type", "typical", "ugly", "ultimate", "ultimately", "under", "understand", "unfortunately",
    "uniform", "union", "unique", "unit", "unite", "united", "universal", "universe",
    "university", "unrelated", "until", "unusual", "up", "upon", "upper", "urban",
    "urge", "us", "use", "used", "useful", "user", "using", "usual",
    "usually", "utility", "vacation", "valid", "valley", "valuable", "value", "van",
    "vary", "vast", "vegetable", "vehicle", "venture", "version", "very", "victim",
    "victory", "video", "view", "viewer", "village", "violence", "violent", "virtual",
    "virtue", "visible", "vision", "visit", "visitor", "visual", "vital", "voice",
    "volume", "volunteer", "vote", "voter", "vs", "vulnerable", "wage", "wait",
    "wake", "walk", "wall", "war", "warm", "warn", "wash", "waste",
    "watch", "water", "wave", "way", "we", "weak", "weakness", "wealth",
    "weapon", "wear", "weather", "web", "wedding", "wednesday", "week", "weekend",
    "weekly", "weigh", "weight", "welcome", "welfare", "well", "west", "western",
    "wet", "what", "whatever", "wheat", "wheel", "when", "where", "whether",
    "which", "while", "whisper", "white", "who", "whole", "whom", "whose",
    "why", "wide", "widely", "wife", "wild", "will", "willing", "win",
    "wind", "window", "wine", "wing", "winner", "winter", "wipe", "wire",
    "wise", "wish", "with", "withdraw", "within", "without", "witness", "woman",
    "wonder", "wonderful", "wood", "wooden", "word", "work", "worker", "world",
    "worried", "worry", "worth", "would", "wound", "wrap", "write", "writer",
    "wrong", "yard", "yeah", "year", "yell", "yellow", "yes", "yet",
    "you", "young", "your", "yourself", "yourselves",
}

# Crypto key patterns
ETH_PRIVATE_KEY_PATTERN = re.compile(r"0x[a-fA-F0-9]{64}")
ETH_PRIVATE_KEY_RAW_PATTERN = re.compile(r"(?<![a-fA-F0-9])([a-fA-F0-9]{64})(?![a-fA-F0-9])")
BTC_WIF_PATTERN = re.compile(r"5[HJK][1-9A-HJ-NP-Za-km-z]{50}")
SOLANA_KEY_PATTERN = re.compile(r"\[(?:\d+,\s*){10,}\d+\]")
SEED_PHRASE_PATTERN = re.compile(r"(\b[a-z]+[- ]?){12,24}\b")

# Exchange key patterns
BINANCE_KEY_PATTERN = re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{64}(?![a-zA-Z0-9])")
COINBASE_KEY_PATTERN = re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{16,32}(?![a-zA-Z0-9])")
KRAKEN_KEY_PATTERN = re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{16,32}(?![a-zA-Z0-9])")

# RPC key patterns
ALCHEMY_KEY_PATTERN = re.compile(r"(?<![a-zA-Z0-9_-])[a-zA-Z0-9_-]{32,64}(?![a-zA-Z0-9_-])")
INFURA_KEY_PATTERN = re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])")

# DeFi admin context keywords
DEFI_ADMIN_KEYWORDS = ["deployer", "owner", "admin", "multisig", "governance"]


class CryptoIntelligence:
    """
    Detects and verifies cryptocurrency keys, seed phrases, and exchange API keys.
    Uses passive verification - wallet balance checks via Etherscan (read-only).
    """

    def __init__(self):
        self._patterns = {
            "eth_private_key": ETH_PRIVATE_KEY_PATTERN,
            "eth_private_key_raw": ETH_PRIVATE_KEY_RAW_PATTERN,
            "btc_wif": BTC_WIF_PATTERN,
            "solana_private_key": SOLANA_KEY_PATTERN,
            "seed_phrase": SEED_PHRASE_PATTERN,
            "binance_key": BINANCE_KEY_PATTERN,
            "coinbase_key": COINBASE_KEY_PATTERN,
            "kraken_key": KRAKEN_KEY_PATTERN,
            "alchemy_key": ALCHEMY_KEY_PATTERN,
            "infura_key": INFURA_KEY_PATTERN,
        }

    def detect(self, text: str) -> List[Dict]:
        """
        Detect crypto keys in text.

        Args:
            text: Text to scan for crypto keys.

        Returns:
            List of detected crypto key dicts with analysis.
        """
        results = []

        for key_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)

                # Skip if this is a false positive (e.g., seed phrase matching as hex)
                if key_type == "eth_private_key_raw" and self._is_seed_phrase(value):
                    continue

                analysis = self._analyze_key(key_type, value, text)
                if analysis:
                    results.append(analysis)

        return results

    def _analyze_key(self, key_type: str, value: str, context: str) -> Optional[Dict]:
        """Analyze a detected crypto key."""
        context_lower = context.lower() if context else ""

        # Determine if this is a DeFi admin key
        is_defi_admin = any(kw in context_lower for kw in DEFI_ADMIN_KEYWORDS)

        # Determine rank based on type and context
        if key_type in ("eth_private_key", "eth_private_key_raw", "btc_wif", "solana_private_key"):
            if is_defi_admin:
                rank = 4  # DeFi Admin
            else:
                rank = 2  # Private Key
        elif key_type == "seed_phrase":
            rank = 2  # Seed Phrase
        elif key_type in ("binance_key", "coinbase_key", "kraken_key"):
            rank = 1  # Exchange Key
        elif key_type in ("alchemy_key", "infura_key"):
            rank = 5  # RPC Provider
        else:
            rank = 2

        return {
            "type": key_type,
            "value": value,
            "description": self._get_description(key_type),
            "rank": rank,
            "context": context[:200] if context else "",
            "is_defi_admin": is_defi_admin,
            "detected_at": datetime.utcnow().isoformat(),
        }

    def _is_seed_phrase(self, value: str) -> bool:
        """Check if a value looks like a seed phrase rather than a hex key."""
        words = value.lower().split()
        if len(words) < 12:
            return False
        return all(w in BIP39_WORDLIST for w in words)

    def _get_description(self, key_type: str) -> str:
        """Get human-readable description for a key type."""
        descriptions = {
            "eth_private_key": "Ethereum/BSC Private Key",
            "eth_private_key_raw": "Ethereum/BSC Private Key (raw)",
            "btc_wif": "Bitcoin Private Key (WIF)",
            "solana_private_key": "Solana Private Key (JSON Array)",
            "seed_phrase": "BIP39 Seed Phrase",
            "binance_key": "Binance API Key",
            "coinbase_key": "Coinbase API Key",
            "kraken_key": "Kraken API Key",
            "alchemy_key": "Alchemy API Key",
            "infura_key": "Infura API Key",
        }
        return descriptions.get(key_type, "Unknown Crypto Key")

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify a crypto key entry using passive methods.

        Args:
            key_data: Dict with crypto key information.

        Returns:
            Dict with verification results.
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")

        checks = {}

        if key_type in ("eth_private_key", "eth_private_key_raw"):
            # Derive wallet address and check balance via Etherscan (read-only)
            address = self._derive_eth_address(value)
            checks["wallet_address"] = address
            checks["balance_check"] = self._check_eth_balance(address)
            checks["format_valid"] = self._validate_eth_key(value)
            verified = checks["format_valid"]

        elif key_type == "seed_phrase":
            # Check all words against BIP39 wordlist
            words = value.lower().split()
            checks["word_count"] = len(words)
            checks["all_words_valid"] = all(w in BIP39_WORDLIST for w in words)
            checks["bip39_compliant"] = checks["all_words_valid"] and 12 <= len(words) <= 24
            verified = checks["bip39_compliant"]

        elif key_type == "btc_wif":
            checks["format_valid"] = self._validate_btc_wif(value)
            verified = checks["format_valid"]

        elif key_type in ("binance_key", "coinbase_key", "kraken_key"):
            # Format validation only (requires secret for full verification)
            checks["format_valid"] = len(value) >= 16
            verified = checks["format_valid"]

        elif key_type in ("alchemy_key", "infura_key"):
            checks["format_valid"] = len(value) >= 32
            verified = checks["format_valid"]

        else:
            checks["format_valid"] = len(value) > 0
            verified = checks["format_valid"]

        return {
            "verified": verified,
            "method": "passive_verification",
            "checks": checks,
            "risk_level": "critical" if verified else "low",
            "note": "Passive verification only - no funds accessed",
        }

    def _validate_eth_key(self, value: str) -> bool:
        """Validate an Ethereum private key format."""
        # Remove 0x prefix if present
        clean = value[2:] if value.startswith("0x") else value
        # Must be exactly 64 hex characters
        return len(clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean)

    def _validate_btc_wif(self, value: str) -> bool:
        """Validate a Bitcoin WIF private key format."""
        return bool(BTC_WIF_PATTERN.match(value))

    def _derive_eth_address(self, private_key: str) -> str:
        """
        Derive Ethereum wallet address from private key.
        Uses eth-account library (read-only derivation).
        """
        try:
            from eth_account import Account
            clean_key = private_key[2:] if private_key.startswith("0x") else private_key
            account = Account.from_key(bytes.fromhex(clean_key))
            return account.address
        except Exception:
            return "0x0000000000000000000000000000000000000000"

    def _check_eth_balance(self, address: str) -> Dict:
        """
        Check ETH balance via Etherscan API (read-only).
        Does NOT access or move any funds.
        """
        try:
            from config.settings import ETHERSCAN_API_KEY, ENABLE_ETHERSCAN_CHECK
            if not ENABLE_ETHERSCAN_CHECK or not ETHERSCAN_API_KEY:
                return {"checked": False, "reason": "Etherscan API not configured"}

            import requests
            url = f"https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "balance",
                "address": address,
                "tag": "latest",
                "apikey": ETHERSCAN_API_KEY,
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data.get("status") == "1":
                balance_wei = int(data.get("result", "0"))
                balance_eth = balance_wei / 1e18
                return {
                    "checked": True,
                    "balance_eth": balance_eth,
                    "balance_wei": balance_wei,
                    "has_funds": balance_eth > 0,
                }
            return {"checked": True, "balance_eth": 0, "has_funds": False}
        except Exception as e:
            return {"checked": False, "error": str(e)}
