import os, json, re
from agents.base_agent import BaseAgent

class TranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "translator_agent",
            "Translate text between multiple languages, detect language, and provide translations",
        )
        self.capabilities = ["translate", "translation", "language", "spanish", "french", "urdu", "hindi"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "detect" in t:
            return self._detect_language(task)
        if "list" in t or "supported" in t:
            return self._list_languages()
        content = re.sub(r'\b(translate|to|from|in|into)\b', '', task, flags=re.IGNORECASE)
        content = content.strip()
        target_lang = self._detect_target(t)
        source_lang = self._detect_source(t)
        if content and len(content) > 2:
            return self._translate(content, source_lang, target_lang)
        return f"TranslatorAgent: Usage: translate 'Hello' to Spanish\nSupported: {', '.join(list(self.languages().keys())[:15])}..."

    def languages(self):
        return {
            "spanish": "es", "french": "fr", "german": "de", "italian": "it",
            "portuguese": "pt", "russian": "ru", "japanese": "ja", "korean": "ko",
            "chinese": "zh", "arabic": "ar", "hindi": "hi", "urdu": "ur",
            "dutch": "nl", "polish": "pl", "turkish": "tr", "vietnamese": "vi",
            "thai": "th", "swedish": "sv", "danish": "da", "finnish": "fi",
            "norwegian": "no", "czech": "cs", "romanian": "ro", "hungarian": "hu",
            "greek": "el", "hebrew": "he", "indonesian": "id", "malay": "ms",
            "english": "en",
        }

    def _detect_source(self, task):
        t = task.lower()
        match = re.search(r'from\s+(\w+)', t)
        if match:
            lang = match.group(1)
            return self.languages().get(lang, lang)
        return "auto"

    def _detect_target(self, task):
        t = task.lower()
        match = re.search(r'to\s+(\w+)', t)
        if match:
            lang = match.group(1)
            return self.languages().get(lang, lang)
        match = re.search(r'in\s+(\w+)', t)
        if match:
            lang = match.group(1)
            return self.languages().get(lang, lang)
        return "es"

    def _detect_language(self, task):
        text = re.sub(r'\b(detect|language)\b', '', task, flags=re.IGNORECASE).strip()
        if not text:
            return "TranslatorAgent: Please provide text to detect"
        try:
            import requests
            r = requests.post("https://libretranslate.com/detect", json={"q": text[:500]}, timeout=10)
            if r.status_code == 200:
                results = r.json()
                if results:
                    best = max(results, key=lambda x: x.get("confidence", 0))
                    return f"TranslatorAgent: Detected language: {best.get('language', 'unknown')} (confidence: {best.get('confidence', 0)*100:.0f}%)"
        except Exception:
            lang_marks = {
                "ur": ["ہے", "کا", "کی", "میں", "اور", "ہیں", "سے", "پر", "نہیں", "گے"],
                "hi": ["है", "का", "की", "में", "और", "हैं", "से", "पर", "नहीं", "गे"],
                "es": ["el", "la", "los", "las", "que", "es", "por", "con", "una", "para"],
                "fr": ["le", "la", "les", "que", "est", "pas", "pour", "dans", "une", "sur"],
                "de": ["der", "die", "das", "ist", "nicht", "ein", "eine", "auf", "für", "mit"],
            }
            scores = {}
            text_lower = text.lower()
            for lang, markers in lang_marks.items():
                scores[lang] = sum(1 for m in markers if m in text_lower)
            if max(scores.values()) > 2:
                best = max(scores, key=scores.get)
                return f"TranslatorAgent: Likely language: {best} (based on common words)"
            return "TranslatorAgent: Could not determine language (LibreTranslate unavailable)"
        return "TranslatorAgent: Could not detect language"

    def _translate(self, text, source, target):
        try:
            payload = {"q": text[:1000], "source": source, "target": target, "format": "text"}
            import requests
            r = requests.post("https://libretranslate.com/translate", json=payload, timeout=15)
            if r.status_code == 200:
                translated = r.json().get("translatedText", text)
                return f"TranslatorAgent: Translation ({source} -> {target}):\n\n{translated[:500]}"
            if r.status_code == 429:
                return "TranslatorAgent: Translation service rate limited. Try again later."
            return f"TranslatorAgent: Translation failed (HTTP {r.status_code})"
        except ImportError:
            return "TranslatorAgent: requests not installed"
        except Exception as e:
            return f"TranslatorAgent: Translation failed: {e}. Using offline fallback.\n\n'{text}' in {target}: [Translation requires internet access to LibreTranslate API]"

    def _list_languages(self):
        langs = self.languages()
        result = "TranslatorAgent: Supported Languages:\n"
        for name, code in sorted(langs.items()):
            result += f"  {name} ({code})\n"
        return result
