from app.analysis.metrics import AnalysisSnapshot
from app.coaching.coach import SafeMasteringCoach


def test_coach_flags_low_end_and_true_peak() -> None:
    coach = SafeMasteringCoach(true_peak_target_dbtp=-1.0)
    snapshot = AnalysisSnapshot(
        analyzed_seconds=30.0,
        sample_peak_dbfs=-0.3,
        true_peak_dbtp=-0.2,
        lufs_integrated=-7.5,
        lufs_short_term=-7.2,
        lufs_momentary=-7.0,
        stereo_width=0.95,
        correlation=0.02,
        mono_warning=True,
        clipping=False,
        sub_db=-10.0,
        bass_db=-12.0,
        low_mid_db=-25.0,
        mids_db=-20.0,
    )

    report = coach.generate(snapshot)
    joined = " ".join(report.do_now_actions).lower()
    assert "50-90 hz" in joined
    assert "lower master gain" in joined
    assert "mono" in joined
    assert report.score < 100
