// coverFile.js 单元测试 —— 「托管路径判定」的纯函数层，不碰磁盘。
//
// cover_image 走 req.body 直存，是不可信输入：可能是站外 URL，也可能是
// "/uploads/projects/../../package.json" 这类穿越串。白名单一次挡掉
// 路径分隔符 / 盘符冒号 / \0 / "." 与 ".."，第二道 relative 检查是纵深防御。
// deleteManagedFile 只测「非托管不碰磁盘 + 不存在文件幂等 false」，不真删文件
// （沙箱对删除有计数守卫，测试不应依赖删除行为）。
const { test } = require('node:test')
const assert = require('node:assert')
const path = require('node:path')
const {
  COVER_DIR,
  COVER_URL_PREFIX,
  isManagedCover,
  resolveManagedPath,
  deleteManagedFile
} = require('../../src/utils/coverFile')

// ---- isManagedCover ----

test('合法托管路径：自家前缀 + 单层合法文件名', () => {
  assert.strictEqual(isManagedCover('/uploads/projects/a1.png'), true)
  assert.strictEqual(isManagedCover('/uploads/projects/1717000000000-abcdef.webp'), true)
  // 从导出常量拼 URL 同样成立：前缀改了测试跟着失效，而不是两边各写一份悄悄漂移
  assert.strictEqual(isManagedCover(COVER_URL_PREFIX + 'b2.jpg'), true)
})

test('穿越串拒绝', () => {
  assert.strictEqual(isManagedCover('/uploads/projects/../package.json'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/..%2f..%2fetc'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/a/../../x.png'), false)
})

test('分隔符 / 盘符 / 空字节 / 点开头 全部不在白名单内', () => {
  assert.strictEqual(isManagedCover('/uploads/projects/a\\b.png'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/C:evil.png'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/a\u0000b.png'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/.hidden'), false)
  assert.strictEqual(isManagedCover('/uploads/projects/'), false)
})

test('非托管前缀与非字符串', () => {
  assert.strictEqual(isManagedCover('https://evil.com/a.png'), false)
  assert.strictEqual(isManagedCover('/uploads/other/a.png'), false)
  assert.strictEqual(isManagedCover('/uploads/projectsX/a.png'), false)
  assert.strictEqual(isManagedCover(null), false)
  assert.strictEqual(isManagedCover(42), false)
})

// ---- resolveManagedPath ----

test('托管路径解析到 COVER_DIR 内的绝对路径', () => {
  const abs = resolveManagedPath('/uploads/projects/a1.png')
  assert.ok(abs.startsWith(COVER_DIR + path.sep))
  assert.strictEqual(path.basename(abs), 'a1.png')
})

test('解析结果永远跑不出 COVER_DIR（纵深防御）', () => {
  assert.strictEqual(resolveManagedPath('/uploads/projects/../package.json'), null)
  assert.strictEqual(resolveManagedPath('https://evil.com/a.png'), null)
  assert.strictEqual(resolveManagedPath(null), null)
})

// ---- deleteManagedFile ----

test('非托管路径不碰磁盘直接 false', () => {
  assert.strictEqual(deleteManagedFile('https://evil.com/a.png'), false)
  assert.strictEqual(deleteManagedFile('/uploads/projects/../secret'), false)
  assert.strictEqual(deleteManagedFile(undefined), false)
})

test('不存在的托管文件幂等返回 false（ENOENT 视为「已经没有垃圾」）', () => {
  assert.strictEqual(deleteManagedFile('/uploads/projects/no-such-file-9x.png'), false)
})
