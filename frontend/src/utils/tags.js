// 标签的共享约定：与后端 src/services/project.service.js 的 normalizeTags 同一套规则
// （5 个上限、单个 12 字符、剥 emoji、大小写不敏感去重）
import { stripEmoji } from '@/utils/text'

export const TAG_MAX_COUNT = 5
export const TAG_MAX_LENGTH = 12

// 冷启动候选池：线上项目的 tags 全为空时「热门标签」也是空的，
// 新用户面对空白输入框往往什么都不打，标签生态就永远起不来。
// 给一组通用标签兜底，让「点一下就选上」在冷启动阶段同样可用。
export const DEFAULT_TAG_SUGGESTIONS = [
  '开源',
  '环保',
  '公益',
  '线下活动',
  '教育',
  '科技',
  '艺术',
  '手作',
  '无障碍',
  '社区营造'
]

// 单个标签的净化：剥 emoji → 收敛空白 → 截断
export const cleanTag = (raw) =>
  stripEmoji(String(raw ?? ''))
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, TAG_MAX_LENGTH)

// 追加一个标签；重复 / 为空 / 已满时原样返回（引用不变，便于调用方判断是否变化）
export const addTagToList = (list, raw) => {
  const name = cleanTag(raw)
  if (!name || list.length >= TAG_MAX_COUNT) return list
  if (list.some((t) => t.toLowerCase() === name.toLowerCase())) return list
  return [...list, name]
}

// 把任意来源（后端返回的 tags、粘贴的多标签字符串）归一成表单可用的数组
export const toTagList = (raw) => {
  const source = Array.isArray(raw) ? raw : String(raw ?? '').split(/[,，\s]+/)
  return source.reduce((acc, item) => addTagToList(acc, item), [])
}
