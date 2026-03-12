"""SEO Analyzers for different aspects of website audit."""

from .architecture import ArchitectureAnalyzer
from .content import ContentAnalyzer
from .technical import TechnicalAnalyzer
from .duplicates import DuplicateAnalyzer
from .structured_data import StructuredDataAnalyzer
from .page_classifier import PageClassifier, PageType, ClassificationReport
from .strategic_linking import StrategicLinkingAnalyzer, StrategicLinkingReport

__all__ = [
    'ArchitectureAnalyzer',
    'ContentAnalyzer',
    'TechnicalAnalyzer',
    'DuplicateAnalyzer',
    'StructuredDataAnalyzer',
    'PageClassifier',
    'PageType',
    'ClassificationReport',
    'StrategicLinkingAnalyzer',
    'StrategicLinkingReport',
]
