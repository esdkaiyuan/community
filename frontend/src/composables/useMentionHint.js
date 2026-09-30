import { ref, watch } from 'vue'

// 行尾 @token 检测：@ + 已输入片段（可为空）。
// 只认「文本末尾正在打 @」的场景——textarea 不做 caret 检测的轻量近似；
// 句中 @ 不弹浮层，但用户打全名后仍会被后端识别并通知，不会丢功能
const TAIL_RE = /(?:^|\s)@([^\s@，。！？；、：,.;:!?"'（）【】《》<>{}()]{0,20})$/

/**
 * 监听一个文本 ref，返回行尾 @token。
 * token 为 null 表示当前不处于提及输入态；字符串是已输入的候选过滤片段。
 */
export function useMentionHint(source) {
  const token = ref(null)
  watch(source, (text) => {
    const m = TAIL_RE.exec(String(text || ''))
    token.value = m ? m[1] : null
  })
  return { token }
}
