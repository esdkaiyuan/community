<template>
  <!-- 移动端：卡片顶部一条手绘品牌带，小屏也能看到「创意 / 互助 / 合作」 -->
  <div class="flex items-center justify-between gap-3 border-b border-dashed border-ink/15 px-5 py-4 md:hidden">
    <div class="flex min-w-0 items-center gap-3">
      <svg viewBox="0 0 40 40" class="h-9 w-9 shrink-0" fill="none" aria-hidden="true">
        <!-- 手画的便签框 -->
        <path
          d="M7 8 C 15 5, 30 5, 34 9 C 36 18, 35 30, 32 34 C 22 37, 12 36, 7 33 C 4 25, 4 15, 7 8 Z"
          class="text-ink/30"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linejoin="round"
        />
        <!-- 灯泡 = 创意 -->
        <circle cx="20" cy="16" r="5.5" class="text-ink" stroke="currentColor" stroke-width="1.5" />
        <path d="M18 21.5 L20 24 L22 21.5" class="text-ink" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
        <path
          d="M20 8 V6.5 M26 11 L27.5 9.5 M14 11 L12.5 9.5"
          class="text-pine"
          stroke="currentColor"
          stroke-width="1.3"
          stroke-linecap="round"
        />
        <!-- 两只手托住 = 互助 / 合作 -->
        <path
          d="M10 31 C 13 27, 17 27, 20 29 C 23 27, 27 27, 30 31"
          class="text-pine"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
        />
      </svg>
      <div class="min-w-0">
        <p class="font-brand text-callout font-semibold leading-tight text-ink">ESDKAIYUAN 共创社区</p>
        <p class="mt-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-pine">创意 · 互助 · 合作</p>
      </div>
    </div>
    <span class="hidden shrink-0 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-dim sm:inline">Co-Creation</span>
  </div>

  <aside class="auth-panel relative hidden flex-col justify-between overflow-hidden p-8 md:flex lg:p-10">
    <div class="relative z-10">
      <span class="auth-chip">ESDKAIYUAN · 共创社区</span>
      <h2 class="mt-6 font-brand text-[clamp(1.75rem,2.4vw,2.25rem)] font-semibold leading-[1.18] tracking-normal text-[#F6F1E5]">
        {{ title }}<br />
        <span class="auth-underline">{{ accent }}</span>
      </h2>
    </div>

    <!-- 手绘蓝图：一张草稿纸 + 三张便签，把「创意 → 互助 → 合作」画成一条线 -->
    <div class="relative z-10 my-5">
      <svg viewBox="0 0 440 252" class="mx-auto w-full max-w-[420px]" aria-hidden="true" fill="none">
        <!-- 草稿纸轮廓：两笔错开的线，像手画的 -->
        <path
          d="M28 20 C 140 14, 306 15, 410 23 C 417 88, 416 174, 405 230 C 294 237, 116 235, 22 227 C 15 154, 17 80, 28 20 Z"
          fill="rgba(246,241,229,0.03)"
          stroke="rgba(246,241,229,0.24)"
          stroke-width="1.4"
          stroke-linejoin="round"
        />
        <path d="M34 26 C 146 20, 306 21, 404 28" stroke="rgba(246,241,229,0.1)" stroke-width="1" />

        <!-- 胶带 -->
        <g transform="rotate(-8 68 18)">
          <rect x="36" y="10" width="62" height="15" fill="rgba(246,241,229,0.1)" stroke="rgba(246,241,229,0.2)" stroke-width="1" />
        </g>
        <g transform="rotate(6 380 232)">
          <rect x="348" y="224" width="62" height="15" fill="rgba(246,241,229,0.08)" stroke="rgba(246,241,229,0.16)" stroke-width="1" />
        </g>

        <!-- 便签 01：创意 -->
        <g transform="rotate(-5 113 100)">
          <path
            d="M52 58 C 84 54, 138 53, 169 55 C 173 85, 173 119, 172 143 C 137 147, 88 146, 54 146 C 50 116, 50 82, 52 58 Z"
            fill="rgba(91,224,235,0.05)"
            stroke="rgba(246,241,229,0.38)"
            stroke-width="1.3"
            stroke-linejoin="round"
          />
          <circle cx="104" cy="88" r="12" stroke="rgba(246,241,229,0.85)" stroke-width="1.6" />
          <path d="M99 98 L104 106 L109 98" stroke="rgba(246,241,229,0.85)" stroke-width="1.5" stroke-linejoin="round" />
          <path d="M100 87 L104 92 L108 83" stroke="#5BE0EB" stroke-width="1.4" stroke-linecap="round" />
          <path
            d="M104 68 V61 M118 74 L123 69 M90 74 L85 69 M121 90 H128 M87 90 H80"
            stroke="rgba(246,241,229,0.5)"
            stroke-width="1.2"
            stroke-linecap="round"
          />
          <text x="76" y="132" fill="rgba(246,241,229,0.7)" font-size="12" font-family="LXGW WenKai, KaiTi, serif">01 想法</text>
        </g>

        <!-- 便签 02：互助 -->
        <g transform="rotate(4 240 159)">
          <path
            d="M176 114 C 214 109, 270 108, 303 110 C 307 146, 307 178, 306 205 C 266 210, 218 210, 178 209 C 174 172, 174 140, 176 114 Z"
            fill="rgba(246,241,229,0.04)"
            stroke="rgba(246,241,229,0.38)"
            stroke-width="1.3"
            stroke-linejoin="round"
          />
          <!-- 三个小人，中间那个被两边拉着 -->
          <circle cx="208" cy="139" r="6" stroke="rgba(246,241,229,0.8)" stroke-width="1.5" />
          <path
            d="M208 145 V161 M208 150 L199 157 M208 150 L217 157 M208 161 L201 172 M208 161 L215 172"
            stroke="rgba(246,241,229,0.8)"
            stroke-width="1.5"
            stroke-linecap="round"
          />
          <circle cx="248" cy="136" r="6" stroke="rgba(246,241,229,0.8)" stroke-width="1.5" />
          <path
            d="M248 142 V158 M248 147 L239 154 M248 147 L257 154 M248 158 L241 169 M248 158 L255 169"
            stroke="rgba(246,241,229,0.8)"
            stroke-width="1.5"
            stroke-linecap="round"
          />
          <circle cx="228" cy="170" r="5" stroke="rgba(246,241,229,0.7)" stroke-width="1.4" />
          <path
            d="M228 175 V187 M228 179 L219 183 M228 179 L237 183 M228 187 L224 196 M228 187 L232 196"
            stroke="rgba(246,241,229,0.7)"
            stroke-width="1.4"
            stroke-linecap="round"
          />
          <!-- 搭在一起的手 -->
          <path d="M217 156 C 223 149, 241 147, 239 154" stroke="#5BE0EB" stroke-width="1.5" stroke-linecap="round" />
          <path d="M219 183 C 224 179, 232 179, 237 183" stroke="#5BE0EB" stroke-width="1.4" stroke-linecap="round" />
          <text x="298" y="202" text-anchor="end" fill="rgba(246,241,229,0.7)" font-size="12" font-family="LXGW WenKai, KaiTi, serif">02 同伴</text>
        </g>

        <!-- 便签 03：合作 -->
        <g transform="rotate(3 362 95)">
          <path
            d="M308 52 C 338 48, 386 47, 414 48 C 417 80, 417 114, 417 139 C 386 143, 340 143, 310 142 C 306 110, 306 76, 308 52 Z"
            fill="rgba(246,241,229,0.035)"
            stroke="rgba(246,241,229,0.38)"
            stroke-width="1.3"
            stroke-linejoin="round"
          />
          <path d="M332 96 L362 71 L392 96" stroke="rgba(246,241,229,0.85)" stroke-width="1.6" stroke-linejoin="round" />
          <path d="M336 96 V127 H388 V96" stroke="rgba(246,241,229,0.85)" stroke-width="1.5" stroke-linejoin="round" />
          <rect x="356" y="108" width="12" height="19" stroke="#5BE0EB" stroke-width="1.4" />
          <path d="M362 66 V58 L372 61 L362 64" stroke="#5BE0EB" stroke-width="1.4" stroke-linejoin="round" />
          <text x="406" y="136" text-anchor="end" fill="rgba(246,241,229,0.7)" font-size="11.5" font-family="LXGW WenKai, KaiTi, serif">03 一起建成</text>
        </g>

        <!-- 虚线箭头：想法 → 同伴 → 一起 -->
        <path d="M176 108 C 188 97, 178 118, 190 122" stroke="#5BE0EB" stroke-opacity="0.65" stroke-width="1.4" stroke-dasharray="5 6" stroke-linecap="round" />
        <path d="M190 122 L182 120 M190 122 L188 130" stroke="#5BE0EB" stroke-opacity="0.65" stroke-width="1.4" stroke-linecap="round" />
        <path d="M308 136 C 322 128, 302 110, 314 110" stroke="#5BE0EB" stroke-opacity="0.65" stroke-width="1.4" stroke-dasharray="5 6" stroke-linecap="round" />
        <path d="M314 110 L306 108 M314 110 L312 118" stroke="#5BE0EB" stroke-opacity="0.65" stroke-width="1.4" stroke-linecap="round" />

        <!-- 手绘圈选与星点 -->
        <path
          d="M162 92 C 198 66, 302 64, 336 100 C 364 130, 352 200, 296 212 C 238 224, 160 212, 152 174 C 147 148, 150 110, 162 92"
          stroke="rgba(91,224,235,0.16)"
          stroke-width="1.2"
          stroke-dasharray="2 8"
        />
        <path d="M166 46 V55 M161.5 50.5 H170.5" stroke="#5BE0EB" stroke-opacity="0.7" stroke-width="1.2" stroke-linecap="round" />
        <path d="M288 208 V216 M284 212 H292" stroke="rgba(246,241,229,0.4)" stroke-width="1.2" stroke-linecap="round" />
        <path d="M60 168 C 69 163, 75 173, 84 168 S 99 173, 108 168" stroke="rgba(246,241,229,0.18)" stroke-width="1.2" stroke-linecap="round" />
      </svg>
    </div>

    <div class="relative z-10">
      <!-- 创意 / 互助 / 合作三步，和插画同一条叙事线 -->
      <ol class="grid grid-cols-3 border-t border-dashed border-white/15 pt-4">
        <li v-for="step in STEPS" :key="step.index" class="auth-step">
          <p class="font-mono text-[10px] font-medium tracking-[0.12em] text-[#5BE0EB]/80">{{ step.index }}</p>
          <p class="mt-1 font-brand text-callout font-semibold text-[#F6F1E5]/90">{{ step.theme }}</p>
          <p class="mt-0.5 text-caption2 text-white/45">{{ step.desc }}</p>
        </li>
      </ol>

      <p class="mt-5 text-footnote leading-relaxed text-white/60">{{ quote }}</p>
      <p class="mt-3 font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">// draw together · build together</p>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  accent: { type: String, required: true },
  quote: { type: String, required: true }
})

const STEPS = [
  { index: '01', theme: '创意', desc: '画下第一笔' },
  { index: '02', theme: '互助', desc: '有人搭把手' },
  { index: '03', theme: '合作', desc: '一起把它建成' }
]
</script>
