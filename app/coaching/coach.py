from __future__ import annotations

from dataclasses import dataclass
from app.analysis.genres import GenreProfile, HOUSE
from app.analysis.metrics import AnalysisSnapshot


@dataclass
class CoachingReport:
    top_issues: list[str]
    do_now_actions: list[str]
    confidence_note: str
    score: float


class SafeMasteringCoach:
    def __init__(self, true_peak_target_dbtp: float = -1.0, genre: GenreProfile | None = None) -> None:
        self.true_peak_target_dbtp = true_peak_target_dbtp
        self.genre = genre or HOUSE

    def set_true_peak_target(self, value: float) -> None:
        self.true_peak_target_dbtp = value

    def set_genre(self, genre: GenreProfile) -> None:
        """Update the genre profile for coaching."""
        self.genre = genre

    def generate(
        self,
        snapshot: AnalysisSnapshot,
        low_end_curve_delta_db: float | None = None,
    ) -> CoachingReport:
        issues: list[str] = []
        actions: list[str] = []
        score = 100.0

        # Only warn about bass dominance if:
        # (1) Bass is significantly elevated relative to mids (more than threshold)
        # AND (2) Bass band has actual content (above -20 dB, not noise floor)
        low_end_over_mid = max(snapshot.sub_db, snapshot.bass_db) - snapshot.mids_db
        bass_absolute_level = max(snapshot.sub_db, snapshot.bass_db)
        
        curve_excess_gate = (
            low_end_curve_delta_db is None or low_end_curve_delta_db > 0.8
        )
        if (
            low_end_over_mid > self.genre.low_end_threshold_db
            and bass_absolute_level > -20.0
            and curve_excess_gate
        ):
            amount = min(3.0, round((low_end_over_mid - (self.genre.low_end_threshold_db - 1.0)) * 0.35, 1))
            issues.append("Low-end dominance is masking mid detail.")
            actions.append(
                f"Reduce 50-90 Hz by {amount:.1f} dB. Bass is dominating the mix."
            )
            score -= 18.0

        if snapshot.low_mid_db < snapshot.mids_db - 5.0:
            issues.append("Low-mids are thin relative to the midrange.")
            actions.append("Increase 180-320 Hz by 1.0 dB. Low-mid support is slightly thin.")
            score -= 10.0

        if snapshot.true_peak_dbtp > self.true_peak_target_dbtp:
            trim = round(snapshot.true_peak_dbtp - self.true_peak_target_dbtp + 0.2, 1)
            issues.append("True peak is above the safety ceiling.")
            actions.append(
                f"Lower master gain by {trim:.1f} dB. Peaks are too close to clipping."
            )
            score -= 22.0

        if snapshot.clipping:
            issues.append("Clipping indicators are active.")
            actions.append("Lower output by 1.0 dB now. Clipping risk is immediate.")
            score -= 25.0

        if snapshot.correlation < 0.05:
            issues.append("Stereo correlation is weak for mono playback.")
            actions.append("Narrow side content by 5-10%. Mono compatibility is at risk.")
            score -= 12.0

        if snapshot.lufs_integrated > -8.0:
            issues.append("Program loudness is very high for mastering headroom.")
            actions.append("Lower master gain by 0.8 dB. Add headroom for safer limiting.")
            score -= 8.0

        crest_low, crest_high = self._crest_band_for_genre()
        if snapshot.crest_factor_db < crest_low:
            issues.append("Crest factor is low for this genre target.")
            actions.append(
                f"Ease limiting or compression to keep crest factor near {crest_low:.1f}-{crest_high:.1f} dB."
            )
            score -= 10.0
        elif snapshot.crest_factor_db > crest_high:
            issues.append("Crest factor is high for this genre target.")
            actions.append(
                f"Add gentle bus control to keep crest factor near {crest_low:.1f}-{crest_high:.1f} dB."
            )
            score -= 7.0

        if snapshot.dynamics_ready and snapshot.dynamic_range_db < 6.0:
            issues.append("Dynamic range is very low and may sound over-compressed.")
            actions.append("Back off limiter drive or reduce compression depth to restore movement.")
            score -= 10.0

        if not issues:
            issues.append("No major risks detected in the analyzed audio.")
            actions.append("Hold settings. Your current balance is within safe targets.")

        confidence = (
            "Low confidence: analyze at least 20 seconds for stable guidance."
            if snapshot.analyzed_seconds < 20.0
            else "High confidence: enough material analyzed for stable guidance."
        )

        return CoachingReport(
            top_issues=issues[:5],
            do_now_actions=actions[:3],
            confidence_note=confidence,
            score=max(0.0, score),
        )

    def _crest_band_for_genre(self) -> tuple[float, float]:
        name = self.genre.name.lower()
        if "jazz" in name or "classical" in name:
            return 14.0, 20.0
        if "rock" in name or "pop" in name:
            return 8.0, 11.0
        if (
            "edm" in name
            or "dubstep" in name
            or "house" in name
            or "techno" in name
            or "trance" in name
            or "minimal" in name
        ):
            return 5.0, 7.0
        return 8.0, 12.0
