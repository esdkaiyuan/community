<template>
  <!--
    Apple HIG 模态表单（Sheet / Modal Card）

    桌面：居中卡片（macOS 的 modal card），窄屏：底部升起（iOS 的 sheet + grabber）。
    同一个组件两种呈现，是因为手势语义不同——手机上从底部升起的面板天然暗示
    「向下滑可关」，居中浮层在小屏上反而没有可推断的关闭方向。

    三条 HIG 硬约束：
      1. 打开时锁滚动，否则背景跟着动，模态层级立刻崩塌；
      2. Esc 关闭 + 焦点收进面板（关闭后归还给触发元素）——纯键盘用户不会掉进死胡同；
      3. 点遮罩关闭，但**不**点面板内容关闭（@click.self 只认遮罩本身）。
  -->
  <Teleport to="body">
    <transition name="sheet">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[90] flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center sm:p-4"
        @click.self="close"
      >
        <div
          ref="panel"
          class="relative w-full max-w-md animate-sheet-up rounded-t-22 bg-cream shadow-pop sm:animate-none sm:rounded-22"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
          :data-test="testId"
        >
          <!-- grabber：iOS sheet 顶部的横条，暗示「可下拉关闭」，只在窄屏有意义 -->
          <div class="flex justify-center pt-2.5 sm:hidden" aria-hidden="true">
            <span class="h-1 w-9 rounded-full bg-line-strong/60"></span>
          </div>

          <!-- 头 -->
          <div class="flex items-start gap-3 px-5 pb-3 pt-4 sm:px-6 sm:pt-5">
            <div class="min-w-0 flex-1">
              <h3 class="text-title3 font-semibold text-ink">{{ title }}</h3>
              <p v-if="message" class="mt-1 text-footnote leading-relaxed text-ink-mid">{{ message }}</p>
            </div>
            <button
              type="button"
              class="-mr-1.5 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink-dim transition-colors hover:bg-sand hover:text-ink"
              aria-label="关闭"
              @click="close"
            >
              <AppIcon name="x" class="h-4 w-4" />
            </button>
          </div>

          <!-- 内容 -->
          <div class="px-5 pb-5 sm:px-6">
            <slot />
          </div>

          <!-- 操作区：HIG 惯例是「取消在左、确认在右」，破坏性确认走红色 -->
          <div v-if="$slots.footer" class="flex items-center justify-end gap-3 border-t border-line px-5 py-4 sm:px-6">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  testId: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const panel = ref(null)
// 触发元素：关闭后把焦点还回去，键盘用户不会丢位置
let lastFocused = null

const close = () => emit('update:modelValue', false)

const onKeydown = (e) => {
  if (e.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      lastFocused = document.activeElement
      // 锁背景滚动：补一个 padding 抵消滚动条消失带来的横向跳动
      const gap = window.innerWidth - document.documentElement.clientWidth
      document.body.style.overflow = 'hidden'
      if (gap > 0) document.body.style.paddingRight = `${gap}px`
      document.addEventListener('keydown', onKeydown)
      await nextTick()
      panel.value?.focus()
    } else {
      document.body.style.overflow = ''
      document.body.style.paddingRight = ''
      document.removeEventListener('keydown', onKeydown)
      lastFocused?.focus?.()
    }
  }
)
</script>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.sheet-enter-active > *,
.sheet-leave-active > * {
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from > *,
.sheet-leave-to > * {
  transform: translateY(12px);
}
</style>
