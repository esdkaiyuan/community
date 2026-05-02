<template>
  <div class="publish-project-view">
    <Header />
    <div class="publish-container">
      <el-card class="publish-card">
        <h2>发布项目</h2>
        <el-form :model="projectForm" :rules="rules" ref="formRef" label-width="100px">
          <el-form-item label="项目名称" prop="title">
            <el-input v-model="projectForm.title" placeholder="请输入项目名称" />
          </el-form-item>
          <el-form-item label="项目描述" prop="description">
            <el-input
              v-model="projectForm.description"
              type="textarea"
              :rows="5"
              placeholder="请输入项目描述"
            />
          </el-form-item>
          <el-form-item label="项目分类" prop="categoryId">
            <el-select v-model="projectForm.categoryId" placeholder="请选择分类" style="width: 100%">
              <el-option
                v-for="category in categories"
                :key="category.id"
                :label="category.name"
                :value="category.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handlePublish" :loading="loading">
              发布项目
            </el-button>
            <el-button @click="handleCancel">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/store/modules/project'
import { useCategoryStore } from '@/store/modules/category'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import Header from '@/components/Header.vue'

const router = useRouter()
const projectStore = useProjectStore()
const categoryStore = useCategoryStore()
const { categories } = storeToRefs(categoryStore)

const formRef = ref(null)
const loading = ref(false)

const projectForm = reactive({
  title: '',
  description: '',
  categoryId: null
})

const rules = {
  title: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 100, message: '项目名称长度在2-100个字符之间', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入项目描述', trigger: 'blur' },
    { min: 10, message: '项目描述不能少于10个字符', trigger: 'blur' }
  ],
  categoryId: [
    { required: true, message: '请选择项目分类', trigger: 'change' }
  ]
}

// 加载分类列表
onMounted(async () => {
  if (categories.value.length === 0) {
    await categoryStore.fetchCategories()
  }
})

const handlePublish = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await projectStore.createNewProject(projectForm)
        ElMessage.success('项目发布成功')
        router.push('/')
      } catch (error) {
        console.error('发布失败:', error)
      } finally {
        loading.value = false
      }
    }
  })
}

const handleCancel = () => {
  router.back()
}
</script>

<style lang="scss" scoped>
.publish-project-view {
  min-height: 100vh;
  background-color: #f5f7fa;

  .publish-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 40px 24px;

    .publish-card {
      padding: 32px;

      h2 {
        text-align: center;
        margin-bottom: 32px;
        color: #303133;
      }
    }
  }
}
</style>
