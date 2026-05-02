import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProjects, getProjectById, createProject, likeProject, unlikeProject, participateProject, cancelParticipate } from '@/api/project'
import { mockProjects } from '@/utils/mockData'

export const useProjectStore = defineStore('project', () => {
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const total = ref(0)

  // 获取项目列表
  async function fetchProjects(params = {}) {
    loading.value = true
    try {
      const res = await getProjects(params)
      projects.value = res.data.projects
      total.value = res.data.total
      return res
    } catch (error) {
      console.warn('获取项目列表失败，使用模拟数据', error)
      // 使用模拟数据
      let filteredProjects = [...mockProjects]
      
      // 根据筛选条件过滤
      if (params.categoryId) {
        const categoryMap = {
          1: '技术开发',
          2: '设计创意',
          3: '产品/运营',
          4: '内容创作',
          5: '硬件/物联网',
          6: '研究学习',
          7: '开源专区',
          8: '公益/社会创新'
        }
        const categoryName = categoryMap[params.categoryId]
        if (categoryName) {
          filteredProjects = filteredProjects.filter(p => p.categoryName === categoryName)
        }
      }
      
      if (params.filter === 'recommend') {
        filteredProjects = filteredProjects.filter(p => p.isRecommend)
      } else if (params.filter === 'hot') {
        filteredProjects = filteredProjects.filter(p => p.isHot)
      }
      
      // 排序
      if (params.sort === 'latest') {
        filteredProjects.sort((a, b) => b.id - a.id)
      } else if (params.sort === 'hot') {
        filteredProjects.sort((a, b) => b.likeCount - a.likeCount)
      } else if (params.sort === 'participants') {
        filteredProjects.sort((a, b) => b.participantCount - a.participantCount)
      }
      
      // 分页
      const page = params.page || 1
      const pageSize = params.pageSize || 12
      const start = (page - 1) * pageSize
      const end = start + pageSize
      
      projects.value = filteredProjects.slice(start, end)
      total.value = filteredProjects.length
      
      return { data: { projects: projects.value, total: total.value } }
    } finally {
      loading.value = false
    }
  }

  // 获取项目详情
  async function fetchProjectById(id) {
    loading.value = true
    try {
      const res = await getProjectById(id)
      currentProject.value = res.data
      return res
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  // 创建项目
  async function createNewProject(projectData) {
    try {
      const res = await createProject(projectData)
      return res
    } catch (error) {
      throw error
    }
  }

  // 点赞项目
  async function likeProjectAction(id) {
    try {
      const res = await likeProject(id)
      // 更新本地状态
      if (currentProject.value && currentProject.value.id === id) {
        currentProject.value.isLiked = true
        currentProject.value.likeCount++
      }
      return res
    } catch (error) {
      throw error
    }
  }

  // 取消点赞
  async function unlikeProjectAction(id) {
    try {
      const res = await unlikeProject(id)
      // 更新本地状态
      if (currentProject.value && currentProject.value.id === id) {
        currentProject.value.isLiked = false
        currentProject.value.likeCount--
      }
      return res
    } catch (error) {
      throw error
    }
  }

  // 参与项目
  async function participateProjectAction(id) {
    try {
      const res = await participateProject(id)
      // 更新本地状态
      if (currentProject.value && currentProject.value.id === id) {
        currentProject.value.isParticipated = true
        currentProject.value.participantCount++
      }
      return res
    } catch (error) {
      throw error
    }
  }

  // 取消参与
  async function cancelParticipateAction(id) {
    try {
      const res = await cancelParticipate(id)
      // 更新本地状态
      if (currentProject.value && currentProject.value.id === id) {
        currentProject.value.isParticipated = false
        currentProject.value.participantCount--
      }
      return res
    } catch (error) {
      throw error
    }
  }

  // 重置当前项目
  function resetCurrentProject() {
    currentProject.value = null
  }

  return {
    projects,
    currentProject,
    loading,
    total,
    fetchProjects,
    fetchProjectById,
    createNewProject,
    likeProjectAction,
    unlikeProjectAction,
    participateProjectAction,
    cancelParticipateAction,
    resetCurrentProject
  }
})
