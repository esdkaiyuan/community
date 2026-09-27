const projectService = require('../services/project.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok, created } = require('../utils/response')

exports.getProjects = asyncHandler(async (req, res) => {
  const data = await projectService.listProjects({
    ...req.query,
    creatorId: req.query.creatorId,
    // 某人参与过的共创（不含 TA 自己发起的）：公开主页「TA 参与的共创」用
    participantId: req.query.participantId,
    // 「只看收藏」需要登录态；未登录时静默忽略，退化为普通列表
    favoritedBy: req.query.favorited ? req.user?.userId : undefined,
    currentUserId: req.user?.userId
  })
  ok(res, data, '获取项目列表成功')
})

exports.getProjectById = asyncHandler(async (req, res) => {
  const data = await projectService.getProjectDetail(req.params.id, req.user?.userId)
  ok(res, data, '获取项目详情成功')
})

// 热门标签（广场入口用）：公开接口
exports.getProjectTags = asyncHandler(async (req, res) => {
  const data = await projectService.listPopularTags({ limit: req.query.limit })
  ok(res, data, '获取热门标签成功')
})

exports.getProjectParticipants = asyncHandler(async (req, res) => {
  const data = await projectService.listParticipants(req.params.id, req.query)
  ok(res, data, '获取共创伙伴成功')
})

exports.getProjectRelated = asyncHandler(async (req, res) => {
  const data = await projectService.listRelatedProjects(req.params.id, req.query)
  ok(res, data, '获取相关项目成功')
})

exports.createProject = asyncHandler(async (req, res) => {
  const data = await projectService.createProject({ ...req.body, creatorId: req.user.userId })
  created(res, data, '项目创建成功')
})

exports.updateProject = asyncHandler(async (req, res) => {
  const data = await projectService.updateProject(req.params.id, req.user.userId, req.body)
  ok(res, data, '项目更新成功')
})

exports.deleteProject = asyncHandler(async (req, res) => {
  await projectService.deleteProject(req.params.id, req.user.userId)
  ok(res, null, '项目删除成功')
})

exports.likeProject = asyncHandler(async (req, res) => {
  const data = await projectService.likeProject(req.params.id, req.user.userId)
  ok(res, data, '点赞成功')
})

exports.unlikeProject = asyncHandler(async (req, res) => {
  const data = await projectService.unlikeProject(req.params.id, req.user.userId)
  ok(res, data, '已取消点赞')
})

exports.participateProject = asyncHandler(async (req, res) => {
  const data = await projectService.participateProject(req.params.id, req.user.userId)
  ok(res, data, '参与成功')
})

exports.cancelParticipate = asyncHandler(async (req, res) => {
  const data = await projectService.cancelParticipate(req.params.id, req.user.userId)
  ok(res, data, '已取消参与')
})

exports.favoriteProject = asyncHandler(async (req, res) => {
  const data = await projectService.favoriteProject(req.params.id, req.user.userId)
  ok(res, data, '收藏成功')
})

exports.unfavoriteProject = asyncHandler(async (req, res) => {
  const data = await projectService.unfavoriteProject(req.params.id, req.user.userId)
  ok(res, data, '已取消收藏')
})
