"""Explicit overrides, deterministic IP defaults and a small theme registry."""
import re

from jade_paper import JadePaperUI
from mystery import MysteryUI

THEMES = {'jade-paper': JadePaperUI, 'mystery': MysteryUI}


def resolve_theme(data):
    requested = data.get('ui_theme', 'auto')
    if not isinstance(requested, str) or requested not in ('auto', *THEMES):
        raise ValueError('ui_theme must be auto, jade-paper or mystery')
    if requested != 'auto':
        return requested
    ip = data.get('ip', '').casefold()
    if re.search(r'柯南|福尔摩斯|侦探|推理|悬疑|\b(conan|case closed|sherlock|detective|mystery)\b', ip):
        return 'mystery'
    return 'jade-paper'
