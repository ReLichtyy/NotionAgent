import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any
from core.logger import get_logger
from core.config import get_settings

logger = get_logger("SearchIndex")

class SimpleSearchIndex:
    def __init__(self):
        self.settings = get_settings()
        self.fragments_file = self.settings.NOTION_JSON_PATH
        self.fragments: List[Dict[str, Any]] = []
        self._load_fragments()

    def _load_fragments(self):
        if not os.path.exists(self.fragments_file):
            logger.warning(f"Fragments file {self.fragments_file} not found. Search index is empty.")
            return
            
        try:
            with open(self.fragments_file, "r", encoding="utf-8") as f:
                self.fragments = json.load(f)
            logger.info(f"Loaded {len(self.fragments)} fragments into search index.")
        except Exception as e:
            logger.error(f"Failed to load fragments: {e}")

    def _normalize_text(self, text: str) -> str:
        """Converts to lowercase, removes accents and punctuation for simpler matching."""
        if not text:
            return ""
        # Remove accents
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Searches the fragments using a fuzzy keyword scoring system.
        """
        if top_k is None:
            top_k = self.settings.NOTION_SEARCH_TOP_K
            
        if not self.fragments:
            return []
            
        norm_query = self._normalize_text(query)
        keywords = norm_query.split()
        
        if not keywords:
            return []
            
        results = []
        
        for frag in self.fragments:
            score = 0
            
            # Normalize fragment fields
            title_norm = self._normalize_text(frag.get("title", ""))
            path_norm = self._normalize_text(frag.get("path", ""))
            text_norm = self._normalize_text(frag.get("text", ""))
            
            # 1. Score against exact normalized full query
            if norm_query in title_norm:
                score += 50  # Huge boost for exact title match
            elif norm_query in path_norm:
                score += 30  # Big boost for path match
                
            # 2. Fuzzy match on title (Tolerance for typos like "lyfe" vs "life")
            title_ratio = SequenceMatcher(None, norm_query, title_norm).ratio()
            if title_ratio > 0.8:
                score += int(title_ratio * 40)
            
            # 3. Score individual keywords
            for kw in keywords:
                # Discard stop words and short words
                if len(kw) <= 3 or kw in ["como", "para", "pero", "esta", "esto", "todo", "sobre", "cual"]:
                    continue
                    
                # Title keyword match
                title_words = title_norm.split()
                if kw in title_words:
                    score += 20
                else:
                    # Partial / Substring title match
                    if kw in title_norm:
                        score += 10
                    # Fuzzy keyword match
                    for tw in title_words:
                        if SequenceMatcher(None, kw, tw).ratio() > 0.8:
                            score += 15
                            break
                    
                # Path keyword match
                if kw in path_norm.split():
                    score += 10
                    
                # Text content keyword frequency
                occurrences = text_norm.split().count(kw)
                score += (occurrences * 2) # +2 per occurrence in text
                
            if score > 0:
                results.append((score, frag))
                
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top_k fragments (without the score)
        return [res[1] for res in results[:top_k]]
