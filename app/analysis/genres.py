"""
Genre-specific mastering target curves and coaching profiles.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class GenreProfile:
    """A mastering target profile for a specific music genre."""
    name: str
    description: str
    anchor_hz: np.ndarray
    anchor_db: np.ndarray
    low_end_threshold_db: float = 5.0
    low_mid_boost_suggestion: float = 1.0
    true_peak_target_dbtp: float = -1.0


# Frequency anchor points (consistent across genres)
_ANCHOR_HZ = np.array([
    20.0,
    35.0,
    50.0,
    60.0,
    80.0,
    100.0,
    150.0,
    250.0,
    400.0,
    800.0,
    1500.0,
    3000.0,
    5000.0,
    8000.0,
    12000.0,
    16000.0,
    20000.0,
], dtype=np.float32)


def _make_genre(name: str, description: str, anchor_db: list[float], **kwargs) -> GenreProfile:
    """Helper to create genre profiles."""
    return GenreProfile(
        name=name,
        description=description,
        anchor_hz=_ANCHOR_HZ.copy(),
        anchor_db=np.array(anchor_db, dtype=np.float32),
        **kwargs
    )


# House Music (classic house with emphasis on kick/bass and smooth highs)
HOUSE = _make_genre(
    name="House",
    description="Classic house: punchy kick, warm mids, smooth highs",
    anchor_db=[
        -24.0,  # 20 Hz
        -14.0,  # 35 Hz
        -7.0,   # 50 Hz
        -4.0,   # 60 Hz
        -6.0,   # 80 Hz
        -10.0,  # 100 Hz
        -15.0,  # 150 Hz
        -20.0,  # 250 Hz
        -24.0,  # 400 Hz
        -27.0,  # 800 Hz
        -29.0,  # 1500 Hz
        -27.0,  # 3000 Hz
        -24.0,  # 5000 Hz
        -22.0,  # 8000 Hz
        -24.0,  # 12000 Hz
        -27.0,  # 16000 Hz
        -32.0,  # 20000 Hz
    ]
)

# Deep House (warmer, deeper bass, less bright highs)
DEEP_HOUSE = _make_genre(
    name="Deep House",
    description="Deep house: warm bass, soulful mids, subdued highs",
    anchor_db=[
        -18.0,  # 20 Hz (lift up the deep sub)
        -12.0,  # 35 Hz
        -6.0,   # 50 Hz
        -3.0,   # 60 Hz
        -5.0,   # 80 Hz
        -8.0,   # 100 Hz
        -14.0,  # 150 Hz
        -18.0,  # 250 Hz
        -22.0,  # 400 Hz
        -25.0,  # 800 Hz
        -28.0,  # 1500 Hz
        -28.0,  # 3000 Hz
        -26.0,  # 5000 Hz
        -25.0,  # 8000 Hz
        -28.0,  # 12000 Hz
        -30.0,  # 16000 Hz
        -35.0,  # 20000 Hz (darker highs)
    ],
    low_end_threshold_db=6.0,  # More forgiving with low-end emphasis
)

# Progressive House (detailed, open, balanced)
PROGRESSIVE_HOUSE = _make_genre(
    name="Progressive House",
    description="Progressive house: open soundscape, detailed mids, extended highs",
    anchor_db=[
        -22.0,  # 20 Hz
        -13.0,  # 35 Hz
        -6.0,   # 50 Hz
        -3.0,   # 60 Hz
        -5.0,   # 80 Hz
        -9.0,   # 100 Hz
        -14.0,  # 150 Hz
        -18.0,  # 250 Hz
        -22.0,  # 400 Hz
        -25.0,  # 800 Hz
        -26.0,  # 1500 Hz
        -24.0,  # 3000 Hz
        -21.0,  # 5000 Hz
        -19.0,  # 8000 Hz
        -20.0,  # 12000 Hz
        -22.0,  # 16000 Hz
        -28.0,  # 20000 Hz
    ]
)

# Tech House (tight kick, aggressive highs, less low-end boost)
TECH_HOUSE = _make_genre(
    name="Tech House",
    description="Tech house: punchy kick, aggressive highs, less bass bloom",
    anchor_db=[
        -26.0,  # 20 Hz (tighter low-end)
        -16.0,  # 35 Hz
        -8.0,   # 50 Hz
        -5.0,   # 60 Hz
        -7.0,   # 80 Hz
        -11.0,  # 100 Hz
        -16.0,  # 150 Hz
        -21.0,  # 250 Hz
        -25.0,  # 400 Hz
        -26.0,  # 800 Hz
        -25.0,  # 1500 Hz
        -22.0,  # 3000 Hz
        -19.0,  # 5000 Hz
        -16.0,  # 8000 Hz
        -17.0,  # 12000 Hz
        -20.0,  # 16000 Hz
        -26.0,  # 20000 Hz
    ],
    low_end_threshold_db=4.0,  # Less tolerant of low-end boost
)

# Minimal (tight, clean, minimal bass)
MINIMAL = _make_genre(
    name="Minimal",
    description="Minimal: tight bass, clean mids, controlled highs",
    anchor_db=[
        -28.0,  # 20 Hz (minimize sub)
        -18.0,  # 35 Hz
        -10.0,  # 50 Hz
        -7.0,   # 60 Hz
        -8.0,   # 80 Hz
        -12.0,  # 100 Hz
        -17.0,  # 150 Hz
        -22.0,  # 250 Hz
        -26.0,  # 400 Hz
        -27.0,  # 800 Hz
        -26.0,  # 1500 Hz
        -23.0,  # 3000 Hz
        -20.0,  # 5000 Hz
        -18.0,  # 8000 Hz
        -19.0,  # 12000 Hz
        -22.0,  # 16000 Hz
        -28.0,  # 20000 Hz
    ],
    low_end_threshold_db=3.0,  # Strict low-end control
)

# Techno (aggressive, energetic, strong presence)
TECHNO = _make_genre(
    name="Techno",
    description="Techno: aggressive kick, energetic mids, bright highs",
    anchor_db=[
        -25.0,  # 20 Hz
        -15.0,  # 35 Hz
        -7.0,   # 50 Hz
        -4.0,   # 60 Hz
        -6.0,   # 80 Hz
        -10.0,  # 100 Hz
        -15.0,  # 150 Hz
        -19.0,  # 250 Hz
        -23.0,  # 400 Hz
        -26.0,  # 800 Hz
        -24.0,  # 1500 Hz
        -21.0,  # 3000 Hz
        -18.0,  # 5000 Hz
        -15.0,  # 8000 Hz
        -16.0,  # 12000 Hz
        -19.0,  # 16000 Hz
        -24.0,  # 20000 Hz
    ],
    low_end_threshold_db=5.5,
)


# Registry of all available genres
GENRES = {
    "house": HOUSE,
    "deep_house": DEEP_HOUSE,
    "progressive_house": PROGRESSIVE_HOUSE,
    "tech_house": TECH_HOUSE,
    "minimal": MINIMAL,
    "techno": TECHNO,
}


def get_genre(genre_key: str) -> GenreProfile:
    """Get a genre profile by key (case-insensitive)."""
    return GENRES.get(genre_key.lower(), HOUSE)


def list_genres() -> list[tuple[str, str]]:
    """Return list of (key, name) tuples for all genres."""
    return [(key, profile.name) for key, profile in GENRES.items()]
