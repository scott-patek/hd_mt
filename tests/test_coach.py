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
        crest_factor_db=4.0,
        dynamic_range_db=5.0,
        dynamics_ready=True,
    )

    report = coach.generate(snapshot)
    joined = " ".join(report.do_now_actions).lower()
    assert "50-90 hz" in joined
    assert "lower master gain" in joined
    assert report.score < 100


def test_coach_flags_low_crest_for_edm_profiles() -> None:
    coach = SafeMasteringCoach(true_peak_target_dbtp=-1.0)
    snapshot = AnalysisSnapshot(
        analyzed_seconds=30.0,
        sample_peak_dbfs=-0.8,
        true_peak_dbtp=-1.2,
        lufs_integrated=-9.5,
        lufs_short_term=-9.1,
        lufs_momentary=-8.9,
        stereo_width=0.6,
        correlation=0.4,
        mono_warning=False,
        clipping=False,
        sub_db=-24.0,
        bass_db=-22.0,
        low_mid_db=-24.0,
        mids_db=-23.0,
        crest_factor_db=3.8,
        dynamic_range_db=8.5,
        dynamics_ready=True,
    )

    report = coach.generate(snapshot)
    assert any("crest factor" in issue.lower() for issue in report.top_issues)


def test_coach_flags_high_crest_for_edm_profiles() -> None:
    coach = SafeMasteringCoach(true_peak_target_dbtp=-1.0)
    snapshot = AnalysisSnapshot(
        analyzed_seconds=30.0,
        sample_peak_dbfs=-2.0,
        true_peak_dbtp=-2.1,
        lufs_integrated=-13.5,
        lufs_short_term=-13.0,
        lufs_momentary=-12.8,
        stereo_width=0.7,
        correlation=0.5,
        mono_warning=False,
        clipping=False,
        sub_db=-28.0,
        bass_db=-26.0,
        low_mid_db=-25.0,
        mids_db=-25.0,
        crest_factor_db=9.2,
        dynamic_range_db=16.5,
        dynamics_ready=True,
    )

    report = coach.generate(snapshot)
    assert any("crest factor" in issue.lower() for issue in report.top_issues)
