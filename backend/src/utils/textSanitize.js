/* eslint-disable no-control-regex -- 本模块的职责就是「匹配并移除控制字符 / 装饰字符」，
   不匹配它们就无从移除。这条规则在这里方向是反的，所以整文件豁免。
   这类正则**只允许出现在这里和 logSanitize.js 两个模块**：业务代码要清洗文本就调这里的
   函数，别自己写正则 —— 否则「no-control-regex」会逼着每个调用方各挂一次豁免，
   而那些豁免散落各处、没人看得懂为什么，真正的规则反而更容易被写错。 */
// 用户输入文本净化：移除 emoji 及零宽连接符等装饰字符（全站仅允许矢量图标，评论/发布内容同理）
const EMOJI_RE =
  /[\u{1F000}-\u{1FAFF}]|[\u{2600}-\u{27BF}]|[\u{2B00}-\u{2BFF}]|[\u{FE00}-\u{FE0F}]|[\u{1F1E6}-\u{1F1FF}]|[\u{2190}-\u{21FF}]|\u{200D}|\u{20E3}|\u{00A9}|\u{00AE}|\u{2122}|\u{3030}|\u{303D}|\u{3297}|\u{3299}/gu

// 清理后的文本（多余空行与首尾空白一并收敛）
const stripEmoji = (text) => {
  if (typeof text !== 'string') return text
  return text
    .replace(EMOJI_RE, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

// 是否包含 emoji（用于前端/后端提示"已自动移除表情符号"）
const hasEmoji = (text) => typeof text === 'string' && EMOJI_RE.test(text)

// ---- 控制字符与不可见字符 ----
//
// 这两类字符用户根本看不见，却会改变别人看到的东西：
//   - C0/C1 控制字符与 DEL：`\r\n` 能在按行解析的下游日志系统里**凭空伪造一条记录**；
//     `\x1b[31m` 会改写终端配色；`\x00` 会截断下游解析器的字符串。
//   - 零宽字符与双向文本控制：`U+202E`（RLO）能让整段文本反向显示，用来伪造视觉内容；
//     `U+200B` 能在肉眼看不见的地方把两个词粘成一个。
//
// ⚠️ 是否保留换行由调用方决定，这是业务语义而不是清洗细节：
//   单行字段（用户名）连 `\t` `\n` 一起去掉 —— 那里出现换行必然是攻击载荷或粘贴夹带；
//   多行字段（简介）必须保留 `\n` —— 用户真的会分段，删掉等于篡改他的内容。
const CONTROL_SINGLE_LINE_RE = /[\u0000-\u001F\u007F-\u009F]/g
const CONTROL_MULTI_LINE_RE = /[\u0000-\u0009\u000B\u000C\u000E-\u001F\u007F-\u009F]/g
const INVISIBLE_RE = /[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g

/**
 * 去掉控制字符与不可见字符（**删除**而不是替换成空格）。
 *
 * @param {string} text
 * @param {{ keepNewlines?: boolean }} [options] 多行文本（如简介）传 true 以保留 `\n`
 * @returns {string} 非字符串输入原样返回
 */
const stripControlChars = (text, { keepNewlines = false } = {}) => {
  if (typeof text !== 'string') return text
  const control = keepNewlines ? CONTROL_MULTI_LINE_RE : CONTROL_SINGLE_LINE_RE
  return text.replace(control, '').replace(INVISIBLE_RE, '')
}

module.exports = { stripEmoji, hasEmoji, stripControlChars }
