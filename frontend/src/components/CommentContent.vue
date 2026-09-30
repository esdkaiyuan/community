<template>
  <!-- 评论正文渲染：纯文本插值（无 v-html，XSS 面 = 0）。
       富文本白名单只认 **粗体** / `行内代码` / ``` 围栏（utils/richText.js），
       未闭合定界符原样显示（内容零丢失）；代码区不解析其它语法；
       @ 用户名高亮只认 mentionNames（后端 listComments 顶层字段 = 整库识别口径） -->
  <span class="comment-content">
    <template v-for="(block, bi) in blocks" :key="bi">
      <pre
        v-if="block.type === 'fence'"
        data-test="rich-pre"
        class="my-1.5 overflow-x-auto rounded-lg bg-sand px-3 py-2 font-mono text-[13px] leading-relaxed text-ink"
      >{{ block.text }}</pre>
      <template v-else>
        <template v-for="(seg, si) in block.segs" :key="si">
          <code
            v-if="seg.type === 'code'"
            data-test="rich-code"
            class="rounded bg-sand px-1 py-0.5 font-mono text-[0.85em] text-ink"
          >{{ seg.text }}</code>
          <strong
            v-else-if="seg.type === 'bold'"
            data-test="rich-bold"
            class="font-semibold text-ink"
          ><template v-for="(p, pi) in seg.parts" :key="pi"><span
              v-if="p.mentioned"
              class="rounded bg-pine-soft px-0.5 font-medium text-pine-deep"
              data-test="mention"
            >{{ p.text }}</span><template v-else>{{ p.text }}</template></template></strong>
          <template v-else><template v-for="(p, pi) in seg.parts" :key="pi"><span
              v-if="p.mentioned"
              class="rounded bg-pine-soft px-0.5 font-medium text-pine-deep"
              data-test="mention"
            >{{ p.text }}</span><template v-else>{{ p.text }}</template></template></template>
        </template>
      </template>
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { parseFences, parseInline } from '@/utils/richText'

const props = defineProps({
  content: { type: String, default: '' },
  mentionNames: { type: Array, default: () => [] }
})

const MENTION_RE = /@([^\s@，。！？；、：,.;:!?"'（）【】《》<>{}()]{1,20})/g

const names = computed(() => new Set(props.mentionNames))

// 文本段（含粗体内）的 @ 切分：只点亮真实存在的用户名
function mentionParts(text, set) {
  const out = []
  let last = 0
  for (const m of String(text).matchAll(MENTION_RE)) {
    if (!set.has(m[1])) continue
    if (m.index > last) out.push({ text: text.slice(last, m.index), mentioned: false })
    out.push({ text: m[0], mentioned: true })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last), mentioned: false })
  return out.length ? out : [{ text, mentioned: false }]
}

const blocks = computed(() => {
  const set = names.value
  return parseFences(String(props.content || '')).map((b) => {
    if (b.type === 'fence') return b
    return {
      type: 'text',
      segs: parseInline(b.text).map((seg) =>
        seg.type === 'code' ? seg : { ...seg, parts: mentionParts(seg.text, set) }
      )
    }
  })
})
</script>
