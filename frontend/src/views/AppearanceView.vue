<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <div>
      <p class="eyebrow">Appearance</p>
      <h1 class="mt-3 font-brand text-[clamp(2rem,3vw,2.8rem)] font-bold tracking-normal text-ink">外观</h1>
      <p class="mt-2 text-footnote text-ink-mid">
        选择明暗模式与主题色。设置只保存在这台设备的浏览器里，随时可以改回来。
      </p>
    </div>

    <!-- ===================== 01 明暗模式 ===================== -->
    <section class="hig-card mt-8 p-5 sm:p-6" data-test="theme-mode-section">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="mono-label">01 / 明暗模式</p>
          <p class="mt-1 text-footnote text-ink-mid">跟随系统时会实时响应系统的浅色与深色外观。</p>
        </div>
        <span class="chip shrink-0" data-test="theme-mode-badge">{{ modeLabel }}</span>
      </div>

      <AppSegmented
        v-model="modeProxy"
        :options="modeOptions"
        aria-label="明暗模式"
        class="mt-4"
      />

      <p class="mt-3 text-caption1 text-ink-dim" data-test="theme-resolved">
        当前渲染为
        <span class="font-medium text-ink-mid">{{ resolvedLabel }}</span>
        {{ mode === 'system' ? '· 由系统决定' : '· 手动选择' }}
      </p>
    </section>

    <!-- ===================== 02 主题色 ===================== -->
    <section class="hig-card mt-5 p-5 sm:p-6" data-test="theme-accent-section">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="mono-label">02 / 主题色</p>
          <p class="mt-1 text-footnote text-ink-mid">主题色驱动按钮、链接、标签与徽标；点赞、警告等语义色保持不变。</p>
        </div>
        <span class="chip shrink-0" data-test="theme-accent-badge">{{ accentOption.label }}</span>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-2.5">
        <button
          v-for="option in THEME_ACCENTS"
          :key="option.value"
          type="button"
          class="accent-option"
          :class="{ 'is-active': accent === option.value }"
          :style="{ '--accent-sample': resolved === 'dark' ? option.dark : option.color }"
          :aria-pressed="accent === option.value"
          :data-accent="option.value"
          data-test="accent-option"
          @click="setAccent(option.value)"
        >
          <span class="accent-option__swatch" aria-hidden="true"></span>
          <span class="min-w-0 flex-1 text-left">
            <span class="block text-footnote font-medium text-ink">{{ option.label }}</span>
            <!-- 窄屏每个卡片只有约 150px，说明文字会把标签挤成两行，直接在 sm 以下收起 -->
            <span class="mt-0.5 hidden text-caption1 text-ink-dim sm:block">{{ option.hint }}</span>
          </span>
          <span v-if="accent === option.value" class="accent-option__check" aria-hidden="true">
            <AppIcon name="check" class="h-3.5 w-3.5" />
          </span>
        </button>
      </div>
    </section>

    <!-- ===================== 实时预览 ===================== -->
    <section class="hig-card mt-5 overflow-hidden" data-test="theme-preview">
      <div class="flex items-center justify-between gap-3 border-b border-line/60 px-5 py-3">
        <p class="mono-label">实时预览</p>
        <p class="font-mono text-caption2 uppercase tracking-[0.12em] text-pine" data-test="theme-preview-accent">
          {{ accentOption.label }} / {{ resolvedLabel }}
        </p>
      </div>

      <div class="p-5 sm:p-6">
        <p class="eyebrow">Preview</p>
        <h2 class="mt-3 font-brand text-[clamp(1.4rem,2vw,1.9rem)] font-bold leading-tight text-ink">
          让每一个好创意都能找到同行者
        </h2>
        <p class="mt-2 max-w-md text-footnote leading-relaxed text-ink-mid">
          发布项目、参与共创，把想法变成现实。下面这些控件会跟着主题色走。
        </p>

        <div class="mt-4 flex flex-wrap items-center gap-2.5">
          <router-link to="/publish" class="btn-primary text-footnote">发布项目</router-link>
          <router-link to="/" class="btn-secondary text-footnote">逛逛广场</router-link>
          <span class="chip-link">标签</span>
          <router-link to="/help" class="inline-flex items-center gap-1 text-footnote font-medium text-pine hover:underline">
            帮助中心
          </router-link>
        </div>

        <div class="mt-5 flex flex-col gap-1.5 border-t border-line/60 pt-4 text-caption1 text-ink-dim sm:flex-row sm:items-center sm:gap-x-5">
          <span class="inline-flex items-center gap-1.5">
            <AppIcon name="heart" class="h-4 w-4 shrink-0 text-clay" />
            点赞与警告保持语义色，不随主题色变化
          </span>
          <span class="inline-flex items-center gap-1.5">
            <AppIcon name="check-circle" class="h-4 w-4 shrink-0 text-green" />
            成功状态同理
          </span>
        </div>
      </div>
    </section>

    <div class="mt-6 flex flex-wrap items-center justify-between gap-3">
      <button type="button" class="btn-secondary text-footnote" data-test="theme-reset" @click="resetTheme">
        <AppIcon name="history" class="h-4 w-4" />
        恢复默认（电光青 · 跟随系统）
      </button>
      <p class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">// 仅存储在本机浏览器</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import AppSegmented from '@/components/AppSegmented.vue'
import { THEME_ACCENTS, THEME_MODES, useTheme } from '@/composables/useTheme'

const { mode, accent, resolved, resolvedLabel, modeLabel, accentOption, setMode, setAccent, resetTheme } = useTheme()

const modeOptions = THEME_MODES.map((item) => ({
  value: item.value,
  label: item.label,
  icon: item.icon,
  test: `theme-mode-${item.value}`
}))

// AppSegmented 用 v-model 写回，这里把 setter 接到 setMode（带白名单校验与持久化）
const modeProxy = computed({
  get: () => mode.value,
  set: (value) => setMode(value)
})
</script>

<style scoped>
.accent-option {
  @apply flex min-h-11 items-center gap-2.5 rounded-14 bg-sand/50 px-3 py-2.5 text-left transition-all;
  border: 1.5px solid rgb(var(--c-ink) / 0.12);
}
.accent-option:hover {
  border-color: rgb(var(--c-ink) / 0.28);
  background: rgb(var(--c-sand) / 0.8);
}
.accent-option.is-active {
  border-color: var(--accent-sample);
  background: rgb(var(--c-cream));
  box-shadow: 2px 2px 0 color-mix(in srgb, var(--accent-sample) 24%, transparent);
}
.accent-option__swatch {
  @apply h-7 w-7 shrink-0 rounded-full;
  background: var(--accent-sample);
  border: 1px solid rgb(var(--c-ink) / 0.12);
  box-shadow: inset 0 0 0 3px rgb(var(--c-cream));
}
.accent-option__check {
  @apply flex h-5 w-5 shrink-0 items-center justify-center rounded-full;
  color: var(--accent-sample);
  border: 1px solid var(--accent-sample);
}
</style>
