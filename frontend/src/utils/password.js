// 密码边界与强度评估：注册页与「账号安全 → 登录密码」共用同一份口径。
//
// 🔥 抽出来的理由与 normalizeTags / normalizeUsername 一样：同一个字段被两个界面
// 分别处理时，口径一定会漂 —— 一处改「至少 8 位」、另一处还写着 6 位，用户就会遇到
// 「这边能过、那边被拒」。
//
// ⚠️ 这里的上下界必须与后端 backend/src/services/user.service.js 的
// PASSWORD_MIN_LENGTH / PASSWORD_MAX_LENGTH 完全一致，且要等于输入框的 maxlength。
// scripts/verify_password_change.py 会解析三处源码直接比对（不靠人工同步）。
export const PASSWORD_MIN_LENGTH = 6
export const PASSWORD_MAX_LENGTH = 64

// 强度 = 长度 + 字符种类（四档累计，展示成 3 格）。刻意不引入 zxcvbn 这类重型依赖：
// 它只影响一根提示条的观感，不参与任何校验决策（真正的门槛是服务端的上下界）。
export const passwordStrength = (password) => {
  const p = password || ''
  let score = 0
  if (p.length >= PASSWORD_MIN_LENGTH) score++
  if (p.length >= 10) score++
  if (/[a-zA-Z]/.test(p) && /\d/.test(p)) score++
  if (/[^a-zA-Z0-9]/.test(p)) score++

  if (score <= 1) return { level: 1, label: '较弱', color: 'bg-clay', textColor: 'text-clay' }
  if (score <= 2) return { level: 2, label: '中等', color: 'bg-amber-warm', textColor: 'text-amber-warm' }
  return { level: 3, label: '强', color: 'bg-pine', textColor: 'text-pine' }
}
