<template>
  <div class="captcha-container">
    <canvas 
      ref="canvasRef" 
      :width="width" 
      :height="height"
      @click="refreshCaptcha"
      title="点击刷新验证码"
    ></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  width: {
    type: Number,
    default: 120
  },
  height: {
    type: Number,
    default: 40
  },
  length: {
    type: Number,
    default: 4
  }
})

const emit = defineEmits(['update:code'])

const canvasRef = ref(null)
const code = ref('')

// 生成随机颜色
const randomColor = (min, max) => {
  const r = Math.floor(Math.random() * (max - min) + min)
  const g = Math.floor(Math.random() * (max - min) + min)
  const b = Math.floor(Math.random() * (max - min) + min)
  return `rgb(${r},${g},${b})`
}

// 生成随机字符（排除容易混淆的字符）
const randomChar = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  return chars[Math.floor(Math.random() * chars.length)]
}

// 绘制干扰线
const drawLine = (ctx) => {
  for (let i = 0; i < 3; i++) {
    ctx.beginPath()
    ctx.moveTo(Math.random() * props.width, Math.random() * props.height)
    ctx.lineTo(Math.random() * props.width, Math.random() * props.height)
    ctx.strokeStyle = randomColor(180, 220)
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

// 绘制干扰点
const drawDot = (ctx) => {
  for (let i = 0; i < 30; i++) {
    ctx.beginPath()
    ctx.arc(
      Math.random() * props.width,
      Math.random() * props.height,
      1,
      0,
      2 * Math.PI
    )
    ctx.fillStyle = randomColor(150, 200)
    ctx.fill()
  }
}

// 生成验证码
const generateCaptcha = () => {
  if (!canvasRef.value) return

  const ctx = canvasRef.value.getContext('2d')
  
  // 清空画布
  ctx.clearRect(0, 0, props.width, props.height)
  
  // 绘制背景
  ctx.fillStyle = '#f5f7fa'
  ctx.fillRect(0, 0, props.width, props.height)

  // 生成验证码文本
  let captchaText = ''
  for (let i = 0; i < props.length; i++) {
    captchaText += randomChar()
  }
  code.value = captchaText

  // 绘制文字
  const fontSize = props.height * 0.6
  ctx.font = `${fontSize}px Arial`
  ctx.textBaseline = 'middle'

  const charWidth = props.width / (props.length + 1)
  for (let i = 0; i < captchaText.length; i++) {
    const x = charWidth * (i + 1)
    const y = props.height / 2
    
    // 随机旋转角度
    const angle = (Math.random() - 0.5) * 0.4
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    
    // 随机颜色
    ctx.fillStyle = randomColor(50, 150)
    ctx.fillText(captchaText[i], 0, 0)
    
    ctx.restore()
  }

  // 绘制干扰线和点
  drawLine(ctx)
  drawDot(ctx)

  // 通知父组件
  emit('update:code', code.value)
}

// 刷新验证码
const refreshCaptcha = () => {
  generateCaptcha()
}

// 暴露方法给父组件
defineExpose({
  refreshCaptcha,
  getCode: () => code.value
})

// 组件挂载时生成
onMounted(() => {
  generateCaptcha()
})

// 监听尺寸变化
watch([() => props.width, () => props.height], () => {
  generateCaptcha()
})
</script>

<style lang="scss" scoped>
.captcha-container {
  display: inline-block;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    opacity: 0.8;
  }

  canvas {
    display: block;
    border: 1px solid #DCDFE6;
    border-radius: 4px;
  }
}
</style>
