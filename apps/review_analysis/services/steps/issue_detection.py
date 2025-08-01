"""
Шаг обнаружения проблем и запросов в отзывах
"""
import re
import logging
from typing import Dict, Any, List

from apps.review.models import Review
from ..base import BaseAnalysisStep, StepRegistry


logger = logging.getLogger(__name__)

# Опциональные зависимости
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    nlp = None
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available for advanced issue detection")


@StepRegistry.register('issue_detection')
class IssueDetectionStep(BaseAnalysisStep):
    """
    Интеллектуальное обнаружение проблем и запросов функций
    """
    
    # Расширенные паттерны для технических проблем
    TECH_PROBLEMS = {
        'crash': {
            'pattern': r'\b(crash(?:es|ed|ing)?|shut(?:s)?\s*down|close(?:s|d)?\s*(?:itself|automatically)|force(?:d)?\s*close|app\s*(?:dies|died|dying))\b',
            'context_negatives': ['no crash', 'never crash', 'without crash', 'crash fixed', 'used to crash'],
            'severity': 'high'
        },
        'bug/glitch': {
            'pattern': r'\b(bug(?:s|gy|ged)?|glitch(?:es|ed|ing|y)?|broken|break(?:s|ing)?|error(?:s)?|issue(?:s)?|problem(?:s)?|fault(?:y)?|defect(?:s)?|flaw(?:s)?)\b',
            'context_negatives': ['no bug', 'no issue', 'no problem', 'bug free', 'fixed'],
            'severity': 'medium'
        },
        'performance': {
            'pattern': r'\b(lag(?:s|gy|ging|ged)?|stutter(?:s|ing|ed)?|fps\s*(?:drop|issue)|frame(?:s)?\s*(?:drop|rate)|slow(?:s|ed|ing)?\s*down|choppy|janky|performance\s*(?:issue|problem))\b',
            'context_negatives': ['no lag', 'smooth', 'lag free', 'fixed lag'],
            'severity': 'medium'
        },
        'freeze/hang': {
            'pattern': r'\b(freeze(?:s|ing)?|frozen|hang(?:s|ing)?|hung|stuck|unresponsive|not\s*respond(?:ing)?)\b',
            'context_negatives': ['never freeze', 'no freeze', "doesn't freeze"],
            'severity': 'high'
        },
        'audio': {
            'pattern': r'\b(?:sound|audio|music|sfx|voice|volume)\s*(?:issue|problem|bug|glitch|not\s*work|broken|missing|gone|delay|cut(?:s|ting)?\s*out)\b',
            'context_negatives': ['sound great', 'audio perfect', 'love the sound'],
            'severity': 'low'
        },
        'save/progress': {
            'pattern': r'\b(?:save|progress|data|file)\s*(?:lost|gone|deleted|corrupt(?:ed)?|disappear(?:ed)?|wipe(?:d)?|reset|erase(?:d)?)\b',
            'context_negatives': ['save works', 'progress saved', 'data safe'],
            'severity': 'critical'
        },
        'controls': {
            'pattern': r'\b(?:control(?:s)?|button(?:s)?|touch|tap|swipe|input)\s*(?:bad|poor|terrible|awful|hard|difficult|unresponsive|delay(?:ed)?|lag(?:gy)?|issue|problem|suck|broken)\b',
            'context_negatives': ['controls are good', 'controls work', 'love controls'],
            'severity': 'medium'
        },
        'compatibility': {
            'pattern': r'\b(?:compatible|compatibility|doesn\'t\s*work|not\s*support(?:ed)?|can\'t\s*play|won\'t\s*(?:start|load|open|run))\b',
            'context_negatives': ['works great', 'runs well', 'compatible with'],
            'severity': 'high'
        },
        'battery': {
            'pattern': r'\b(?:battery|power)\s*(?:drain|consumption|hog|killer|issue|problem)\b',
            'context_negatives': ['battery efficient', 'low battery usage'],
            'severity': 'low'
        }
    }
    
    # Расширенные паттерны для запросов функций
    FEATURE_REQUESTS = {
        'multiplayer': {
            'pattern': r'\b(?:add|want|need|wish|hope|please|would\s*(?:be\s*)?(?:nice|great|awesome)|should\s*(?:have|add)|missing)\s*(?:for\s*)?(?:multiplayer|multi-player|co-?op|coop|pvp|online|friend(?:s)?|together)\b',
            'type': 'feature'
        },
        'save_system': {
            'pattern': r'\b(?:add|want|need|wish|hope)\s*(?:for\s*)?(?:checkpoint|save\s*(?:point|system)|cloud\s*save|cross-?save|sync)\b',
            'type': 'feature'
        },
        'content': {
            'pattern': r'\b(?:add|want|need|more)\s*(?:level|stage|character|weapon|item|content|dlc|expansion|mode|map)\b',
            'type': 'content'
        },
        'customization': {
            'pattern': r'\b(?:add|want|need|wish)\s*(?:for\s*)?(?:custom|setting|option|configuration|remap|rebind)\b',
            'type': 'settings'
        },
        'platform': {
            'pattern': r'\b(?:port|bring|release)\s*(?:to|on|for)\s*(?:pc|console|steam|switch|xbox|playstation|ps\d)\b',
            'type': 'platform'
        },
        'update': {
            'pattern': r'\b(?:update|patch|fix|waiting\s*for|need|want)\s*(?:the\s*)?(?:update|patch|fix|latest|new\s*version)\b',
            'type': 'update'
        }
    }
    
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обнаруживает проблемы и запросы в отзыве
        """
        content = review.content
        content_lower = content.lower().replace('.', '. ').replace('!', '! ')
        
        # Получаем или создаем doc
        if 'nlp_doc' in context:
            doc = context['nlp_doc']
        elif nlp:
            doc = nlp(content)
            context['nlp_doc'] = doc
        else:
            doc = None
        
        # Обнаруживаем проблемы
        issues = self._detect_issues(doc, content_lower)
        
        # Обновляем контекст
        context['issues'] = issues
        
        return context
    
    def _detect_issues(self, doc, content_lower: str) -> List[str]:
        """
        Интеллектуальная функция обнаружения проблем с расширенным набором паттернов
        """
        issues = []
        
        # Проверяем технические проблемы
        for problem_type, config in self.TECH_PROBLEMS.items():
            matches = list(re.finditer(config['pattern'], content_lower, re.IGNORECASE))
            for match in matches:
                if self._check_context(match, content_lower, config['context_negatives']):
                    severity = config.get('severity', 'medium')
                    issues.append(f"Problem: {problem_type} ({severity} severity)")
        
        # Проверяем запросы функций
        for request_type, config in self.FEATURE_REQUESTS.items():
            if re.search(config['pattern'], content_lower, re.IGNORECASE):
                issues.append(f"Request: {request_type} ({config['type']})")
        
        # Интеллектуальный анализ на основе синтаксиса
        if doc:
            negative_patterns = []
            request_patterns = []
            
            for sent in doc.sents:
                # Анализ негативных конструкций
                for token in sent:
                    # Проверяем негативные прилагательные с существительными
                    if token.pos_ == "ADJ" and token.dep_ in ["amod", "attr"]:
                        if token.lemma_ in ['bad', 'terrible', 'awful', 'horrible', 'poor', 'worst', 'annoying', 'frustrating']:
                            head = token.head
                            if head.pos_ == "NOUN":
                                negative_patterns.append(f"Problem: {token.text} {head.text}")
                    
                    # Проверяем модальные глаголы для запросов
                    if token.lemma_ in ['should', 'could', 'would', 'must', 'need']:
                        # Ищем глаголы действия после модальных
                        for child in token.children:
                            if child.pos_ == "VERB" and child.lemma_ in ['add', 'include', 'have', 'implement', 'support']:
                                obj = [c for c in child.children if c.dep_ == "dobj"]
                                if obj:
                                    request_patterns.append(f"Request: {child.lemma_} {obj[0].text}")
            
            # Добавляем уникальные паттерны
            issues.extend(list(set(negative_patterns)))
            issues.extend(list(set(request_patterns)))
        
        return issues if issues else ["No specific issue or request detected"]
    
    def _check_context(self, match, content: str, negatives: List[str]) -> bool:
        """
        Проверяет контекст вокруг найденного совпадения
        """
        start = max(0, match.start() - 30)
        end = min(len(content), match.end() + 30)
        context = content[start:end].lower()
        
        for neg in negatives:
            if neg in context:
                return False
        return True