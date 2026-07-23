# Decisions log — one line each: what + why. Append only.

- 2026-07-22 ShazamKit custom catalog over Olaf: on-device matching, zero porting risk, signatures generated on Mac.
- 2026-07-22 Phone = brain, pendant = smart mic: nothing pendant-sized runs Gemma E2B (needs ~2 GB RAM).
- 2026-07-22 Fingerprint before Gemma in the ladder: a 2B model cannot memorize exact track identity; Gemma is the permanent brain (transitions, moments, recap, ID card), not the lookup.
- 2026-07-22 Double tap = pin, long press = privacy. Highlights are automatic (crowd volume), no dedicated gesture.
- 2026-07-22 Deep-sleep listening management -> roadmap, not hackathon scope.
- 2026-07-22 NVIDIA challenge = conditional stretch goal only (vLLM night-batch variant), never before the core demo works.
- 2026-07-23 Heart-shaped case replaces the round puck: pulse-wave engraving = the product story worn on the chest; USB-C slot so it charges closed.
- 2026-07-23 Components stacked (LiPo flat, XIAO on top, USB at right wall), not side-by-side: smallest heart face (58 mm vs ~70 mm); XIAO header pins clipped flush, camera removed.
- 2026-07-23 Case v2 after design review: round implicit-curve heart (48.5 mm, roomier than the boxy construction) and the pulse as raised relief like the ref jewel — lid becomes a drop-in plate in a rim rebate so the relief prints flat without supports.
- 2026-07-23 Case v3: true 3D rounded heart (lofted, soft edges) split into two snap-fit shells at a mid-depth seam — no lid; fitted pocket, perimeter ridge/groove snap, Ø5.5 integrated bail hole; interactive viewer.html + four_views.png as design artifacts.
- 2026-07-23 Exact component modeling (XIAO Sense no-camera, LP502030 per datasheet) corrected the stack height 3.4 -> 7.5 mm (Sense board + empty cam socket): case deepened to 18.4 mm; wire bay sized for the folded JST, not the full lead length.
- 2026-07-23 Case v3.1: hollow interior by default (fitted pocket only after measuring real parts); mic hole cluster backed by an internal acoustic chamber because the exact mic XY is unverified; viewer gains flat shading (smooth faces) and a wiring/solder view showing the battery->BAT-pads connection.
- 2026-07-23 The pulse relief IS the pin button: capacitive electrode (copper tape) in a hollowed recess behind the relief (1.05 mm membrane), no mechanical switch — flexing/floating pulse rejected (no function without a switch, print scarring, PLA fatigue).
- 2026-07-23 FPC WiFi antenna placed under the front ceiling's upper band (front = away from the body which absorbs 2.4 GHz; >=5 mm from the touch copper; never on the LiPo pouch); U.FL clicked flat + hot-glue dab before casing.
