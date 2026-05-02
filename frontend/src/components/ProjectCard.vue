<template>
  <div class="project-card" @click="goToDetail">
    <!-- 项目封面 -->
    <div class="card-cover">
      <img v-if="project.coverImage" :src="project.coverImage" :alt="project.title" />
      <div v-else class="default-cover">
        <el-icon><Picture /></el-icon>
      </div>
      <!-- 推荐/热门标签 -->
      <div v-if="project.isRecommend" class="badge recommend">
        <el-icon><Star /></el-icon>
        <span>推荐</span>
      </div>
      <div v-else-if="project.isHot" class="badge hot">
        <el-icon><Fire /></el-icon>
        <span>热门</span>
      </div>
    </div>

    <!-- 项目信息 -->
    <div class="card-content">
      <h3 class="card-title">{{ project.title }}</h3>
      <p class="card-description">{{ project.description }}</p>

      <!-- 标签 -->
      <div class="card-tags">
        <el-tag
          v-for="tag in project.tags"
          :key="tag"
          size="small"
          type="info"
          effect="plain"
        >
          # {{ tag }}
        </el-tag>
      </div>

      <!-- 底部信息 -->
      <div class="card-footer">
        <div class="footer-left">
          <el-avatar :size="24" :src="project.creator?.avatar">
            {{ project.creator?.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span class="participants">
            <el-icon><UserFilled /></el-icon>
            {{ project.participantCount || 0 }} 人参与
          </span>
        </div>
        <div class="footer-right">
          <span class="like-count" @click.stop="handleLike">
            <el-icon><StarFilled /></el-icon>
            {{ project.likeCount || 0 }}
          </span>
          <span class="comment-count">
            <el-icon><ChatDotRound /></el-icon>
            {{ project.commentCount || 0 }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import {
  Picture,
  Star,
  Fire,
  UserFilled,
  StarFilled,
  ChatDotRound
} from '@element-plus/icons-vue'

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
</script>

<style lang="scss" scoped>
.project-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;

  &:hover {
    transform: translateY(-6px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);

    .card-cover img {
      transform: scale(1.08);
    }
  }

  .card-cover {
    position: relative;
    width: 100%;
    height: 200px;
    overflow: hidden;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .default-cover {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 64px;
      color: rgba(255, 255, 255, 0.6);
    }

    .badge {
      position: absolute;
      top: 12px;
      left: 12px;
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      color: #fff;
      backdrop-filter: blur(10px);

      &.recommend {
        background: rgba(102, 126, 234, 0.9);
      }

      &.hot {
        background: rgba(255, 140, 66, 0.9);
      }

      .el-icon {
        font-size: 14px;
      }
    }
  }

  .card-content {
    padding: 20px;

    .card-title {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 12px 0;
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .card-description {
      font-size: 14px;
      color: #909399;
      margin: 0 0 16px 0;
      line-height: 1.6;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      min-height: 45px;
    }

    .card-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;

      .el-tag {
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 12px;
        background: #f5f7fa;
        color: #606266;
        border: none;
      }
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 16px;
      border-top: 1px solid #f0f0f0;

      .footer-left {
        display: flex;
        align-items: center;
        gap: 8px;

        .participants {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: #909399;

          .el-icon {
            font-size: 16px;
          }
        }
      }

      .footer-right {
        display: flex;
        align-items: center;
        gap: 16px;

        .like-count,
        .comment-count {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: #909399;
          cursor: pointer;
          transition: color 0.3s;

          &:hover {
            color: #667eea;
          }

          .el-icon {
            font-size: 16px;
          }
        }

        .like-count:hover {
          color: #ff8c42;
        }
      }
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .project-card {
    .card-cover {
      height: 160px;
    }

    .card-content {
      padding: 16px;

      .card-title {
        font-size: 16px;
      }
    }
  }
}
</style>
