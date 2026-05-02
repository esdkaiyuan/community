<template>
  <header class="header">
    <div class="header-container">
      <!-- Logo -->
      <div class="logo" @click="goHome">
        <h1>共创社区</h1>
      </div>

      <!-- 搜索框 -->
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索项目..."
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 用户操作区 -->
      <div class="user-actions">
        <template v-if="!isLoggedIn">
          <el-button type="primary" @click="goLogin">登录</el-button>
          <el-button @click="goRegister">注册</el-button>
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 1000;

  .header-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .logo {
    cursor: pointer;
    h1 {
      font-size: 24px;
      font-weight: 600;
      color: #409eff;
      margin: 0;
      white-space: nowrap;
    }
  }

  .search-box {
    flex: 1;
    max-width: 500px;

    :deep(.el-input) {
      .el-input__wrapper {
        border-radius: 20px;
      }
    }
  }

  .user-actions {
    display: flex;
    align-items: center;
    gap: 12px;

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: background-color 0.3s;

      &:hover {
        background-color: #f5f7fa;
      }

      .username {
        font-size: 14px;
        color: #303133;
      }
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .header {
    .header-container {
      padding: 12px 16px;
      gap: 12px;
    }

    .logo h1 {
      font-size: 20px;
    }

    .search-box {
      display: none;
    }
  }
}
</style>
