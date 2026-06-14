You are an expert audio software engineer and mastering assistant.

Build a Python desktop app (with Makefile) that helps me master tracks despite reduced low-frequency hearing. I tend to over-boost bass, so prioritize objective visual feedback and simple, actionable EQ and gain guidance.

Model target: Open LLM Gemma4:12B-mlx.

Tech stack (default)
- Python 3.11+
- PySide6 (UI)
- PyQtGraph (real-time plots)
- NumPy + SciPy (FFT/signal analysis)
- soundfile + sounddevice (decode/playback)
- ffmpeg-python or PyAV (extract audio from video)
- Optional fallback: pydub + ffmpeg for MP3 edge cases

Core product requirements
1. Input and playback
- File picker in UI (no typed paths required).
- Support audio files: at least MP3, WAV.
- Support video files: at least MP4, MOV.
- For video, analyze audio track only.
- Playback controls: Play, Pause, Stop, Seek.
- Show current time and duration.

2. Real-time analysis
- Spectrum analyzer: Three separate graphs for better frequency range detail
  - Low spectrum: 20-300 Hz (bass range, 10 Hz grouping)
  - Mid spectrum: 300-4000 Hz (vocal/instrument range, 50 Hz grouping)
  - High spectrum: 4000-20000 Hz (air/brilliance range, 500 Hz grouping)
  - When a display bucket is narrower than the FFT bin spacing, interpolate the bucket value instead of showing an empty bar.
  - Each graph can show a toggled dashed static target curve for digital House music, indicating where peaks should generally sit by frequency band.
- Each spectrum shows calibrated dBFS magnitude with independent scale
- Bars above 0 dBFS are colored red for immediate over detection
- Peak-hold toggle per band
- 0 dBFS line + clipping indicators

3. Mastering meters and safety
- LUFS: integrated, short-term, momentary.
- Peaks: sample peak and true peak (dBTP).
- Default safety target: true peak <= -1.0 dBTP (user-adjustable).
- Stereo width/correlation meter + mono-compatibility warning.
- Low-end diagnostic bands:
  - Sub: 20-60 Hz
  - Bass: 60-120 Hz
  - Low-mid: 120-350 Hz
- Warn if sub/bass is too strong relative to mids.

4. Coaching and Analyze button
- Continuous lightweight coaching during playback (for example every 5-10s).
- Include an Analyze button that reports what has been heard so far.
- Analyze report must include:
  - Top 3-5 issues
  - EQ actions with exact frequency/range and dB amount
  - Gain/headroom actions (clipping risk + recommended trim)
  - Confidence note if not enough audio analyzed yet
- Include a persistent Safe Mastering Suggestions panel with:
  - Do this now (1-3 actions)
  - Why (one short sentence)
  - Amount (exact dB/range)

5. Reference and progress tracking
- Optional reference-track loading.
- Auto level-match current track vs reference before A/B comparison.
- A/B compare controls.
- Keep per-file analysis history and show trend (improving/worsening) across Analyze runs.

6. Accessibility and advice style
- Do not rely on hearing alone; prioritize visual meters and numeric readouts.
- Use plain language with direct commands, minimal jargon.
- Every recommendation format:
  - Action + Area + Amount + short Reason
- Example style:
  - "Reduce 50-80 Hz by 1.5 dB. Bass is dominating the mix."
  - "Lower master gain by 1 dB. Peaks are too close to clipping."
  - "Increase 300 Hz by 1 dB. Low-mids feel slightly thin."

7. UI direction
- Modern tactical vibe, restrained (not flashy).
- Dark-neutral base, high-contrast accents.
- Clear panel hierarchy, readable labels, subtle grids, minimal motion.
- Prioritize readability of meters/warnings over decoration.
- Works well on common Mac resolutions and when resized.

8. Engineering constraints
- Target macOS first.
- Clean module structure (for example app/ui, app/audio, app/analysis, app/coaching).
- Include robust handling for corrupt/unsupported files.
- Keep latency low for smooth real-time visuals.
- For video inputs, clean up temporary extracted audio artifacts.

9. Delivery format (important for Gemma4:12B-mlx)
- Keep responses compact and structured.
- Do not include long theory unless asked.
- Output code responses in this order:
  1) Project tree
  2) Full file contents
  3) Run commands
  4) Quick verification checklist
- If uncertain, choose the simplest robust default and state one short assumption.

10. Run experience
- Provide requirements and Makefile targets:
  - make venv
  - make install
  - make run
  - make test
- On macOS, if ffmpeg is missing, print clear install guidance:
  - brew install ffmpeg

If defaults are needed, prioritize reliability, deterministic behavior, low latency, and clear visuals.

11. Implementation updates (2026-06-12)
- Spectrum analyzer display corrected so bars rise upward from a floor baseline (not upside down).
- Spectrum frequency view tightened to human hearing with wiggle room: ~15 Hz to ~22 kHz (bounded by sample rate/Nyquist).
- Spectrum magnitude window tightened for visibility so peaks are easier to see during playback.

12. Implementation updates (2026-06-12, pass 2)
- Spectrum X-axis tightened further to practical hearing focus: ~25 Hz to ~18 kHz (bounded by sample rate/Nyquist).
- Peak history now holds for 3 seconds and renders as a yellow line overlay when Peak Hold is enabled.
- Spectrum groups narrowed by increasing band resolution so adjacent frequency buckets are less wide.

13. Implementation updates (2026-06-12, pass 3)
- Spectrum X-axis now focuses on 40 Hz to 5 kHz (bounded by sample rate/Nyquist) for clearer actionable view.
- Spectrum bottom-axis labels now show explicit Hertz/kHz tick labels (for example 40 Hz through 5 kHz).
- Peak history visualization now draws yellow horizontal caps over each frequency-group bar top.

14. Implementation updates (2026-06-12, pass 4)
- Spectrum analyzer switched to linear frequency mode with 40 Hz at the left edge and 10 kHz at the right edge (bounded by sample rate/Nyquist).
- Frequency groups are now fixed 100 Hz bins with equal-width bars.
- Spectrum X-axis labels are set every 100 Hz to match the bar group boundaries.

15. Implementation updates (2026-06-12, pass 5)
- Spectrum bins remain fixed at 100 Hz width.
- Spectrum X-axis label cadence changed to every 200 Hz for readability, with 40 Hz anchored at the left edge.

16. Implementation updates (2026-06-12, pass 6)
- Spectrum X-axis now starts at 0 Hz and extends to 10 kHz (bounded by sample rate/Nyquist).
- Spectrum label readability improved: major labeled ticks every 1000 Hz with unlabeled minor ticks every 200 Hz.
- Spectrum band values now use per-band RMS energy (instead of max-bin spikes) for more stable and credible high-frequency behavior.

17. Implementation updates (2026-06-12, pass 7)
- Spectrum analyzer now removes DC bias before FFT to prevent false 0 Hz energy spikes.
- Sub-audible content below 20 Hz is suppressed in band calculations for more believable readout in the first (0-100 Hz) group.

18. Implementation updates (2026-06-12, pass 8)
- Spectrum analysis/display now only covers human hearing range: 20 Hz to 20 kHz (Nyquist-limited by sample rate).
- Spectrum plot switched to log-frequency view with denser human-range tick marks for improved readability.
- Frequency grouping switched to log-spaced bands to match perceptual spacing across human hearing.

19. Implementation updates (2026-06-12, pass 9)
- Spectrum plot switched back to linear frequency view (20 Hz to 20 kHz) so bars utilize the full chart width.
- Frequency groups now use fixed 100 Hz bins with uniform bar widths across the spectrum.
- X-axis tick labeling simplified for readability (major every 1 kHz, minor markers every 500 Hz).

20. Implementation updates (2026-06-12, pass 10)
- Loading a new main track/video now fully resets analysis state, report/suggestions text, meters, warnings, and spectrum/spectrogram visuals so analysis always starts over cleanly.
- Spectrum X-axis ticks are now intentionally denser and non-uniform in 40-2000 Hz for better low-mid readability where most mastering decisions occur.

21. Implementation updates (2026-06-12, pass 11)
- Spectrum X-axis now uses a focus-scaled mapping so 40-2000 Hz occupies most plot width while 2k-20k remains visible in compressed form.
- Tick labels are intentionally "faked" to remain interpretable: dense in the focused low-mid range, sparser in upper frequencies.
- Bar and peak-cap positions are mapped with the same transform so visual alignment remains accurate.

22. Implementation updates (2026-06-12, pass 12)
- Focus scaling adjusted further for human readability: most width is now dedicated to roughly 20-4k Hz, with highs compressed into context view.
- Spectrum bins are now variable-width by region: finer in low-mid, coarser in highs to reduce visual clutter while preserving trend visibility.
- Axis labels simplified to key frequencies only, and a live hover readout now shows approximate Hz and dB for the nearest bar.

