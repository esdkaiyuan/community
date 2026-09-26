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

module.exports = { stripEmoji, hasEmoji }
