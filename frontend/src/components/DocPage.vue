<template>
  <article class="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
    <!--
      长文档页壳：协议 / 隐私 / 管理条例 / 帮助中心共用。
      只负责标题、更新时间、正文排版与底部互链，内容全部由页面插槽提供，
      避免四份页面各自维护一套排版。

      注意：这段注释必须留在 <article> 内部。放在模板最外层会让组件根节点变成
      Fragment，从文档页切换路由时 <transition mode="out-in"> 拿不到稳定根元素，
      会永远停在离场占位态，页面渲染成空白。
    -->
    <p class="eyebrow">{{ eyebrow }}</p>
    <h1 class="mt-4 font-brand text-[clamp(2rem,3.4vw,3rem)] font-bold leading-[1.15] tracking-normal text-ink">{{ title }}</h1>
    <p class="mt-4 text-callout leading-relaxed text-ink-mid">{{ intro }}</p>
    <p class="mt-4 font-mono text-caption2 uppercase tracking-[0.16em] text-ink-dim">// 最后更新 · {{ updated }}</p>

    <div class="doc-prose mt-9">
      <slot />
    </div>

    <nav class="mt-14 border-t border-line/70 pt-6" aria-label="相关文档">
      <p class="font-mono text-caption2 uppercase tracking-[0.16em] text-ink-dim">// 相关文档</p>
      <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-footnote text-ink-mid">
        <router-link
          v-for="doc in docs"
          :key="doc.to"
          :to="doc.to"
          class="transition-colors hover:text-pine"
          :class="doc.to === route.path ? 'font-medium text-ink' : ''"
        >
          {{ doc.label }}
        </router-link>
      </div>
    </nav>
  </article>
</template>

<script setup>
import { useRoute } from 'vue-router'

defineProps({
  eyebrow: { type: String, required: true },
  title: { type: String, required: true },
  intro: { type: String, required: true },
  updated: { type: String, default: '2026 年 11 月 3 日' }
})

const route = useRoute()

const docs = [
  { label: '用户协议', to: '/terms' },
  { label: '隐私政策', to: '/privacy' },
  { label: '平台管理条例', to: '/community-rules' },
  { label: '帮助中心', to: '/help' }
]
</script>
