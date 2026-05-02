<template>
  <div class="project-card" @click="goToDetail">
    <!-- 项目封面 -->
    <div class="card-cover">
      <img v-if="project.coverImage" :src="project.coverImage" :alt="project.title" />
      <div v-else class="default-cover">
        <el-icon><Document /></el-icon>
      </div>
      <el-tag class="category-tag" size="small">
        {{ project.categoryName || '未分类' }}
      </el-tag>
    </div>

    <!-- 项目信息 -->
    <div class="card-content">
      <h3 class="card-title">{{ project.title }}</h3>
      <p class="card-description">{{ project.description }}</p>

      <!-- 项目元信息 -->
      <div class="card-meta">
        <div class="meta-item">
          <el-icon><User /></el-icon>
          <span>{{ project.participantCount || 0 }} 人参与</span>
        </div>
        <div class="meta-item">
          <el-icon @click.stop="handleLike"><Star /></el-icon>
          <span>{{ project.likeCount || 0 }}</span>
        </div>
      </div>

      <!-- 项目创建者 -->
      <div class="card-footer">
        <el-avatar :size="24" :src="project.creator?.avatar">
          {{ project.creator?.username?.charAt(0)?.toUpperCase() }}
        </el-avatar>
        <span class="creator-name">{{ project.creator?.username || '匿名用户' }}</span>
        <span class="create-time">{{ formatTime(project.createdAt) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Document, User, Star } from '@element-plus/icons-vue'

const props = defineProps({
  project: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['like'])

const router = useRouter()

// 跳转到项目详情
const goToDetail = () => {
  router.push(`/project/${props.project.id}`)
}

// 处理点赞
const handleLike = () => {
  emit('like', props.project.id)
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  // 小于1天
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  // 小于7天
  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`
  }
  
  // 超过7天显示具体日期
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
</script>

<style lang="scss" scoped>
.project-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
  cursor: pointer;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .card-cover {
    position: relative;
    width: 100%;
    height: 180px;
    overflow: hidden;
    background: #f5f7fa;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s;
    }

    &:hover img {
      transform: scale(1.05);
    }

    .default-cover {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 48px;
      color: #c0c4cc;
    }

    .category-tag {
      position: absolute;
      top: 12px;
      left: 12px;
    }
  }

  .card-content {
    padding: 16px;

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 8px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      line-height: 1.5;
      height: 48px;
    }

    .card-description {
      font-size: 14px;
      color: #909399;
      margin: 0 0 12px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      line-height: 1.6;
      height: 45px;
    }

    .card-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid #f0f0f0;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: #909399;

        .el-icon {
          font-size: 16px;
        }

        &:last-child {
          .el-icon {
            cursor: pointer;
            transition: color 0.3s;

            &:hover {
              color: #e6a23c;
            }
          }
        }
      }
    }

    .card-footer {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #c0c4cc;

      .creator-name {
        flex: 1;
        color: #606266;
      }

      .create-time {
        white-space: nowrap;
      }
    }
  }
}
</style>
