"""
Email content cleaning utility for removing HTML, quotes, and noise.
Provides centralized email cleaning logic for all email providers.
"""

import re
import html2text
from bs4 import BeautifulSoup
from email_reply_parser import EmailReplyParser
import logging

logger = logging.getLogger(__name__)
from typing import Optional, Dict, Tuple


class EmailCleaner:
    """
    Centralized email content cleaner that handles:
    - HTML to text conversion
    - Quote removal from replies
    - Text normalization and cleanup
    - Signature detection and removal
    """
    
    def __init__(self):
        # Configure html2text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # No line wrapping
        self.html_converter.unicode_snob = True
        
    def clean_email_content(self, email_data: dict) -> dict:
        """
        Main cleaning function that processes email content.
        
        Args:
            email_data: Email data dictionary with body_text and body_html
            
        Returns:
            Updated email_data with cleaned content
        """
        try:
            body_text = email_data.get("body_text", "")
            body_html = email_data.get("body_html", "")
            
            # Step 1: Get the best text representation
            clean_text = self._get_best_text_content(body_text, body_html)
            
            # Step 2: Detect email type (reply vs forward) before quote removal
            email_type = self._detect_email_type(email_data, clean_text)
            email_data["email_type"] = email_type
            
            # Step 3: Remove quoted content (replies) - but preserve forward content
            if email_type != "forward":
                clean_text = self._remove_quoted_content(clean_text)
            else:
                # For forwards, preserve the forwarded content but clean it
                clean_text = self._clean_forwarded_content(clean_text)
            
            # Step 4: Clean and normalize text
            clean_text = self._normalize_text(clean_text)
            
            # Step 4: Remove signatures if detected
            clean_text = self._remove_signatures(clean_text)
            
            # Step 5: Clean subject line
            subject = email_data.get("subject", "")
            if subject:
                email_data["subject"] = self.clean_subject(subject)
                email_data["original_subject"] = subject  # Keep original for reference
            
            # Update email data with cleaned content
            email_data["body_text"] = clean_text
            email_data["original_body_text"] = body_text  # Keep original for reference
            email_data["original_body_html"] = body_html  # Keep original for reference
            
            print(f"🧹 [CLEANER] Cleaned email content: {len(body_text or '')} → {len(clean_text)} chars")
            
            return email_data
            
        except Exception as e:
            print(f"❌ [CLEANER] Error cleaning email content: {e}")
            # Return original data if cleaning fails
            return email_data
    
    def _get_best_text_content(self, body_text: str, body_html: str) -> str:
        """
        Get the best text representation from available content.
        Prefers clean text, but converts HTML if needed.
        """
        # If we have good text content, use it
        if body_text and len(body_text.strip()) > 0:
            # Check if text seems to be HTML escaped
            if "&lt;" in body_text or "&gt;" in body_text or "&amp;" in body_text:
                # Text contains HTML entities, try to clean it
                import html
                decoded_text = html.unescape(body_text)
                if self._looks_like_html(decoded_text):
                    return self._html_to_text(decoded_text)
                return decoded_text
            return body_text
        
        # If no text but we have HTML, convert it
        if body_html and len(body_html.strip()) > 0:
            return self._html_to_text(body_html)
        
        # Fallback to whatever we have
        return body_text or body_html or ""
    
    def _looks_like_html(self, text: str) -> bool:
        """Check if text appears to contain HTML markup."""
        html_indicators = ["<html", "<body", "<div", "<p>", "<br", "<span", "</"]
        return any(indicator in text.lower() for indicator in html_indicators)
    
    def _html_to_text(self, html_content: str) -> str:
        """
        Convert HTML content to clean text using multiple approaches.
        """
        if not html_content or not html_content.strip():
            return ""
        
        try:
            # Method 1: Try html2text first (best for email formatting)
            text_content = self.html_converter.handle(html_content)
            
            # Method 2: If html2text fails or produces poor results, try BeautifulSoup
            if not text_content or len(text_content.strip()) < len(html_content.strip()) * 0.1:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text_content = soup.get_text()
            
            return text_content.strip()
            
        except Exception as e:
            print(f"⚠️ [CLEANER] HTML conversion error: {e}")
            # Fallback: simple HTML tag removal
            return self._simple_html_strip(html_content)
    
    def _simple_html_strip(self, html_content: str) -> str:
        """Fallback method for HTML tag removal using regex."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Decode HTML entities
        import html
        text = html.unescape(text)
        return text.strip()
    
    def _remove_quoted_content(self, text: str) -> str:
        """
        Remove quoted content from email replies using email_reply_parser.
        """
        try:
            # Use email_reply_parser to extract only the new content
            parsed = EmailReplyParser.parse_reply(text)
            return parsed.strip() if parsed else text
            
        except Exception as e:
            print(f"⚠️ [CLEANER] Quote removal error: {e}")
            # Fallback: manual quote detection
            return self._manual_quote_removal(text)
    
    def _manual_quote_removal(self, text: str) -> str:
        """
        Fallback method for quote removal using patterns.
        """
        lines = text.split('\n')
        cleaned_lines = []
        quote_started = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect common quote patterns
            quote_patterns = [
                r'^>.*',  # Lines starting with >
                r'^On.*wrote:$',  # "On [date] [person] wrote:"
                r'^Il giorno.*ha scritto:$',  # Italian version
                r'^Le.*a écrit:$',  # French version
                r'^Am.*schrieb:$',  # German version
                r'^El.*escribió:$',  # Spanish version
                r'^From:.*',  # Email header patterns
                r'^Sent:.*',
                r'^To:.*',
                r'^Subject:.*',
                r'^Da:.*',  # Italian headers
                r'^Inviato:.*',
                r'^A:.*',
                r'^Oggetto:.*',
            ]
            
            # Check if this line starts a quote
            if any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in quote_patterns):
                quote_started = True
                break
            
            # If we haven't hit quotes yet, keep the line
            if not quote_started:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize and clean text content.
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces and tabs
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{3,}', '!!!', text)  # Max 3 exclamation marks
        text = re.sub(r'[?]{3,}', '???', text)  # Max 3 question marks
        text = re.sub(r'[.]{4,}', '...', text)  # Max 3 dots
        
        # Remove control characters but keep useful ones
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def _remove_signatures(self, text: str) -> str:
        """
        Detect and remove email signatures.
        """
        lines = text.split('\n')
        signature_indicators = [
            r'^--\s*$',  # Standard signature delimiter
            r'^Sent from my \w+',  # Mobile signatures
            r'^Get Outlook for \w+',  # Outlook mobile
            r'^Inviato da \w+',  # Italian mobile
            r'^Best regards?[,.]?$',  # Common closings
            r'^Kind regards?[,.]?$',
            r'^Sincerely[,.]?$',
            r'^Cordiali saluti[,.]?$',  # Italian closing
            r'^Distinti saluti[,.]?$',
            r'^Grazie[,.]?$',
            r'^Thanks?[,.]?$',
        ]
        
        # Find signature start
        signature_start = None
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in signature_indicators):
                signature_start = i
                break
        
        # If signature found, remove it and everything after
        if signature_start is not None:
            lines = lines[:signature_start]
        
        return '\n'.join(lines).strip()
    
    def clean_subject(self, subject: str) -> str:
        """
        Clean email subject line.
        """
        if not subject:
            return ""
        
        # Remove common prefixes
        subject = re.sub(r'^(Re:|RE:|Fwd:|FWD:|Fw:|\[EXTERNAL\]|\[Ext\])\s*', '', subject, flags=re.IGNORECASE).strip()
        
        # Remove excessive whitespace
        subject = re.sub(r'\s+', ' ', subject)
        
        return subject.strip()
    
    def extract_metadata(self, original_text: str, cleaned_text: str) -> Dict[str, any]:
        """
        Extract useful metadata from the cleaning process.
        """
        return {
            "original_length": len(original_text),
            "cleaned_length": len(cleaned_text),
            "reduction_ratio": (len(original_text) - len(cleaned_text)) / len(original_text) if original_text else 0,
            "had_html": self._looks_like_html(original_text),
            "had_quotes": len(cleaned_text) < len(original_text) * 0.8,  # Heuristic
        }
    
    def _detect_email_type(self, email_data: dict, body_text: str) -> str:
        """
        Detect if email is a forward, reply, or original message
        
        Returns:
            - "forward": Email è un messaggio inoltrato
            - "reply": Email è una risposta 
            - "original": Email originale
        """
        try:
            subject = email_data.get("subject", "").lower()
            body_lower = body_text.lower()
            
            # 1. Check subject for forward indicators
            forward_subject_patterns = [
                "fwd:", "fw:", "forward:", "forwarded:",
                "i:", "tr:", "trasf:", "inolt:",  # Italian
                "enc:", "reenviado:",  # Spanish
                "weiterleitung:", "wg:",  # German
                "rép:", "transféré:",  # French
            ]
            
            for pattern in forward_subject_patterns:
                if subject.startswith(pattern):
                    logger.debug(f"Forward detected via subject pattern: {pattern}")
                    return "forward"
            
            # 2. Check body for forward indicators
            forward_body_patterns = [
                "forwarded message", "messaggio inoltrato", "mensaje reenviado",
                "nachricht weiterleiten", "message transféré",
                "-----original message-----", "-----messaggio originale-----",
                "-----mensaje original-----", "-----ursprüngliche nachricht-----",
                "-----message d'origine-----",
                "from:", "sent:", "to:", "subject:",  # Email header block
                "da:", "inviato:", "a:", "oggetto:",  # Italian headers
                "de:", "enviado:", "para:", "asunto:",  # Spanish headers
            ]
            
            forward_indicators = 0
            for pattern in forward_body_patterns:
                if pattern in body_lower:
                    forward_indicators += 1
                    if forward_indicators >= 2:  # Multiple indicators = likely forward
                        logger.debug(f"Forward detected via body patterns")
                        return "forward"
            
            # 3. Check for reply indicators (after ruling out forward)
            reply_indicators = [
                email_data.get("in_reply_to"),
                email_data.get("references"),
            ]
            
            if any(reply_indicators):
                logger.debug("Reply detected via headers")
                return "reply"
            
            # 4. Default to original message
            return "original"
            
        except Exception as e:
            logger.error(f"Error detecting email type: {e}")
            return "original"
    
    def _clean_forwarded_content(self, text: str) -> str:
        """
        Clean forwarded content while preserving the forwarded message
        """
        try:
            # Remove multiple newlines but preserve structure
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            
            # Clean up header blocks but don't remove them entirely
            text = re.sub(r'(From|Da|De|Sent|Inviato|Enviado|To|A|Para|Subject|Oggetto|Asunto):\s*', r'\1: ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning forwarded content: {e}")
            return text if text else ""