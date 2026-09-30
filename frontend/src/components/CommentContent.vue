<template>
  <!-- 评论正文渲染：纯文本插值（无 v-html，XSS 面 = 0）。
       @ 用户名高亮只认 mentionNames（后端 listComments 顶层字段 = 整库识别口径），
       不会把任何 @token 都点亮 -->
  <span class="comment-content">
    <template v-for="(part, i) in parts" :key="i">
      <span
        v-if="part.mentioned"
        class="rounded bg-pine-soft px-0.5 font-medium text-pine-deep"
        data-test="mention"
      >{{ part.text }}</span>
      <template v-else>{{ part.text }}</template>
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  content: { type: String, default: '' },
  // 后端 listComments 返回的本页真实存在的 @ 用户名
  mentionNames: { type: Array, default: () => [] }
})

// 与后端 extractMentionNames 同口径：@ 到空白或常见标点为止，2-20 字符。
// 两端口径漂移时表现为「高亮少了」而不是「假高亮」，方向安全
const MENTION_RE = /@([^\s@，。！？；、：,.;:!?"'（）【】《》<>{}()]{1,20})/g

const parts = computed(() => {
  const names = new Set(props.mentionNames)
  const text = String(props.content || '')
  const out = []
  let last = 0
  for (const m of text.matchAll(MENTION_RE)) {
    if (!names.has(m[1])) continue
    if (m.index > last) out.push({ text: text.slice(last, m.index), mentioned: false })
    out.push({ text: m[0], mentioned: true })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last), mentioned: false })
  return out.length ? out : [{ text, mentioned: false }]
})
</script>
