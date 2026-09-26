const { Project, Category, User } = require('../models')
const { Op } = require('sequelize')

// 将数据库行转换为前端使用的数据形状（camelCase）
const toClientProject = (p) => {
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
    createdAt: row.created_at,
    creator: row.creator
      ? { id: row.creator.id, username: row.creator.username, avatar: row.creator.avatar || '' }
      : null
  }
}

// 获取项目列表（支持分页、分类、筛选、排序、搜索）
exports.getProjects = async (req, res) => {
  try {
    const {
      page = 1,
      pageSize = 12,
      categoryId,
      search,
      filter,
      sort
    } = req.query

    const limit = parseInt(pageSize)
    const offset = (parseInt(page) - 1) * limit

    // 构建查询条件
    const where = {}
    if (categoryId) where.category_id = categoryId
    if (filter === 'recommend') where.is_recommend = 1
    if (filter === 'hot') where.is_hot = 1
    if (search) {
      where[Op.or] = [
        { title: { [Op.like]: `%${search}%` } },
        { description: { [Op.like]: `%${search}%` } }
      ]
    }

    // 排序映射
    let order = [['created_at', 'DESC']]
    if (sort === 'latest') order = [['created_at', 'DESC']]
    else if (sort === 'hot') order = [['like_count', 'DESC']]
    else if (sort === 'participants') order = [['participant_count', 'DESC']]
    else if (sort === 'recommend') order = [['is_recommend', 'DESC'], ['like_count', 'DESC']]

    // 查询项目
    const { count, rows } = await Project.findAndCountAll({
      where,
      include: [
        { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
        { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
      ],
      order,
      limit,
      offset,
      distinct: true
    })

    res.json({
      code: 200,
      message: '获取项目列表成功',
      data: {
        projects: rows.map(toClientProject),
        total: count,
        page: parseInt(page),
        pageSize: limit
      }
    })
  } catch (error) {
    console.error('获取项目列表错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 获取项目详情
exports.getProjectById = async (req, res) => {
  try {
    const { id } = req.params

    const project = await Project.findByPk(id, {
      include: [
        { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
        { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
      ]
    })

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    res.json({
      code: 200,
      message: '获取项目详情成功',
      data: toClientProject(project)
    })
  } catch (error) {
    console.error('获取项目详情错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 创建项目
exports.createProject = async (req, res) => {
  try {
    const { title, description, cover_image, coverImage, category_id, categoryId, tags } = req.body
    const creator_id = req.user.userId

    if (!title || !description) {
      return res.status(400).json({
        code: 400,
        message: '标题和描述为必填项'
      })
    }

    // 创建项目（tags 存入 projects.tags JSON 列；兼容 snake/camel 入参）
    const project = await Project.create({
      title,
      description,
      cover_image: cover_image || coverImage || null,
      category_id: category_id || categoryId || null,
      creator_id,
      tags: tags || []
    })

    // 添加创建者为参与者
    await require('../models/ProjectParticipant').create({
      project_id: project.id,
      user_id: creator_id,
      role: 'creator'
    })

    res.status(201).json({
      code: 200,
      message: '项目创建成功',
      data: toClientProject(project)
    })
  } catch (error) {
    console.error('创建项目错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 更新项目
exports.updateProject = async (req, res) => {
  try {
    const { id } = req.params
    const { title, description, cover_image, category_id } = req.body
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    // 验证权限
    if (project.creator_id !== userId) {
      return res.status(403).json({
        code: 403,
        message: '无权修改此项目'
      })
    }

    // 更新字段
    if (title) project.title = title
    if (description) project.description = description
    if (cover_image) project.cover_image = cover_image
    if (category_id) project.category_id = category_id

    await project.save()

    res.json({
      code: 200,
      message: '项目更新成功',
      data: toClientProject(project)
    })
  } catch (error) {
    console.error('更新项目错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 删除项目
exports.deleteProject = async (req, res) => {
  try {
    const { id } = req.params
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    // 验证权限
    if (project.creator_id !== userId) {
      return res.status(403).json({
        code: 403,
        message: '无权删除此项目'
      })
    }

    await project.destroy()

    res.json({
      code: 200,
      message: '项目删除成功'
    })
  } catch (error) {
    console.error('删除项目错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 点赞项目（project_likes 判重，防止重复点赞无限累加）
exports.likeProject = async (req, res) => {
  try {
    const { id } = req.params
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    const sequelize = require('../config/database')
    const [existing] = await sequelize.query(
      'SELECT id FROM project_likes WHERE project_id = ? AND user_id = ? LIMIT 1',
      { replacements: [id, userId] }
    )

    if (existing.length > 0) {
      return res.status(400).json({
        code: 400,
        message: '已点赞过该项目'
      })
    }

    await sequelize.query(
      'INSERT INTO project_likes (project_id, user_id) VALUES (?, ?)',
      { replacements: [id, userId] }
    )
    project.like_count += 1
    await project.save()

    res.json({
      code: 200,
      message: '点赞成功',
      data: { likeCount: project.like_count }
    })
  } catch (error) {
    console.error('点赞项目错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 取消点赞
exports.unlikeProject = async (req, res) => {
  try {
    const { id } = req.params
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    const sequelize = require('../config/database')
    const [existing] = await sequelize.query(
      'SELECT id FROM project_likes WHERE project_id = ? AND user_id = ? LIMIT 1',
      { replacements: [id, userId] }
    )

    if (existing.length === 0) {
      return res.status(400).json({
        code: 400,
        message: '尚未点赞该项目'
      })
    }

    await sequelize.query(
      'DELETE FROM project_likes WHERE project_id = ? AND user_id = ?',
      { replacements: [id, userId] }
    )
    if (project.like_count > 0) {
      project.like_count -= 1
      await project.save()
    }

    res.json({
      code: 200,
      message: '已取消点赞',
      data: { likeCount: project.like_count }
    })
  } catch (error) {
    console.error('取消点赞错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 参与项目
exports.participateProject = async (req, res) => {
  try {
    const { id } = req.params
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    // 检查是否已参与
    const ProjectParticipant = require('../models/ProjectParticipant')
    const existingParticipant = await ProjectParticipant.findOne({
      where: { project_id: id, user_id: userId }
    })

    if (existingParticipant) {
      return res.status(400).json({
        code: 400,
        message: '已参与此项目'
      })
    }

    // 添加参与者
    await ProjectParticipant.create({
      project_id: id,
      user_id: userId,
      role: 'member'
    })

    // 更新参与人数
    project.participant_count += 1
    await project.save()

    res.json({
      code: 200,
      message: '参与成功',
      data: { participantCount: project.participant_count }
    })
  } catch (error) {
    console.error('参与项目错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}

// 取消参与
exports.cancelParticipate = async (req, res) => {
  try {
    const { id } = req.params
    const userId = req.user.userId

    const project = await Project.findByPk(id)

    if (!project) {
      return res.status(404).json({
        code: 404,
        message: '项目不存在'
      })
    }

    const ProjectParticipant = require('../models/ProjectParticipant')
    const participant = await ProjectParticipant.findOne({
      where: { project_id: id, user_id: userId }
    })

    if (!participant) {
      return res.status(400).json({
        code: 400,
        message: '未参与此项目'
      })
    }

    await participant.destroy()

    if (project.participant_count > 0) {
      project.participant_count -= 1
      await project.save()
    }

    res.json({
      code: 200,
      message: '已取消参与',
      data: { participantCount: project.participant_count }
    })
  } catch (error) {
    console.error('取消参与错误:', error)
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    })
  }
}
