const { Op } = require('sequelize')
const sequelize = require('../config/database')
const { Project, Category, User, ProjectParticipant, ProjectLike, ProjectFavorite, ProjectView } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji } = require('../utils/textSanitize')
const { toClientUser } = require('./user.service')
const notificationService = require('./notification.service')
const coverService = require('./cover.service')
const activityLogService = require('./activityLog.service')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const { bumpCounter } = require('../utils/counter')

// 数据库行 -> 前端数据形状（camelCase）
const toClientProject = (p, extra = {}) => {
  const row = p.toJSON ? p.toJSON() : p
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    coverImage: row.cover_image,
    categoryId: row.category_id,
    categoryName: row.category ? row.category.name : null,
    tags: Array.isArray(row.tags) ? row.tags : [],
    participantCount: row.participant_count || 0,
    likeCount: row.like_count || 0,
    commentCount: row.comment_count || 0,
    viewCount: row.view_count || 0,
    isRecommend: !!row.is_recommend,
    isHot: !!row.is_hot,
    // 近 7 天活跃度：只有列表按 sort=trending 查询时才带出来
    ...(row.trendScore === undefined || row.trendScore === null
      ? {}
      : { trendScore: Number(row.trendScore) || 0 }),
    createdAt: row.created_at,
    creator: row.creator ? toClientUser(row.creator) : null,
    ...extra
  }
}

// 共创者预览条数（详情页头像堆叠）
const PARTICIPANT_PREVIEW = 8

// 中间表行 -> 前端共创者形状（用户已注销时兜底，避免渲染空头像）
const toClientParticipant = (p) => {
  const row = p.toJSON ? p.toJSON() : p
  const user = row.user
  return {
    id: user ? user.id : row.user_id,
    username: user && user.username ? user.username : '已注销用户',
    avatar: user ? user.avatar || '' : '',
    role: row.role,
    joinedAt: row.joined_at
  }
}

// 发起人永远置顶，其余按加入时间升序
const sortParticipants = (rows) =>
  rows.slice().sort((a, b) => {
    const ac = a.role === 'creator' ? 0 : 1
    const bc = b.role === 'creator' ? 0 : 1
    if (ac !== bc) return ac - bc
    return new Date(a.joined_at).getTime() - new Date(b.joined_at).getTime()
  })

// 「本周热门」的统计窗口（天）
const TREND_WINDOW_DAYS = 7

// 近 7 天的活跃度：参与（最重）×3 + 评论 ×2 + 点赞 ×1。
// 只看累计值（like_count）的话，早期爆款会永远压在上面 —— 时间窗口衡量的是「最近发生了什么」
const TREND_SCORE_SQL = `(
  (SELECT COUNT(*) FROM project_likes pl
     WHERE pl.project_id = \`Project\`.\`id\`
       AND pl.created_at >= DATE_SUB(NOW(), INTERVAL ${TREND_WINDOW_DAYS} DAY))
  + (SELECT COUNT(*) FROM project_comments pc
     WHERE pc.project_id = \`Project\`.\`id\`
       AND pc.status = 1
       AND pc.created_at >= DATE_SUB(NOW(), INTERVAL ${TREND_WINDOW_DAYS} DAY)) * 2
  + (SELECT COUNT(*) FROM project_participants pp
     WHERE pp.project_id = \`Project\`.\`id\`
       AND pp.role <> 'creator'
       AND pp.joined_at >= DATE_SUB(NOW(), INTERVAL ${TREND_WINDOW_DAYS} DAY)) * 3
)`

const SORT_MAP = {
  latest: [['created_at', 'DESC']],
  hot: [['like_count', 'DESC']],
  participants: [['participant_count', 'DESC']],
  recommend: [
    ['is_recommend', 'DESC'],
    ['like_count', 'DESC']
  ]
}

// 标签约束：与前端输入框保持一致（5 个上限、单个 12 字符）
const TAG_MAX_COUNT = 5
const TAG_MAX_LENGTH = 12

// 文本上界：同样与前端输入框的 maxlength 对齐（标题 60 / 介绍 2000）。
// 这两条不能省 —— 缺了它们，超长输入会一路走到 MySQL 列宽限制
// （title 是 VARCHAR(200)、description 是 TEXT），抛 1406「Data too long」，
// 经 errorHandler 变成用户完全看不懂的 500「数据存储异常」。
// 取值同时满足两个条件：不严于前端承诺（否则前端能填、提交必失败），
// 又远在列容量之内（60 ≪ 200 字符；2000 字符 × 最多 4 字节 ≪ 65535 字节）。
const TITLE_MAX_LENGTH = 60
const DESCRIPTION_MAX_LENGTH = 2000

// 标签归一化：剥 emoji → 收敛空白 → 去重（大小写不敏感，避免「开源」与「开源 」被算成两个标签）
// 前端已做一遍，这里是服务端的最后一道闸：直接调 API 也要得到干净的 tags
// 超长不截断而是拒绝：标题/介绍/评论全站都是「超长 400」，唯独标签曾静默 slice ——
// 15 字标签悄悄变 12 字残体，用户毫无感知。改为明确拒绝（净化后超长才算，与评论同哲学）
const normalizeTags = (tags) => {
  if (!Array.isArray(tags)) return []
  const result = []
  const seen = new Set()
  for (const raw of tags) {
    if (result.length >= TAG_MAX_COUNT) break
    const name = stripEmoji(String(raw ?? ''))
      .replace(/\s+/g, ' ')
      .trim()
    if (!name) continue
    if (name.length > TAG_MAX_LENGTH) {
      throw ApiError.badRequest(`单个标签最多 ${TAG_MAX_LENGTH} 个字符`)
    }
    const key = name.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    result.push(name)
  }
  return result
}

// 分类在线上是 NOT NULL：不校验的话 MySQL 会直接抛 1048，前端只能看到 500
const assertCategoryExists = async (categoryId) => {
  if (!categoryId) throw ApiError.badRequest('请选择项目分类')
  if (!(await Category.findByPk(categoryId))) throw ApiError.badRequest('所选分类不存在')
  return categoryId
}

const getProjectOr404 = async (id) => {
  // 详情/编辑都要用 category 与 creator 的展示字段，统一在这里带出来
  const project = await Project.findByPk(id, {
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ]
  })
  if (!project) throw ApiError.notFound('项目不存在')
  return project
}

exports.listProjects = async ({
  page = 1,
  pageSize = 12,
  categoryId,
  tag,
  search,
  filter,
  sort,
  creatorId,
  participantId,
  favoritedBy,
  currentUserId
}) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 12 })
  const offset = (page - 1) * limit

  const where = {}
  if (categoryId) where.category_id = categoryId
  if (creatorId) where.creator_id = creatorId
  // 筛选只认「编辑推荐」：这个标记位由 scripts/refresh-project-flags.js 维护。
  // 曾经还有一条 `filter=hot -> is_hot = 1`，但全仓没有任何代码写 is_hot，
  // 于是该筛选永远返回空列表 —— 一个长得能用、实际恒空的假入口。
  // 「热门」语义交给 sort=hot（按 like_count 排序），不再依赖人工标记位；
  // 任何认不出的 filter 值一律静默忽略（退化成不过滤），不拼进 SQL。
  if (filter === 'recommend') where.is_recommend = 1
  // 标签筛选：tags 列存 JSON 数组，用 JSON_CONTAINS 精确匹配，
  // 而不是 LIKE —— 否则「开源」会误命中「开源硬件」这类互含子串的标签
  if (tag) {
    where[Op.and] = [
      sequelize.where(
        sequelize.fn('JSON_CONTAINS', sequelize.col('Project.tags'), JSON.stringify(tag)),
        1
      )
    ]
  }
  if (search) {
    where[Op.or] = [
      { title: { [Op.like]: `%${search}%` } },
      { description: { [Op.like]: `%${search}%` } },
      // 关键词也命中标签：搜「开源」能找到打了该标签的项目
      { tags: { [Op.like]: `%${search}%` } }
    ]
  }

  // 收窄集合类筛选：先取 id 列表再用 IN 收窄，**交集为空必须短路返回**（否则生成非法 SQL）
  const idSets = []

  if (participantId) {
    // 「参与过的共创」不含自己发起的，否则会与「TA 发布的项目」重复
    const joins = await ProjectParticipant.findAll({
      where: { user_id: participantId, role: { [Op.ne]: 'creator' } },
      attributes: ['project_id']
    })
    idSets.push(joins.map((j) => j.project_id))
  }

  // 「只看收藏」
  if (favoritedBy) {
    const favorites = await ProjectFavorite.findAll({
      where: { user_id: favoritedBy },
      attributes: ['project_id']
    })
    idSets.push(favorites.map((f) => f.project_id))
  }

  if (idSets.length) {
    const ids = idSets.reduce((acc, cur) => acc.filter((id) => cur.includes(id)))
    if (!ids.length) return { projects: [], total: 0, page, pageSize: limit }
    where.id = { [Op.in]: ids }
  }

  // 「本周热门」只有在这个排序下才算：三个子查询白给其它排序添负担，
  // 而且分数只在「按它排序」时才有解释意义（卡片据此显示「本周 N」徽标）
  const isTrending = sort === 'trending'

  // SORT_MAP[sort] 不能直接取：sort 是用户输入，`?sort=__proto__` 会命中原型链上的
  // Object.prototype（truthy，绕过了 `|| 默认值` 的兜底），塞给 Sequelize 直接 500。
  // 用 hasOwnProperty 收口到「自有键」，任何坏值一律退回默认排序。
  const sortOrder = Object.prototype.hasOwnProperty.call(SORT_MAP, sort)
    ? SORT_MAP[sort]
    : SORT_MAP.latest

  const { count, rows } = await Project.findAndCountAll({
    where,
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ],
    ...(isTrending
      ? {
          attributes: { include: [[sequelize.literal(TREND_SCORE_SQL), 'trendScore']] },
          order: [sequelize.literal('trendScore DESC'), ['created_at', 'DESC']]
        }
      : { order: sortOrder }),
    limit,
    offset,
    distinct: true
  })

  // 登录用户：批量标记本页项目的收藏状态（卡片书签徽标用），只查一次
  let favoritedIds = null
  if (currentUserId && rows.length) {
    const favorites = await ProjectFavorite.findAll({
      where: { user_id: currentUserId, project_id: { [Op.in]: rows.map((r) => r.id) } },
      attributes: ['project_id']
    })
    favoritedIds = new Set(favorites.map((f) => f.project_id))
  }

  return {
    projects: rows.map((row) =>
      toClientProject(row, favoritedIds ? { favorited: favoritedIds.has(row.id) } : {})
    ),
    total: count,
    page,
    pageSize: limit
  }
}

// 标签是 projects.tags 里的 JSON 数组（无独立表），这里全量聚合出「热门标签」
// 数据量小、也无索引可用，直接拉非空行在内存里计数；随项目增长可改为定时物化
exports.listPopularTags = async ({ limit = 12 } = {}) => {
  const max = clampInt(limit, { max: 30, fallback: 12 })

  // 单条 SQL 聚合：JSON_TABLE 把 tags 里的 JSON 数组摊成行，GROUP BY 直接计数。
  // 旧实现是把**全表** projects 的 tags 捞进内存再用 Map 逐条数 —— 全表扫描 +
  // 大内存 + 无上限，数据量一大就拖垮列表页。交给数据库只返回聚合结果。
  // JSON_VALID 是必要的护栏：历史上存在非 JSON 的脏值，缺了它整条查询会报错。
  const [rows] = await sequelize.query(
    `SELECT jt.tag_name AS name, COUNT(*) AS cnt
       FROM projects p,
            JSON_TABLE(p.tags, '$[*]' COLUMNS (tag_name VARCHAR(50) PATH '$')) jt
      WHERE p.deleted_at IS NULL
        AND p.tags IS NOT NULL
        AND JSON_VALID(p.tags)
      GROUP BY jt.tag_name
      ORDER BY cnt DESC, jt.tag_name ASC
      LIMIT ${max}`
  )

  // 并列时按名称的二进制序（旧实现用 zh localeCompare）。排序口径不同但同样稳定，
  // 热门标签是索引入口，顺序稳定比「按中文习惯排」更重要。
  return rows.map((r) => ({ name: r.name, count: Number(r.cnt) }))
}

// —— 相关项目推荐 ——
// 权重：共同标签最能说明「为什么推这条」，同分类次之；
// 跨发起人 +1 只是并列时的多样性偏好，**不是硬性剔除**——
// 只在 2 个项目的冷启动库里硬剔的话，推荐区会永远空着
const RELATED_SCORE = { tag: 3, category: 2, crossCreator: 1 }
const RELATED_POOL = 60 // 候选池上限：够排序即可，不必把整表拉进内存

exports.listRelatedProjects = async (id, { limit = 3 } = {}) => {
  const project = await getProjectOr404(id)
  const max = clampInt(limit, { max: 12, fallback: 3 })

  // 原样大小写用于 SQL 收窄（JSON_CONTAINS 大小写敏感），小写副本只用于比对
  const tags = (Array.isArray(project.tags) ? project.tags : [])
    .map((t) => String(t).trim())
    .filter(Boolean)
  const tagKeys = new Set(tags.map((t) => t.toLowerCase()))

  // 候选池：至少共享一个标签，或同分类。一条线索都没有就直接返回空，
  // 不做「最新项目」兜底 —— 那等于把无关结果包装成推荐
  const candidates = []
  tags.forEach((t) =>
    candidates.push(
      sequelize.where(
        sequelize.fn('JSON_CONTAINS', sequelize.col('Project.tags'), JSON.stringify(t)),
        1
      )
    )
  )
  if (project.category_id) candidates.push({ category_id: project.category_id })
  if (!candidates.length) return []

  const rows = await Project.findAll({
    where: {
      id: { [Op.ne]: project.id },
      [Op.or]: candidates
    },
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ],
    order: [['created_at', 'DESC']],
    limit: RELATED_POOL
  })

  const scored = rows.map((row) => {
    const rowTags = Array.isArray(row.tags) ? row.tags : []
    // 比对用小写，展示用原样
    const byKey = new Map(rowTags.map((t) => [String(t).trim().toLowerCase(), String(t).trim()]))
    const sharedTags = [...byKey.keys()].filter((k) => tagKeys.has(k)).map((k) => byKey.get(k))
    const sameCategory = !!(project.category_id && row.category_id === project.category_id)
    const sameCreator = row.creator_id === project.creator_id

    return {
      row,
      reason: { sharedTags, sameCategory, sameCreator },
      score:
        sharedTags.length * RELATED_SCORE.tag +
        (sameCategory ? RELATED_SCORE.category : 0) +
        (sameCreator ? 0 : RELATED_SCORE.crossCreator)
    }
  })

  return scored
    .filter((x) => x.reason.sharedTags.length || x.reason.sameCategory)
    // 分高者在前；同分让新的项目占先，避免每次刷新都推那几个老项目
    .sort((a, b) => b.score - a.score || new Date(b.row.created_at) - new Date(a.row.created_at))
    .slice(0, max)
    // 推荐理由要跟着结果回去：看不见依据的推荐会让人怀疑是不是随机塞的
    .map((x) => toClientProject(x.row, { relatedReason: x.reason }))
}

// SQL 层自增浏览量（literal）。
// ⚠️ 必须用 literal，不能写成 `project.view_count + 1`：
// 后者是「先读内存里的旧值、再把旧值 +1 写回」，两个并发请求会读到同一个旧值、
// 各自写回同一个结果，**只 +1（丢更新）**。浏览量天然是高频并发写，这个竞态很容易踩到。
const bumpViewCount = (projectId) =>
  Project.update(
    { view_count: sequelize.literal('view_count + 1') },
    { where: { id: projectId } }
  ).catch(() => {})

// 登录用户浏览去重：project_views 复合主键 (project_id, user_id) 占位，
// 只有真正新插入（created=true）才自增 —— 同一用户终身只 +1，刷新/重访不重复计数。
// findOrCreate 靠主键兜底并发：并发首访只有一个 created=true，其余回头重读，不会重复自增。
const recordProjectView = async (projectId, userId) => {
  try {
    const [, created] = await ProjectView.findOrCreate({
      where: { project_id: projectId, user_id: userId }
    })
    if (created) bumpViewCount(projectId)
  } catch {
    // 去重表故障不阻塞详情响应（退化为不计本次浏览）
  }
}

exports.getProjectDetail = async (id, currentUserId) => {
  const project = await getProjectOr404(id)

  // 浏览量异步累加，不阻塞响应。登录用户终身去重，游客每次 +1。
  if (currentUserId) {
    recordProjectView(id, currentUserId)
  } else {
    bumpViewCount(id)
  }

  const [participantRows, participantTotal, liked, participated, favorited] = await Promise.all([
    ProjectParticipant.findAll({
      where: { project_id: id },
      include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }],
      order: [['joined_at', 'ASC']],
      limit: 200
    }),
    ProjectParticipant.count({ where: { project_id: id } }),
    currentUserId ? ProjectLike.findOne({ where: { project_id: id, user_id: currentUserId } }) : null,
    currentUserId ? ProjectParticipant.findOne({ where: { project_id: id, user_id: currentUserId } }) : null,
    currentUserId ? ProjectFavorite.findOne({ where: { project_id: id, user_id: currentUserId } }) : null
  ])

  // 历史数据可能存在计数漂移：以中间表真实行数为准，并异步回写自愈
  if (project.participant_count !== participantTotal) {
    Project.update({ participant_count: participantTotal }, { where: { id } }).catch(() => {})
  }

  // 详情页只带预览条数，完整名单走 /projects/:id/participants
  const extra = {
    participantCount: participantTotal,
    participants: sortParticipants(participantRows)
      .slice(0, PARTICIPANT_PREVIEW)
      .map(toClientParticipant)
  }
  if (currentUserId) {
    extra.liked = !!liked
    extra.participated = !!participated
    extra.favorited = !!favorited
  }

  return toClientProject(project, extra)
}

exports.listParticipants = async (id, { page = 1, pageSize = 24 } = {}) => {
  await getProjectOr404(id)
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 60, fallback: 24 })
  const offset = (page - 1) * limit

  const { count, rows } = await ProjectParticipant.findAndCountAll({
    where: { project_id: id },
    include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }],
    order: [['joined_at', 'ASC']],
    limit,
    offset
  })

  return {
    // 分页列表保持数据库顺序（joined_at 升序），分页切片后才重排会跨页错位
    participants: rows.map(toClientParticipant),
    total: count,
    page,
    pageSize: limit
  }
}

exports.createProject = async ({ title, description, coverImage, categoryId, tags, creatorId, req }) => {
  const cleanTitle = stripEmoji(String(title ?? '')).trim()
  if (!cleanTitle) throw ApiError.badRequest('标题为必填项')
  if (cleanTitle.length < 4) throw ApiError.badRequest('标题至少 4 个字符')
  if (cleanTitle.length > TITLE_MAX_LENGTH) {
    throw ApiError.badRequest(`标题最多 ${TITLE_MAX_LENGTH} 个字符`)
  }
  const cleanDescription = stripEmoji(String(description ?? '')).trim()
  if (cleanDescription.length < 20) {
    throw ApiError.badRequest('项目介绍至少 20 个字符')
  }
  if (cleanDescription.length > DESCRIPTION_MAX_LENGTH) {
    throw ApiError.badRequest(`项目介绍最多 ${DESCRIPTION_MAX_LENGTH} 个字符`)
  }
  await assertCategoryExists(categoryId)

  const project = await Project.create({
    title: cleanTitle,
    description: cleanDescription,
    cover_image: coverImage || null,
    category_id: categoryId,
    creator_id: creatorId,
    tags: normalizeTags(tags)
  })

  await ProjectParticipant.create({ project_id: project.id, user_id: creatorId, role: 'creator' })
  // 发起人自己也是一名共创者：计数列从 0 起，不补这一下列表里会永远少 1，
  // 「参与最多」排序也跟着失真（详情页的自愈只能兜住详情页，列表读的是列值）
  project.participant_count = 1
  await project.save()

  // 操作日志：写在业务全部成功之后。record() 内部吞异常，
  // 所以「日志写失败」不会变成用户的发布失败。
  await activityLogService.logProjectCreated({ creatorId, project, req })

  return toClientProject(project)
}

exports.updateProject = async (id, userId, { title, description, coverImage, categoryId, tags }, req) => {
  const project = await getProjectOr404(id)
  if (project.creator_id !== userId) throw ApiError.forbidden('无权修改此项目')

  // 换封面 / 清空封面时，旧的上传文件会变成没人引用的孤儿。先留一份旧值，
  // 等保存成功后再回收（失败时不动磁盘，避免「改了没生效却把图删了」）。
  const previousCover = project.cover_image

  // 变更前快照：保存后用它 diff 出「这次究竟改了什么」。比在每个赋值分支里手动
  // push 稳 —— 将来加字段时不会漏记。
  const before = {
    title: project.title,
    description: project.description,
    cover_image: project.cover_image,
    category_id: project.category_id,
    tags: JSON.stringify(project.tags)
  }

  if (title !== undefined) {
    const cleanTitle = stripEmoji(String(title)).trim()
    if (cleanTitle.length < 4) throw ApiError.badRequest('标题至少 4 个字符')
    if (cleanTitle.length > TITLE_MAX_LENGTH) {
      throw ApiError.badRequest(`标题最多 ${TITLE_MAX_LENGTH} 个字符`)
    }
    project.title = cleanTitle
  }
  if (description !== undefined) {
    const cleanDescription = stripEmoji(String(description)).trim()
    if (cleanDescription.length < 20) throw ApiError.badRequest('项目介绍至少 20 个字符')
    if (cleanDescription.length > DESCRIPTION_MAX_LENGTH) {
      throw ApiError.badRequest(`项目介绍最多 ${DESCRIPTION_MAX_LENGTH} 个字符`)
    }
    project.description = cleanDescription
  }
  if (coverImage !== undefined) project.cover_image = coverImage || null
  if (categoryId !== undefined) project.category_id = await assertCategoryExists(categoryId)
  // 传空数组即清空标签（编辑页允许把标签删光）
  if (tags !== undefined && Array.isArray(tags)) project.tags = normalizeTags(tags)

  await project.save()

  // 回收放在 save 之后：回收本身失败不影响本次编辑的结果，也不该让接口报错
  if (coverImage !== undefined && previousCover && previousCover !== project.cover_image) {
    await coverService.releaseCover(previousCover, id).catch(() => {})
  }

  // 只有真改动了才留痕：空 PUT（什么都没变）写一条「改动了 无」只是噪音。
  // 字段名是代码里写死的常量，不来自用户输入。
  const changedFields = ['title', 'description', 'cover_image', 'category_id', 'tags'].filter((key) => {
    const now = key === 'tags' ? JSON.stringify(project.tags) : project[key]
    return String(before[key]) !== String(now)
  })
  if (changedFields.length) {
    await activityLogService.logProjectUpdated({ userId, project, changedFields, req })
  }

  return toClientProject(project)
}

exports.deleteProject = async (id, userId, req) => {
  const project = await getProjectOr404(id)
  if (project.creator_id !== userId) throw ApiError.forbidden('无权删除此项目')
  await project.destroy()
  // 日志在删除之后写：项目已软删除，日志表刻意不挂外键，所以留着不受影响
  await activityLogService.logProjectDeleted({ userId, project, req })
}

exports.likeProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectLike.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已点赞过该项目')

  await ProjectLike.create({ project_id: id, user_id: userId })
  // 原子自增：交给数据库做。绝不能「读出来 +1 再写回」——并发下会丢更新
  const likeCount = await bumpCounter(Project, id, 'like_count', 1)
  return { likeCount }
}

exports.unlikeProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectLike.findOne({ where: { project_id: id, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未点赞该项目')

  await existing.destroy()
  // 自减同理；下限由 SQL 的 GREATEST 兜住，不会减成负数
  const likeCount = await bumpCounter(Project, id, 'like_count', -1)
  return { likeCount }
}

// 收藏项目（数据库唯一键兜底防重复）
exports.favoriteProject = async (id, userId) => {
  await getProjectOr404(id)

  const existing = await ProjectFavorite.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已收藏过该项目')

  await ProjectFavorite.create({ project_id: id, user_id: userId })
  return { favorited: true }
}

exports.unfavoriteProject = async (id, userId) => {
  await getProjectOr404(id)

  const existing = await ProjectFavorite.findOne({ where: { project_id: id, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未收藏该项目')

  await existing.destroy()
  return { favorited: false }
}

exports.participateProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectParticipant.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已参与此项目')

  await ProjectParticipant.create({ project_id: id, user_id: userId, role: 'member' })
  const participantCount = await bumpCounter(Project, id, 'participant_count', 1)

  // 通知发起人（同一人对同一项目只提醒一次，避免「退出 → 再加入」刷屏）
  notificationService.notifyOnce({
    userId: project.creator_id,
    type: 'participate',
    actorId: userId,
    projectId: Number(id)
  })

  return { participantCount }
}

exports.cancelParticipate = async (id, userId) => {
  const project = await getProjectOr404(id)

  const participant = await ProjectParticipant.findOne({ where: { project_id: id, user_id: userId } })
  if (!participant) throw ApiError.badRequest('未参与此项目')
  if (participant.role === 'creator') throw ApiError.badRequest('项目创建者不能退出自己的项目')

  await participant.destroy()
  const participantCount = await bumpCounter(Project, id, 'participant_count', -1)
  return { participantCount }
}

exports.toClientProject = toClientProject
