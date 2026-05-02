<template>
  <header class="header">
    <div class="header-container">
      <!-- Logo -->
      <div class="logo" @click="goHome">
        <div class="logo-icon">
          <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="20" cy="20" r="18" fill="#5B6AF0" opacity="0.1"/>
            <path d="M12 15C12 13.8954 12.8954 13 14 13H18C19.1046 13 20 13.8954 20 15V19C20 20.1046 19.1046 21 18 21H14C12.8954 21 12 20.1046 12 19V15Z" fill="#5B6AF0"/>
            <path d="M20 15C20 13.8954 20.8954 13 22 13H26C27.1046 13 28 13.8954 28 15V19C28 20.1046 27.1046 21 26 21H22C20.8954 21 20 20.1046 20 19V15Z" fill="#FF8C42"/>
            <path d="M12 23C12 21.8954 12.8954 21 14 21H18C19.1046 21 20 21.8954 20 23V27C20 28.1046 19.1046 29 18 29H14C12.8954 29 12 28.1046 12 27V23Z" fill="#36D1DC"/>
            <path d="M20 23C20 21.8954 20.8954 21 22 21H26C27.1046 21 28 21.8954 28 23V27C28 28.1046 27.1046 29 26 29H22C20.8954 29 20 28.1046 20 27V23Z" fill="#5B6AF0"/>
          </svg>
        </div>
        <div class="logo-text">
          <h1>共创社区</h1>
          <p>一起想，一起做</p>
        </div>
      </div>

      <!-- 搜索框 -->
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索项目、技术、标签或用户"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #suffix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 用户操作区 -->
      <div class="user-actions">
        <template v-if="!isLoggedIn">
          <el-button plain @click="goLogin">登录</el-button>
          <el-button type="primary" @click="goRegister">注册</el-button>
        </template>
        <template v-else>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :src="userInfo?.avatar">
                {{ userInfo?.username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <span class="username">{{ userInfo?.username }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="publish">发布项目</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { storeToRefs } from 'pinia'
import { Search, ArrowDown } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const { isLoggedIn, userInfo } = storeToRefs(userStore)

const searchKeyword = ref('')

// 返回首页
const goHome = () => {
  router.push('/')
}

// 去登录页
const goLogin = () => {
  router.push('/login')
}

// 去注册页
const goRegister = () => {
  router.push('/register')
}

// 搜索
const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    router.push({ path: '/', query: { search: searchKeyword.value.trim() } })
  }
}

// 下拉菜单命令处理
const handleCommand = (command) => {
  if (command === 'publish') {
    router.push('/publish')
  } else if (command === 'logout') {
    userStore.logout()
    router.push('/')
  }
}
</script>

<style lang="scss" scoped>
.header {
  background: #fff;
  border-bottom: 1px solid #E4E7ED;
  position: sticky;
  top: 0;
  z-index: 1000;

  .header-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 12px 24px;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 40px;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    justify-self: start;

    .logo-icon {
      width: 40px;
      height: 40px;
    }

    .logo-text {
      h1 {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
        margin: 0;
        line-height: 1.2;
      }

      p {
        font-size: 12px;
        color: #909399;
        margin: 0;
        line-height: 1.2;
      }
    }
  }

  .search-box {
    justify-self: center;
    width: 100%;
    max-width: 800px;

    :deep(.el-input) {
      .el-input__wrapper {
        border-radius: 20px;
        background-color: #F5F7FA;
        box-shadow: none;
        border: 1px solid #E4E7ED;
        
        &:hover,
        &.is-focus {
          box-shadow: 0 0 0 1px #5B6AF0 inset;
        }
      }
    }
  }

  .user-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    justify-self: end;

    :deep(.el-button) {
      border-radius: 6px;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background-color 0.3s;

      &:hover {
        background-color: #F5F7FA;
      }

      .username {
        font-size: 14px;
        color: #303133;
      }
    }
  }
}

// 响应式适配
@media (max-width: 1024px) {
  .header {
    .header-container {
      gap: 20px;
    }

    .search-box {
      max-width: 500px;
    }
  }
}

@media (max-width: 768px) {
  .header {
    .header-container {
      padding: 12px 16px;
      gap: 12px;
      grid-template-columns: auto 1fr auto;
    }

    .logo-text {
      p {
        display: none;
      }

      h1 {
        font-size: 16px;
      }
    }

    .logo-icon {
      width: 32px;
      height: 32px;
    }

    .search-box {
      max-width: none;

      :deep(.el-input__inner) {
        font-size: 14px;
      }
    }

    .user-actions {
      gap: 8px;

      :deep(.el-button) {
        padding: 8px 12px;
        font-size: 13px;
      }
    }
  }
}

@media (max-width: 480px) {
  .header {
    .header-container {
      padding: 8px 12px;
      gap: 8px;
    }

    .logo-text {
      display: none;
    }

    .search-box {
      :deep(.el-input__wrapper) {
        padding: 0 12px;
      }
    }

    .user-actions {
      :deep(.el-button) {
        padding: 6px 10px;
        font-size: 12px;
      }
    }
  }
}
</style>
