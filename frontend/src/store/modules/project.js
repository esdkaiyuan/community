import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProjects, getProjectById, createProject, likeProject, unlikeProject, participateProject, cancelParticipate } from '@/api/project'

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
      throw error
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
