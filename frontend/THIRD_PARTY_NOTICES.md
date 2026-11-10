# Rhine frontend attribution

Source: https://github.com/tmc5csxr9m-cpu/rhine-lock

Upstream revision: a4df68c6bd9e01ecb7660659becf495957e57faa.
License: AGPL-3.0-or-later. Full license: public/assets/licenses/rhine-lock-AGPL-3.0.txt.

Adapted on 2026-11-08 for PersonalRAG: Stage.ts and shaders.ts (Three.js scene),
the fan-drawn infinity mark, locally hosted scene textures, and the personnel-file
visual treatment. Stage asset URLs, playback lifecycle and frame clock were changed. Vue UI,
HTTP authentication integration, responsive workspace and fallback were adapted
for this project. Upstream Rust/PAM/session-lock code is not included.
Upstream transition.ts SnapCard geometry, App.svelte boot/exit cue equations,
the BootOverlay treatment and AuthRing construction are adapted in motionMath.js,
useRhineMotion.js, RhineBoot.vue and RhineReticle.vue. A retained live Vue archive
viewport takes the place of the operating-system screenshot. The login/GPU scene
stays mounted through the original 1230ms handoff. No OS capture is performed.
DecodeText's progressive glyph treatment, WarningOverlay's staged rows and
projected scene leader-line treatment were adapted into RhineDecodeText.vue,
decodeText.js, RhineReticle.vue and RhineCallouts.vue. Compact layouts, DOM-based
card origins, viewport-change handoff and fallback warning anchors are project
adaptations; OS-only controls and claims are not reproduced.

The derived frontend is provided under AGPL-3.0-or-later. Preserve this notice,
the license, corresponding source and change notices when distributing it.
When serving a modified version over a network, offer its corresponding source
to users as required by the license. This local change does not publish the app.

Montserrat and JetBrains Mono fonts retain their bundled SIL Open Font License
notices in public/assets/rhine/fonts/OFL-*.txt.

Fan work, not affiliated with or endorsed by Hypergryph. Arknights and Rhine Lab
are trademarks of Hypergryph; the infinity mark is a fan redrawing.

## Workspace design guidance and UI primitives

Workspace layout and overlay decisions were adapted on 2026-11-08 from
Ludi-Herry/b-end-design-system-skill, revision
f56256e0a7432bd2d60d317eb33048f2c09df296 (MIT, Copyright 2026 Ludi).
Source: https://github.com/Ludi-Herry/b-end-design-system-skill .
Its React templates were not imported; the implementation remains Vue.
License copy: public/assets/licenses/ludi-design-MIT.txt.

Reka UI 2.11.0 provides dialog/focus/portal primitives (MIT, UnoVue).
Lucide Vue Next 0.577.0 provides workspace icons (ISC, Lucide Contributors,
with Feather MIT portions). Bundled notices are retained in
public/assets/licenses/reka-ui-MIT.txt and lucide-ISC.txt.


## Naive UI

Main library workspace controls use Naive UI 2.45.3 (MIT).
Source: https://github.com/tusen-ai/naive-ui
License: public/assets/licenses/naive-ui-MIT.txt.

