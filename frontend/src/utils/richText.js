// 评论富文本解析 —— 零 import 纯函数（node 可直接单测，约束见 verify 脚本）。
// 白名单只认三种语法：**粗体**、`行内代码`、``` 围栏代码块（语言标注忽略）。
// 不产生 HTML：解析结果交给组件纯插值渲染（XSS 面 = 0）。
// 约束：内容零丢失 —— 未闭合定界符原样显示；行内代码与代码块内不解析其它语法；
// 粗体内不含 *（**a*b** 整段按字面显示），行内代码优先于粗体（与 markdown 主流一致）。

const INLINE_CODE_RE = /`([^`\n]+)`/g
const BOLD_RE = /\*\*([^*\n]+?)\*\*/g
const FENCE_OPEN_RE = /^```[^\n`]*$/
const FENCE_CLOSE_RE = /^```[^\n`]*$/

/**
 * 切围栏代码块：返回 [{ type: 'fence' | 'text', text }]。
 * 开启围栏但找不到闭合行时整段按纯文本降级（未闭合定界符原样显示）。
 */
export function parseFences(text) {
  const out = []
  const lines = String(text ?? '').split('\n')
  let buf = []
  const flush = () => {
    if (buf.length) {
      out.push({ type: 'text', text: buf.join('\n') })
      buf = []
    }
  }
  for (let i = 0; i < lines.length; i++) {
    if (!FENCE_OPEN_RE.test(lines[i])) {
      buf.push(lines[i])
      continue
    }
    // 找闭合围栏；找不到就当纯文本
    let close = -1
    for (let j = i + 1; j < lines.length; j++) {
      if (FENCE_CLOSE_RE.test(lines[j])) {
        close = j
        break
      }
    }
    if (close === -1) {
      buf.push(lines[i])
      continue
    }
    flush()
    out.push({ type: 'fence', text: lines.slice(i + 1, close).join('\n') })
    i = close
  }
  flush()
  return out.length ? out : [{ type: 'text', text: '' }]
}

/** 粗体段解析（行内代码已先行切出，粗体只在纯文本段里识别） */
function pushBold(out, slice) {
  let last = 0
  for (const m of slice.matchAll(BOLD_RE)) {
    if (m.index > last) out.push({ type: 'text', text: slice.slice(last, m.index) })
    out.push({ type: 'bold', text: m[1] })
    last = m.index + m[0].length
  }
  if (last < slice.length) out.push({ type: 'text', text: slice.slice(last) })
}

/**
 * 行内解析：先切 `行内代码`，剩余文本段里再切 **粗体**。
 * 返回 [{ type: 'code' | 'bold' | 'text', text }]
 */
export function parseInline(text) {
  const out = []
  let last = 0
  const s = String(text ?? '')
  for (const m of s.matchAll(INLINE_CODE_RE)) {
    if (m.index > last) pushBold(out, s.slice(last, m.index))
    out.push({ type: 'code', text: m[1] })
    last = m.index + m[0].length
  }
  pushBold(out, s.slice(last))
  return out
}
