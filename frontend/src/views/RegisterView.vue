<template>
  <div class="register-view">
    <Header />
    <div class="register-container">
      <el-card class="register-card">
        <h2>用户注册</h2>
        <el-form :model="registerForm" :rules="rules" ref="formRef">
          <el-form-item prop="username">
            <el-input v-model="registerForm.username" placeholder="用户名" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="email">
            <el-input v-model="registerForm.email" placeholder="邮箱" prefix-icon="Message" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="registerForm.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" prefix-icon="Lock" show-password />
          </el-form-item>
          
          <!-- 图形验证码 -->
          <el-form-item prop="captcha">
            <div class="captcha-wrapper">
              <el-input 
                v-model="registerForm.captcha" 
                placeholder="请输入验证码" 
                prefix-icon="Key"
                style="flex: 1;"
              />
              <div class="captcha-image" @click="refreshCaptcha" title="点击刷新验证码">
                <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
                <span v-else>加载中...</span>
              </div>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleRegister" :loading="loading" style="width: 100%">
              注册
            </el-button>
          </el-form-item>
          <div class="login-link">
            已有账号？<router-link to="/login">立即登录</router-link>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { ElMessage } from 'element-plus'
import svgCaptcha from 'svg-captcha'
import Header from '@/components/Header.vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const captchaImage = ref('')
const captchaCode = ref('')

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  captcha: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateCaptcha = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入验证码'))
  } else if (value.toLowerCase() !== captchaCode.value.toLowerCase()) {
    callback(new Error('验证码错误'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在2-20个字符之间', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  captcha: [
    { required: true, validator: validateCaptcha, trigger: 'blur' }
  ]
}

// 生成验证码
const generateCaptcha = () => {
  const captcha = svgCaptcha.create({
    size: 4,
    ignoreChars: '0oO1lIi',
    noise: 3,
    color: true,
    background: '#f5f7fa',
    width: 120,
    height: 40
  })
  captchaImage.value = `data:image/svg+xml;base64,${Buffer.from(captcha.data).toString('base64')}`
  captchaCode.value = captcha.text
}

// 刷新验证码
const refreshCaptcha = () => {
  generateCaptcha()
  registerForm.captcha = ''
}

const handleRegister = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const { confirmPassword, captcha, ...data } = registerForm
        await userStore.register(data)
        ElMessage.success('注册成功，请登录')
        router.push('/login')
      } catch (error) {
        console.error('注册失败:', error)
        // 注册失败后刷新验证码
        refreshCaptcha()
      } finally {
        loading.value = false
      }
    }
  })
}

// 组件挂载时生成验证码
onMounted(() => {
  generateCaptcha()
})
</script>

<style lang="scss" scoped>
.register-view {
  min-height: 100vh;
  background-color: #f5f7fa;

  .register-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 40px 20px;
    min-height: calc(100vh - 80px);

    .register-card {
      width: 100%;
      max-width: 400px;
      padding: 20px;

      h2 {
        text-align: center;
        margin-bottom: 30px;
        color: #303133;
      }

      .login-link {
        text-align: center;
        font-size: 14px;
        color: #909399;

        a {
          color: #409eff;
          text-decoration: none;

          &:hover {
            text-decoration: underline;
          }
        }
      }

      .captcha-wrapper {
        display: flex;
        gap: 12px;
        align-items: center;

        .captcha-image {
          width: 120px;
          height: 40px;
          border: 1px solid #DCDFE6;
          border-radius: 4px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f5f7fa;
          transition: all 0.3s;

          &:hover {
            border-color: #409eff;
            box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
          }

          img {
            width: 100%;
            height: 100%;
            object-fit: contain;
          }

          span {
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .register-view {
    .register-container {
      padding: 20px 16px;

      .register-card {
        .captcha-wrapper {
          .captcha-image {
            width: 100px;
            height: 36px;
          }
        }
      }
    }
  }
}

@media (max-width: 480px) {
  .register-view {
    .register-container {
      .register-card {
        .captcha-wrapper {
          flex-direction: column;
          gap: 8px;

          .el-input {
            width: 100%;
          }

          .captcha-image {
            width: 100%;
            height: 40px;
          }
        }
      }
    }
  }
}
</style>
