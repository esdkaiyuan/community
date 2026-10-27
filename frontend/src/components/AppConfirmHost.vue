<template>
  <!--
    Apple HIG 警告框（Alert）
    用于「确认一个不可逆或代价高的动作」：删除项目、退出登录、放弃未保存的编辑。

    HIG 的 Alert 有固定结构：标题（一句话说清后果）+ 说明（说清代价）+ 两个按钮。
    **破坏性按钮在左、取消在右**——这是 iOS Alert 的特例（普通对话框是取消在左），
    因为拇指最先落到的是右侧，把「取消」放在最容易误触的位置更安全。

    自适应：窄屏用 iOS 的 action sheet 形态（按钮竖排、从底部升起），
    桌面用 macOS 的居中 alert（按钮横排）。
  -->
  <Teleport to="body">
    <transition name="alert">
      <div
        v-if="state.open"
        class="fixed inset-0 z-[100] flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center sm:p-4"
        data-test="confirm-dialog"
        @click.self="settleConfirm(false)"
      >
        <div
          ref="panel"
          class="w-full max-w-sm animate-sheet-up overflow-hidden rounded-t-22 bg-[color:var(--glass-menu)] shadow-pop backdrop-blur-xl sm:animate-none sm:rounded-22"
          role="alertdialog"
          aria-modal="true"
          :aria-label="state.title"
          tabindex="-1"
        >
          <div class="px-5 pb-4 pt-5 text-center sm:px-6 sm:pb-5 sm:pt-6">
            <h3 class="text-headline font-semibold text-ink">{{ state.title }}</h3>
            <p v-if="state.message" class="mt-1.5 text-footnote leading-relaxed text-ink-mid">
              {{ state.message }}
            </p>
          </div>

          <!-- 分隔线用 0.5px 发丝线，这是 HIG Alert 的标志性细节。

               按钮只渲染一份 DOM，靠 flex 方向切换两种排布：
                 窄屏 flex-col（iOS action sheet：竖排、更厚的行高）；
                 桌面 flex-row（macOS alert：横排、均分宽度）。
               刻意不做「两套 DOM + hidden 切换」——那样同一个 data-test 会在 DOM 里
               出现两次，脚本 count() 拿到 2、click() 点到不可见的那一套。
               确认键放第一个：竖排时在上、横排时在左，两种排布下都落在 HIG 要求的位置。 -->
          <div class="flex flex-col border-t border-line sm:flex-row">
            <button
              type="button"
              data-test="confirm-ok"
              class="border-b border-line py-3.5 text-body transition-colors sm:flex-1 sm:border-b-0 sm:border-r sm:py-3"
              :class="state.destructive ? 'font-semibold text-clay hover:bg-clay/5' : 'font-medium text-pine hover:bg-pine-soft/50'"
              @click="settleConfirm(true)"
            >
              {{ state.confirmLabel }}
            </button>
            <button
              type="button"
              data-test="confirm-cancel"
              class="py-3.5 text-body font-medium text-pine transition-colors hover:bg-pine-soft/50 sm:flex-1 sm:py-3"
              @click="settleConfirm(false)"
            >
              {{ state.cancelLabel }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { settleConfirm, useConfirmState } from '@/composables/useConfirm'

const state = useConfirmState()
const panel = ref(null)
let lastFocused = null

const onKeydown = (e) => {
  // Alert 的 Esc = 取消（HIG：Esc 永远等价于「不做事」）
  if (e.key === 'Escape') settleConfirm(false)
}

watch(
  () => state.open,
  async (open) => {
    if (open) {
      lastFocused = document.activeElement
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
.alert-enter-active,
.alert-leave-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.alert-enter-from,
.alert-leave-to {
  opacity: 0;
}
</style>
