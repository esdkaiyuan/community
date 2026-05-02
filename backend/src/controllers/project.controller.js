const { Project, Category, User, Tag, ProjectTag } = require('../models')
const { Op } = require('sequelize')

// 获取项目列表（支持分页、筛选、搜索）
exports.getProjects = async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 12, 
      categoryId, 
      keyword, 
      sortBy = 'created_at', 
      sortOrder = 'DESC' 
    } = req.query
    
    const offset = (page - 1) * limit
    
    // 构建查询条件
    const where = {}
    if (categoryId) where.category_id = categoryId
    if (keyword) {
      where[Op.or] = [
        { title: { [Op.like]: `%${keyword}%` } },
        { description: { [Op.like]: `%${keyword}%` } }
      ]
    }
    
    // 查询项目
    const { count, rows } = await Project.findAndCountAll({
      where,
      include: [
        { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
        { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
      ],
      order: [[sortBy, sortOrder]],
      limit: parseInt(limit),
      offset,
      distinct: true
    })
    
    res.json({
      success: true,
      data: {
        projects: rows,
        pagination: {
          total: count,
          page: parseInt(page),
          limit: parseInt(limit),
          totalPages: Math.ceil(count / limit)
        }
      }
    })
  } catch (error) {
    console.error('获取项目列表错误:', error)
    res.status(500).json({ 
      success: false, 
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
        success: false, 
        message: '项目不存在' 
      })
    }
    
    res.json({
      success: true,
      data: { project }
    })
  } catch (error) {
    console.error('获取项目详情错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

// 创建项目
exports.createProject = async (req, res) => {
  try {
    const { title, description, cover_image, category_id, tags } = req.body
    const creator_id = req.user.userId
    
    if (!title || !description) {
      return res.status(400).json({ 
        success: false, 
        message: '标题和描述为必填项' 
      })
    }
    
    // 创建项目
    const project = await Project.create({
      title,
      description,
      cover_image,
      category_id,
      creator_id
    })
    
    // 添加标签
    if (tags && tags.length > 0) {
      const tagInstances = await Tag.findAll({ where: { name: tags } })
      await project.setTags(tagInstances)
    }
    
    // 添加创建者为参与者
    await require('../models/ProjectParticipant').create({
      project_id: project.id,
      user_id: creator_id,
      role: 'creator'
    })
    
    res.status(201).json({
      success: true,
      message: '项目创建成功',
      data: { project }
    })
  } catch (error) {
    console.error('创建项目错误:', error)
    res.status(500).json({ 
      success: false, 
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
        success: false, 
        message: '项目不存在' 
      })
    }
    
    // 验证权限
    if (project.creator_id !== userId) {
      return res.status(403).json({ 
        success: false, 
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
      success: true,
      message: '项目更新成功',
      data: { project }
    })
  } catch (error) {
    console.error('更新项目错误:', error)
    res.status(500).json({ 
      success: false, 
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
        success: false, 
        message: '项目不存在' 
      })
    }
    
    // 验证权限
    if (project.creator_id !== userId) {
      return res.status(403).json({ 
        success: false, 
        message: '无权删除此项目' 
      })
    }
    
    await project.destroy()
    
    res.json({
      success: true,
      message: '项目删除成功'
    })
  } catch (error) {
    console.error('删除项目错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

// 点赞项目
exports.likeProject = async (req, res) => {
  try {
    const { id } = req.params
    
    const project = await Project.findByPk(id)
    
    if (!project) {
      return res.status(404).json({ 
        success: false, 
        message: '项目不存在' 
      })
    }
    
    project.likes_count += 1
    await project.save()
    
    res.json({
      success: true,
      message: '点赞成功',
      data: { likes_count: project.likes_count }
    })
  } catch (error) {
    console.error('点赞项目错误:', error)
    res.status(500).json({ 
      success: false, 
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
        success: false, 
        message: '项目不存在' 
      })
    }
    
    // 检查是否已参与
    const existingParticipant = await require('../models/ProjectParticipant').findOne({
      where: { project_id: id, user_id: userId }
    })
    
    if (existingParticipant) {
      return res.status(400).json({ 
        success: false, 
        message: '已参与此项目' 
      })
    }
    
    // 添加参与者
    await require('../models/ProjectParticipant').create({
      project_id: id,
      user_id: userId,
      role: 'member'
    })
    
    // 更新参与人数
    project.participants_count += 1
    await project.save()
    
    res.json({
      success: true,
      message: '参与成功',
      data: { participants_count: project.participants_count }
    })
  } catch (error) {
    console.error('参与项目错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}
